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

    # 4. Create transactions table
    # Make sure gen_random_uuid extension is enabled (in PG 13+ it is built-in but good to have)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('card_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('merchant', sa.String(length=100), nullable=False),
        sa.Column('merchant_category', sa.String(length=50), nullable=False),
        sa.Column('country', sa.String(length=3), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='approved', nullable=False)
    )
    op.create_index('idx_transactions_user_id_created_at', 'transactions', ['user_id', 'created_at'])
    op.create_index('idx_transactions_device_id', 'transactions', ['device_id'])
    op.create_index('idx_transactions_ip_address', 'transactions', ['ip_address'])
    op.create_index('idx_transactions_created_at', 'transactions', ['created_at'])
    
    op.create_foreign_key('fk_transactions_user_id', 'transactions', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_transactions_card_id', 'transactions', 'cards', ['card_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_transactions_device_id', 'transactions', 'devices', ['device_id'])

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
    op.create_foreign_key('fk_fraud_scores_transaction_id', 'fraud_scores', 'transactions', ['transaction_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_table('fraud_scores')
    op.drop_table('transactions')
    op.drop_table('cards')
    op.drop_table('devices')
    op.drop_table('users')
