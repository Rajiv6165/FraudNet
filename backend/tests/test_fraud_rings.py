import pytest
from sqlalchemy import text
from app import database, crud

@pytest.mark.asyncio
async def test_detect_planted_fraud_ring():
    """
    Test 2: Plant a fraud ring of connected users sharing a device_id and IP address,
    and verify that detect_fraud_rings() identifies the ring cluster and correct member count.
    """
    async with database.AsyncSessionLocal() as session:
        ring_uids = [99920, 99921, 99922]
        shared_device = "dev_planted_ring_test"
        shared_ip = "198.51.100.99"

        # Create users
        for uid in ring_uids:
            await session.execute(
                text("INSERT INTO users (id, name, home_country, risk_tier) VALUES (:id, :name, 'USA', 'medium') ON CONFLICT DO NOTHING"),
                {"id": uid, "name": f"Ring Member {uid}"}
            )
            await session.execute(
                text("INSERT INTO cards (id, last_four, issuer, user_id) VALUES (:cid, '9999', 'Visa', :uid) ON CONFLICT DO NOTHING"),
                {"cid": uid, "uid": uid}
            )
        await session.execute(
            text("INSERT INTO devices (id, fingerprint) VALUES (:did, 'fp_planted_ring') ON CONFLICT DO NOTHING"),
            {"did": shared_device}
        )
        await session.commit()

        # Insert transactions linking all 3 users to the shared device and IP
        for uid in ring_uids:
            await session.execute(
                text("""
                    INSERT INTO transactions (user_id, card_id, device_id, ip_address, amount, merchant, merchant_category, country, status)
                    VALUES (:uid, :cid, :did, :ip, 100.00, 'Test Store', 'retail', 'USA', 'approved')
                """),
                {"uid": uid, "cid": uid, "did": shared_device, "ip": shared_ip}
            )
        await session.commit()

        # Execute fraud ring detection CTE function
        detected_rings = await crud.get_fraud_rings(session)

        # Check if our planted users belong to a detected ring
        user_rings = [r for r in detected_rings if r.user_id in ring_uids]
        assert len(user_rings) >= 3

        # Assert ring_size is at least 3
        found_sizes = {r.ring_size for r in user_rings}
        assert max(found_sizes) >= 3
