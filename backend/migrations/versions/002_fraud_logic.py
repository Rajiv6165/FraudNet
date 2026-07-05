"""load fraud logic SQL

Revision ID: 002
Revises: 001
Create Date: 2026-07-06 00:05:00.000000

"""
import os
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def load_sql_file(filename):
    # Determine the directory of the current migration file
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # points to migrations/
    project_dir = os.path.dirname(current_dir) # points to backend/
    filepath = os.path.join(project_dir, 'sql', filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def upgrade() -> None:
    # 1. Load and execute fraud functions
    op.execute(load_sql_file('02_fraud_functions.sql'))
    
    # 2. Load and execute triggers
    op.execute(load_sql_file('03_triggers.sql'))
    
    # 3. Load and execute materialized view
    op.execute(load_sql_file('04_materialized_view.sql'))


def downgrade() -> None:
    # Remove triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trg_process_transaction_fraud_scores ON transactions;")
    op.execute("DROP FUNCTION IF EXISTS process_transaction_fraud_scores();")
    op.execute("DROP FUNCTION IF EXISTS detect_user_fraud_ring(INT);")
    op.execute("DROP FUNCTION IF EXISTS detect_fraud_rings();")
    op.execute("DROP FUNCTION IF EXISTS calculate_deviation_score(UUID);")
    op.execute("DROP FUNCTION IF EXISTS calculate_velocity_score(UUID);")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS live_risk_dashboard;")
