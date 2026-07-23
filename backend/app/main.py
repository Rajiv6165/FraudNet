import asyncio
import os
from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app import crud, schemas, database, simulator, auth

# WebSocket connection manager to broadcast updates to dashboard clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Silently handle disconnected clients that haven't triggered disconnect yet
                pass

manager = ConnectionManager()

# Background task: Listen for Postgres pg_notify events and push them to WebSockets
async def pg_listener():
    # Retrieve DB URL and adapt for asyncpg connection
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/fraudnet")
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    
    while True:
        try:
            print(f"pg_listener: Connecting to {dsn}...")
            conn = await asyncpg.connect(dsn)
            print("pg_listener: Successfully connected to Postgres. Registering LISTEN transaction_flagged...")
            
            def handle_notification(connection, pid, channel, payload):
                # Schedule the broadcast immediately in the running async event loop
                asyncio.create_task(manager.broadcast(payload))
                
            await conn.add_listener('transaction_flagged', handle_notification)
            
            # Keep listener task alive indefinitely
            while True:
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("pg_listener: Cancelled.")
            try:
                await conn.close()
            except Exception:
                pass
            break
        except Exception as e:
            print(f"pg_listener: Connection lost ({e}). Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

# Background task: Periodic refresh of live_risk_dashboard materialized view
async def refresh_materialized_view_loop():
    # Wait for the DB to populate initially
    await asyncio.sleep(10)
    while True:
        try:
            async with database.AsyncSessionLocal() as db:
                await crud.refresh_materialized_view(db)
                print("pg_scheduler: Concurrently refreshed live_risk_dashboard view.")
        except asyncio.CancelledError:
            print("pg_scheduler: Materialized view refresh loop cancelled.")
            break
        except Exception as e:
            print(f"pg_scheduler: Materialized view refresh failed ({e}). Retrying in 30 seconds.")
        
        await asyncio.sleep(30) # Refresh materialized view every 30 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    listener_task = asyncio.create_task(pg_listener())
    refresh_task = asyncio.create_task(refresh_materialized_view_loop())
    yield
    # Shutdown tasks
    listener_task.cancel()
    refresh_task.cancel()
    await simulator.stop_simulation()
    
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass
    print("Application shutdown complete.")

app = FastAPI(
    title="FraudNet Real-time Scoring Backend",
    description="Thin ingestion and real-time streaming shell using SQL-Native PG triggers.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configurations for local React development and production
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")] if allowed_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication endpoint
@app.post("/auth/token", response_model=auth.Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Issues JWT access tokens for valid demo credentials.
    Supports both JSON payload and OAuth2 Form data.
    """
    username = None
    password = None

    if request.headers.get("content-type") == "application/json":
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            pass

    if not username and form_data:
        username = form_data.username
        password = form_data.password

    if username != auth.DEMO_USERNAME or password != auth.DEMO_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}

# Ingestion endpoint
@app.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(tx: schemas.TransactionCreate, db: AsyncSession = Depends(database.get_db)):
    """
    Ingests a financial transaction. The transaction table trigger automatically
    fires PL/pgSQL routines calculating risk scores and saving to fraud_scores.
    """
    db_tx, db_score = await crud.create_transaction(db, tx)
    return {
        "transaction": schemas.Transaction.from_orm(db_tx),
        "score": schemas.FraudScore.from_orm(db_score) if db_score else None
    }

# Score retrieval endpoint (Protected behind JWT Bearer token)
@app.get("/transactions/{id}/score", response_model=schemas.FraudScore)
async def get_transaction_score(
    id: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: str = Depends(auth.verify_jwt)
):
    """
    Returns the computed fraud scores for a specific transaction. Protected by JWT auth.
    """
    try:
        tx_uuid = UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID transaction ID format")
        
    db_score = await crud.get_transaction_score(db, tx_uuid)
    if not db_score:
        raise HTTPException(status_code=404, detail="Score record not found for this transaction")
    return db_score

# Connected Fraud Rings endpoint (Protected behind JWT Bearer token)
@app.get("/rings", response_model=list[schemas.FraudRing])
async def get_fraud_rings(
    db: AsyncSession = Depends(database.get_db),
    current_user: str = Depends(auth.verify_jwt)
):
    """
    Returns active user clusters identified by the recursive CTE ring algorithm. Protected by JWT auth.
    """
    return await crud.get_fraud_rings(db)

# Materialized View Dashboard aggregation endpoint
@app.get("/dashboard/metrics", response_model=list[schemas.DashboardMetric])
async def get_dashboard_metrics(db: AsyncSession = Depends(database.get_db)):
    """
    Retrieves aggregated merchant/country risk volume metrics from live_risk_dashboard.
    """
    return await crud.get_dashboard_metrics(db)

# Simulator Control: Start
@app.post("/simulator/start")
async def start_sim(speed: float = 1.0):
    """
    Kicks off the live transaction generator simulation loop.
    """
    started = await simulator.start_simulation(speed)
    if started:
        return {"status": "started", "speed": speed}
    else:
        return {"status": "running", "speed": speed, "message": "Simulator speed updated."}

# Simulator Control: Stop
@app.post("/simulator/stop")
async def stop_sim():
    """
    Halts the live transaction generator simulation loop.
    """
    stopped = await simulator.stop_simulation()
    if stopped:
        return {"status": "stopped"}
    else:
        return {"status": "not_running"}

# Live stream WebSocket feed
@app.websocket("/ws/live-feed")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("WebSocket client connected to live feed.")
    try:
        while True:
            # Keep connection alive; discard any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket client disconnected.")
    except Exception as e:
        manager.disconnect(websocket)
        print(f"WebSocket client error: {e}")
