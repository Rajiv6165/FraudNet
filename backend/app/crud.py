from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from app import models, schemas
from uuid import UUID

async def create_transaction(db: AsyncSession, tx: schemas.TransactionCreate):
    # Insert new transaction
    db_tx = models.Transaction(
        user_id=tx.user_id,
        card_id=tx.card_id,
        device_id=tx.device_id,
        ip_address=tx.ip_address,
        amount=tx.amount,
        merchant=tx.merchant,
        merchant_category=tx.merchant_category,
        country=tx.country,
        status=tx.status
    )
    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)
    
    # Retrieve the score computed by the AFTER INSERT trigger
    result = await db.execute(
        select(models.FraudScore).where(models.FraudScore.transaction_id == db_tx.id)
    )
    db_score = result.scalars().first()
    
    return db_tx, db_score

async def get_transaction_score(db: AsyncSession, transaction_id: UUID):
    result = await db.execute(
        select(models.FraudScore).where(models.FraudScore.transaction_id == transaction_id)
    )
    return result.scalars().first()

async def get_fraud_rings(db: AsyncSession):
    # Execute the custom postgres function detect_fraud_rings()
    result = await db.execute(text("SELECT ring_id, user_id, ring_size, ring_volume FROM detect_fraud_rings()"))
    rows = result.all()
    
    # Map raw rows to schema
    return [
        schemas.FraudRing(
            ring_id=row[0],
            user_id=row[1],
            ring_size=row[2],
            ring_volume=row[3]
        )
        for row in rows
    ]

async def get_dashboard_metrics(db: AsyncSession):
    # Retrieve data from the materialized view
    result = await db.execute(
        text("""
            SELECT merchant_category, country, transaction_hour, transaction_count, flagged_count, total_volume, avg_risk_score 
            FROM live_risk_dashboard 
            ORDER BY transaction_hour DESC
        """)
    )
    rows = result.all()
    return [
        schemas.DashboardMetric(
            merchant_category=row[0],
            country=row[1],
            transaction_hour=row[2],
            transaction_count=row[3],
            flagged_count=row[4],
            total_volume=row[5],
            avg_risk_score=row[6]
        )
        for row in rows
    ]

async def refresh_materialized_view(db: AsyncSession):
    await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY live_risk_dashboard"))
    await db.commit()
