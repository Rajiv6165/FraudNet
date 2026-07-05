import os
import random
import sys
import datetime
from decimal import Decimal
from faker import Faker
from sqlalchemy import text
from app.database import SessionLocal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

fake = Faker()

COUNTRIES = ['USA', 'GBR', 'CAN', 'IND', 'DEU', 'FRA', 'AUS', 'SGP', 'JPN', 'BRA']
CATEGORIES = ['retail', 'food', 'electronics', 'entertainment', 'travel', 'services', 'transfer']
ISSUERS = ['Visa', 'Mastercard', 'Amex', 'Discover']
MERCHANTS = {
    'retail': ['Amazon', 'Walmart', 'Target', 'BestBuy', 'Costco'],
    'food': ['UberEats', 'Starbucks', 'McDonalds', 'Dominos', 'Subway'],
    'electronics': ['Apple Store', 'Samsung Electronics', 'Newegg', 'BestBuy'],
    'entertainment': ['Netflix', 'Spotify', 'Steam', 'Ticketmaster', 'Nintendo'],
    'travel': ['Delta Airlines', 'Uber', 'Airbnb', 'Expedia', 'Booking.com'],
    'services': ['AWS', 'Google Cloud', 'Adobe', 'Zoom', 'Fiverr'],
    'transfer': ['PayPal', 'Venmo', 'CashApp', 'Revolut', 'Wise']
}

def seed_db():
    db = SessionLocal()
    print("Connecting to database and clearing existing data...")
    db.execute(text("TRUNCATE TABLE users, devices, cards, transactions, fraud_scores CASCADE;"))
    db.commit()

    print("Generating users, devices, and cards...")
    
    # 1. Generate 5,000 regular users
    users = []
    user_countries = {}
    print("Creating users...")
    user_insert_data = []
    for i in range(1, 5001):
        country = random.choices(COUNTRIES, weights=[40, 10, 10, 15, 5, 5, 5, 4, 3, 3])[0]
        user_countries[i] = country
        created_at = datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(30, 365))
        
        user_insert_data.append({
            "id": i,
            "name": fake.name(),
            "home_country": country,
            "risk_tier": "low",
            "created_at": created_at
        })
        
        if i % 1000 == 0:
            print(f"  Generated {i}/5000 users...")

    # Execute users bulk insert
    db.execute(
        text("INSERT INTO users (id, name, home_country, risk_tier, created_at) VALUES (:id, :name, :home_country, :risk_tier, :created_at)"),
        user_insert_data
    )
    db.commit()

    # 2. Generate Devices (about 4,500 unique devices for 5,000 users)
    print("Creating devices...")
    device_fingerprints = [fake.sha256() for _ in range(4500)]
    device_insert_data = []
    for i, fp in enumerate(device_fingerprints):
        device_insert_data.append({
            "id": f"dev_{i+1}",
            "fingerprint": fp,
            "first_seen": datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(30, 365))
        })
    
    db.execute(
        text("INSERT INTO devices (id, fingerprint, first_seen) VALUES (:id, :fingerprint, :first_seen)"),
        device_insert_data
    )
    db.commit()

    # Assign devices to users
    user_devices = {}
    for uid in range(1, 5001):
        # 90% of users have a dedicated device, 10% share
        if random.random() < 0.9:
            dev_idx = (uid - 1) % len(device_fingerprints)
        else:
            dev_idx = random.randint(0, len(device_fingerprints) - 1)
        user_devices[uid] = f"dev_{dev_idx+1}"

    # 3. Generate Cards (about 5,500 cards for 5,000 users)
    print("Creating credit cards...")
    card_insert_data = []
    card_counter = 1
    user_cards = {}
    for uid in range(1, 5001):
        user_cards[uid] = []
        # average 1.1 cards per user
        num_cards = 1 if random.random() < 0.9 else 2
        for _ in range(num_cards):
            card_id = card_counter
            card_counter += 1
            last_four = f"{random.randint(0, 9999):04d}"
            issuer = random.choice(ISSUERS)
            card_insert_data.append({
                "id": card_id,
                "last_four": last_four,
                "issuer": issuer,
                "user_id": uid
            })
            user_cards[uid].append(card_id)

    db.execute(
        text("INSERT INTO cards (id, last_four, issuer, user_id) VALUES (:id, :last_four, :issuer, :user_id)"),
        card_insert_data
    )
    db.commit()

    # Reset sequences for serial columns after bulk insert
    db.execute(text("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1), true)"))
    db.execute(text("SELECT setval('cards_id_seq', COALESCE((SELECT MAX(id) FROM cards), 1), true)"))
    db.commit()

    # Keep track of card details for sharing in fraud rings
    card_last_fours = {c['id']: c['last_four'] for c in card_insert_data}

    # 4. Generate normal historical transactions (15,000 transactions)
    print("Generating 15,000 normal transactions...")
    transactions = []
    start_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    
    # Generate user-specific parameters to ensure behavioral consistency
    user_behaviors = {}
    for uid in range(1, 5001):
        user_behaviors[uid] = {
            "avg_amount": float(random.choices([20.0, 50.0, 150.0, 500.0], weights=[50, 35, 12, 3])[0]) * random.uniform(0.8, 1.2),
            "common_category": random.choice(CATEGORIES),
            "ip_prefix": f"{random.randint(1, 223)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        }

    for i in range(15000):
        # Pick a user
        uid = random.randint(1, 5000)
        behavior = user_behaviors[uid]
        country = user_countries[uid]
        
        # 3% chance of transaction in a different country (traveling)
        if random.random() < 0.03:
            country = random.choice(COUNTRIES)
            
        # Amount centered around user's average amount
        amount = Decimal(str(round(random.normalvariate(behavior["avg_amount"], behavior["avg_amount"] * 0.3), 2)))
        if amount <= 0:
            amount = Decimal(str(round(random.uniform(5.0, 20.0), 2)))
            
        category = behavior["common_category"]
        # 20% chance of shopping elsewhere
        if random.random() < 0.20:
            category = random.choice(CATEGORIES)
            
        merchant = random.choice(MERCHANTS[category])
        card_id = random.choice(user_cards[uid])
        device_id = user_devices[uid]
        ip = f"{behavior['ip_prefix']}.{random.randint(1, 254)}"
        
        # Spread transactions evenly over 30 days
        created_at = start_date + datetime.timedelta(
            seconds=random.randint(0, 30 * 86400)
        )
        
        # Status
        status = 'approved'
        if random.random() < 0.02:
            status = 'declined'

        transactions.append({
            "user_id": uid,
            "card_id": card_id,
            "device_id": device_id,
            "ip_address": ip,
            "amount": amount,
            "merchant": merchant,
            "merchant_category": category,
            "country": country,
            "created_at": created_at,
            "status": status
        })

    # 5. Plant 8 Fraud Rings (linked users)
    # Ring sizes between 4 and 8
    # Placed in the final 2 days to act as immediate "unsolved" alerts
    print("Planting 8 fraud rings...")
    ring_users_list = []
    
    # We will grab a block of unused user IDs or override some existing user records
    # Let's override user records from 100 to 150 to keep it simple and clean,
    # or just create dedicated users. Since we already populated 5000 users,
    # we can use users 4900 to 5000 for our rings to avoid messing with other random behaviors.
    ring_user_pool = list(range(4900, 5000))
    
    for ring_idx in range(8):
        ring_size = random.randint(4, 7)
        ring_users = [ring_user_pool.pop() for _ in range(ring_size)]
        ring_users_list.append(ring_users)
        
        # All users in this ring share a single device or IP or card last four
        shared_device_id = f"dev_ring_{ring_idx+1}"
        shared_ip = f"198.51.100.{10 + ring_idx}"
        shared_last_four = f"99{ring_idx:02d}"
        
        # Insert the shared device record
        db.execute(
            text("INSERT INTO devices (id, fingerprint, first_seen) VALUES (:id, :fingerprint, :first_seen) ON CONFLICT DO NOTHING"),
            {
                "id": shared_device_id,
                "fingerprint": fake.sha256(),
                "first_seen": start_date
            }
        )
        
        # Link cards of some members to have the same last four digits
        for uid in ring_users:
            # Update user home country to be distinct, or make transactions country novel
            db.execute(
                text("UPDATE users SET home_country = 'USA', risk_tier = 'medium' WHERE id = :uid"),
                {"uid": uid}
            )
            # Create a card with the shared last_four
            db.execute(
                text("INSERT INTO cards (last_four, issuer, user_id) VALUES (:last_four, :issuer, :user_id)"),
                {"last_four": shared_last_four, "issuer": "Mastercard", "user_id": uid}
            )
            # Fetch the newly created card id
            new_card_id = db.execute(text("SELECT max(id) FROM cards WHERE user_id = :uid"), {"uid": uid}).scalar()
            if uid not in user_cards:
                user_cards[uid] = []
            user_cards[uid].append(new_card_id)
            card_last_fours[new_card_id] = shared_last_four

        # Generate sudden transaction spikes for this ring in the last 2 days
        spike_start = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        
        # Create normal looking setup transactions
        for uid in ring_users:
            card_id = user_cards[uid][0]
            transactions.append({
                "user_id": uid,
                "card_id": card_id,
                "device_id": shared_device_id,
                "ip_address": shared_ip,
                "amount": Decimal("15.50"),
                "merchant": "Netflix",
                "merchant_category": "entertainment",
                "country": "USA",
                "created_at": spike_start - datetime.timedelta(hours=6),
                "status": "approved"
            })
            
        # The Spike: sudden rapid high-value transactions
        # E.g., multiple members transacting within minutes of each other
        for spike_step in range(12):
            uid = random.choice(ring_users)
            card_id = random.choice(user_cards[uid])
            amount = Decimal(str(random.randint(600, 1200))) # high amount
            category = "transfer"
            merchant = random.choice(MERCHANTS[category])
            
            # Transactions occur 5 to 15 minutes apart
            tx_time = spike_start + datetime.timedelta(minutes=spike_step * 10 + random.randint(0, 5))
            
            transactions.append({
                "user_id": uid,
                "card_id": card_id,
                "device_id": shared_device_id,
                "ip_address": shared_ip,
                "amount": amount,
                "merchant": merchant,
                "merchant_category": category,
                "country": "RUS" if random.random() < 0.5 else "USA", # Novel country (RUS)
                "created_at": tx_time,
                "status": "approved"
            })

    # 6. Sort all transactions chronologically!
    # This is critical so that rolling count triggers execute in correct historical sequence
    print("Sorting all transactions chronologically...")
    transactions.sort(key=lambda x: x["created_at"])

    # Disable triggers during seeding?
    # NO! We WANT the triggers to execute so they compute velocity, deviation,
    # and ring scores for the historical database in correct sequence!
    # This is a real test of our SQL scoring engine.
    print(f"Inserting {len(transactions)} transactions sequentially. Triggers will execute...")
    
    # Using raw SQL with parameters for speed
    tx_insert_sql = text("""
        INSERT INTO transactions (user_id, card_id, device_id, ip_address, amount, merchant, merchant_category, country, created_at, status)
        VALUES (:user_id, :card_id, :device_id, :ip_address, :amount, :merchant, :merchant_category, :country, :created_at, :status)
    """)
    
    batch_size = 500
    total_tx = len(transactions)
    for idx in range(0, total_tx, batch_size):
        batch = transactions[idx:idx+batch_size]
        # In order for triggers to run sequentially and capture correct velocity window statistics,
        # we can commit each batch. Since Postgres evaluates row-level triggers inside the transaction,
        # batching is perfectly fine as long as they are sorted chronologically!
        db.execute(tx_insert_sql, batch)
        db.commit()
        print(f"  Inserted {min(idx + batch_size, total_tx)}/{total_tx} transactions...")

    # Refresh materialized view at the end
    print("Refreshing materialized view live_risk_dashboard...")
    db.execute(text("REFRESH MATERIALIZED VIEW live_risk_dashboard"))
    db.commit()

    print("Database seeding completed successfully!")
    db.close()

if __name__ == "__main__":
    seed_db()
