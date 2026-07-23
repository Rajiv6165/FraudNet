"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-07-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('home_country', sa.String(length=3), nullable=False),
        sa.Column('risk_tier', sa.String(length=20), server_default='low', nullable=False)
    )
    op.create_index('idx_users_id', 'users', ['id'])

    # 2. Create devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.String(length=50), nullable=False, primary_key=True),
        sa.Column('fingerprint', sa.String(length=255), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_devices_fingerprint', 'devices', ['fingerprint'], unique=True)

    # 3. Create cards table
    op.create_table(
        'cards',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('last_four', sa.String(length=4), nullable=False),
        sa.Column('issuer', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False)
    )
    op.create_index('idx_cards_id', 'cards', ['id'])
    op.create_index('idx_cards_last_four', 'cards', ['last_four'])
    op.create_foreign_key('fk_cards_user_id', 'cards', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # 4. Create partitioned transactions table
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id UUID DEFAULT gen_random_uuid(),
            user_id INT NOT NULL,
            card_id INT NOT NULL,
            device_id VARCHAR(50) NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            amount NUMERIC(12, 2) NOT NULL,
            merchant VARCHAR(100) NOT NULL,
            merchant_category VARCHAR(50) NOT NULL,
            country VARCHAR(3) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            status VARCHAR(20) DEFAULT 'approved' NOT NULL,
            
            PRIMARY KEY (id, created_at),
            CONSTRAINT fk_transactions_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_transactions_card_id FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
            CONSTRAINT fk_transactions_device_id FOREIGN KEY (device_id) REFERENCES devices(id)
        ) PARTITION BY RANGE (created_at);
    """)

    # Monthly Range Partitions
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_05 PARTITION OF transactions FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_06 PARTITION OF transactions FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_07 PARTITION OF transactions FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_08 PARTITION OF transactions FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_09 PARTITION OF transactions FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_10 PARTITION OF transactions FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_11 PARTITION OF transactions FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_2026_12 PARTITION OF transactions FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');")
    op.execute("CREATE TABLE IF NOT EXISTS transactions_default PARTITION OF transactions DEFAULT;")

    op.create_index('idx_transactions_user_id_created_at', 'transactions', ['user_id', 'created_at'])
    op.create_index('idx_transactions_device_id', 'transactions', ['device_id'])
    op.create_index('idx_transactions_ip_address', 'transactions', ['ip_address'])
    op.create_index('idx_transactions_created_at', 'transactions', ['created_at'])

    # 5. Create fraud_scores table
    op.create_table(
        'fraud_scores',
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('velocity_score', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('deviation_score', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('ring_score', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('composite_score', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('flagged', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_fraud_scores_flagged', 'fraud_scores', ['flagged'])


def downgrade() -> None:
    op.drop_table('fraud_scores')
    op.drop_table('transactions')
    op.drop_table('cards')
    op.drop_table('devices')
    op.drop_table('users')
