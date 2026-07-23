import pytest
from uuid import UUID
from sqlalchemy import text
from app import database, crud, schemas

@pytest.mark.asyncio
async def test_insert_transaction_triggers_fraud_scores():
    """
    Test 1: Verify that inserting a transaction into the transactions table
    fires the PL/pgSQL trigger process_transaction_fraud_scores() and automatically
    creates a corresponding row in the fraud_scores table.
    """
    async with database.AsyncSessionLocal() as session:
        # Create a test user and device if needed
        test_user_id = 99901
        await session.execute(
            text("INSERT INTO users (id, name, home_country, risk_tier) VALUES (:id, 'Trigger Test User', 'USA', 'low') ON CONFLICT DO NOTHING"),
            {"id": test_user_id}
        )
        await session.execute(
            text("INSERT INTO devices (id, fingerprint) VALUES ('dev_test_trigger', 'fp_trigger_1') ON CONFLICT DO NOTHING")
        )
        await session.execute(
            text("INSERT INTO cards (id, last_four, issuer, user_id) VALUES (99901, '4321', 'Visa', :uid) ON CONFLICT DO NOTHING"),
            {"uid": test_user_id}
        )
        await session.commit()

        tx_in = schemas.TransactionCreate(
            user_id=test_user_id,
            card_id=99901,
            device_id="dev_test_trigger",
            ip_address="192.168.1.50",
            amount=250.00,
            merchant="Test Merchant",
            merchant_category="retail",
            country="USA",
            status="approved"
        )

        db_tx, db_score = await crud.create_transaction(session, tx_in)

        # Assert transaction was created
        assert db_tx.id is not None
        assert db_tx.user_id == test_user_id

        # Assert trigger automatically created a fraud_scores row
        assert db_score is not None
        assert db_score.transaction_id == db_tx.id
        assert db_score.velocity_score is not None
        assert db_score.deviation_score is not None
        assert db_score.ring_score is not None
        assert db_score.composite_score is not None
        assert isinstance(db_score.flagged, bool)
