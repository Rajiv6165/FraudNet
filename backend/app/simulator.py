import asyncio
import random
import os
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app import crud, schemas

# Shared state for simulation
is_running = False
speed = 1.0 # transactions per second
simulation_task = None

# Pre-defined simulation profiles to generate realistic live data
COUNTRIES = ['USA', 'GBR', 'CAN', 'IND', 'DEU', 'FRA', 'AUS', 'SGP', 'JPN', 'BRA']
CATEGORIES = ['retail', 'food', 'electronics', 'entertainment', 'travel', 'services', 'transfer']
MERCHANTS = {
    'retail': ['Amazon', 'Walmart', 'Target', 'BestBuy', 'Costco'],
    'food': ['UberEats', 'Starbucks', 'McDonalds', 'Dominos', 'Subway'],
    'electronics': ['Apple Store', 'Samsung Electronics', 'Newegg', 'BestBuy'],
    'entertainment': ['Netflix', 'Spotify', 'Steam', 'Ticketmaster', 'Nintendo'],
    'travel': ['Delta Airlines', 'Uber', 'Airbnb', 'Expedia', 'Booking.com'],
    'services': ['AWS', 'Google Cloud', 'Adobe', 'Zoom', 'Fiverr'],
    'transfer': ['PayPal', 'Venmo', 'CashApp', 'Revolut', 'Wise']
}

# Pre-cached user and card lists to avoid querying DB for every transaction
users_cache = []
cards_cache = []
devices_cache = []

async def load_caches():
    global users_cache, cards_cache, devices_cache
    async with AsyncSessionLocal() as db:
        # Load first 1000 users for simulation
        res_users = await db.execute(text("SELECT id, home_country FROM users LIMIT 1000"))
        users_cache = [{"id": r[0], "home_country": r[1]} for r in res_users.all()]
        
        res_cards = await db.execute(text("SELECT id, last_four, user_id FROM cards LIMIT 1200"))
        cards_cache = [{"id": r[0], "last_four": r[1], "user_id": r[2]} for r in res_cards.all()]
        
        res_devices = await db.execute(text("SELECT id FROM devices LIMIT 1000"))
        devices_cache = [r[0] for r in res_devices.all()]

async def simulate_loop():
    global is_running, speed
    print("Simulator started.")
    
    # Pre-load caches if empty
    if not users_cache or not cards_cache:
        await load_caches()
        
    if not users_cache:
        print("No users found in database. Seed the database first.")
        is_running = False
        return

    # Planted fraud ring simulation states
    # Define 3 active fraud rings
    fraud_rings = [
        # Ring 1: users 10, 11, 12, 13 sharing dev_sim_1, IP 192.168.1.100, last four card 5555
        {
            "users": [10, 11, 12, 13],
            "device": "dev_sim_1",
            "ip": "192.168.1.100",
            "last_four": "5555",
            "card_ids": [], # will populate
        },
        # Ring 2: users 25, 26, 27, 28 sharing dev_sim_2, IP 10.0.0.5, last four card 7777
        {
            "users": [25, 26, 27, 28],
            "device": "dev_sim_2",
            "ip": "10.0.0.5",
            "last_four": "7777",
            "card_ids": [],
        }
    ]

    # Initialize fraud ring cards & devices in DB if they don't exist
    async with AsyncSessionLocal() as db:
        # Create devices
        for ring in fraud_rings:
            await db.execute(
                text("INSERT INTO devices (id, fingerprint, first_seen) VALUES (:id, :fp, :seen) ON CONFLICT DO NOTHING"),
                {"id": ring["device"], "fp": ring["device"] + "_fp", "seen": datetime.utcnow()}
            )
            # Find or create card IDs for these users sharing card last_four
            for uid in ring["users"]:
                # Ensure users exist (fallback check)
                await db.execute(
                    text("INSERT INTO users (id, name, home_country, risk_tier) VALUES (:id, :name, 'USA', 'medium') ON CONFLICT DO NOTHING"),
                    {"id": uid, "name": f"Ring Member {uid}"}
                )
                # Create a card
                await db.execute(
                    text("INSERT INTO cards (last_four, issuer, user_id) VALUES (:last_four, 'Visa', :user_id)"),
                    {"last_four": ring["last_four"], "user_id": uid}
                )
                res = await db.execute(
                    text("SELECT id FROM cards WHERE user_id = :user_id AND last_four = :last_four LIMIT 1"),
                    {"user_id": uid, "last_four": ring["last_four"]}
                )
                card_id = res.scalar()
                ring["card_ids"].append(card_id)
        await db.commit()

    while is_running:
        # Determine if we should generate a normal or a fraud ring transaction
        # 85% normal, 15% fraud ring
        is_fraud = random.random() < 0.15
        
        async with AsyncSessionLocal() as db:
            try:
                if is_fraud:
                    # Choose a random fraud ring
                    ring = random.choice(fraud_rings)
                    uid = random.choice(ring["users"])
                    # select their shared card id
                    card_idx = ring["users"].index(uid)
                    card_id = ring["card_ids"][card_idx]
                    
                    # Generate anomaly: high transaction amount, novel merchant, different country
                    tx_create = schemas.TransactionCreate(
                        user_id=uid,
                        card_id=card_id,
                        device_id=ring["device"],
                        ip_address=ring["ip"],
                        amount=Decimal(str(random.randint(700, 1500))),
                        merchant="WireTransfer Inc",
                        merchant_category="transfer",
                        country="RUS" if random.random() < 0.6 else "USA",
                        status="approved"
                    )
                else:
                    # Choose a random normal user
                    user = random.choice(users_cache)
                    uid = user["id"]
                    country = user["home_country"]
                    
                    # Find user cards
                    user_cards = [c for c in cards_cache if c["user_id"] == uid]
                    if not user_cards:
                        # Fallback card
                        card_id = random.choice(cards_cache)["id"]
                    else:
                        card_id = random.choice(user_cards)["id"]
                        
                    device_id = random.choice(devices_cache) if devices_cache else "dev_generic"
                    
                    # 2% chance of travel anomaly
                    if random.random() < 0.02:
                        country = random.choice(COUNTRIES)
                        
                    category = random.choice(CATEGORIES)
                    merchant = random.choice(MERCHANTS[category])
                    
                    # Amount is usually normal, occasionally a bit higher
                    amount = Decimal(str(round(random.expovariate(1 / 45.0) + 5.0, 2)))
                    
                    tx_create = schemas.TransactionCreate(
                        user_id=uid,
                        card_id=card_id,
                        device_id=device_id,
                        ip_address=f"{random.randint(1, 223)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
                        amount=amount,
                        merchant=merchant,
                        merchant_category=category,
                        country=country,
                        status="approved"
                    )
                
                # Ingest transaction (this triggers SQL logic and broadcasts to WS)
                _, db_score = await crud.create_transaction(db, tx_create)
                
            except Exception as e:
                print(f"Simulator error in loop: {e}")
                
        # Sleep based on the configured speed
        await asyncio.sleep(1.0 / speed)

async def start_simulation(sim_speed: float):
    global is_running, speed, simulation_task
    if is_running:
        speed = sim_speed
        return False
        
    is_running = True
    speed = sim_speed
    simulation_task = asyncio.create_task(simulate_loop())
    return True

async def stop_simulation():
    global is_running, simulation_task
    if not is_running:
        return False
        
    is_running = False
    if simulation_task:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
        simulation_task = None
    return True
