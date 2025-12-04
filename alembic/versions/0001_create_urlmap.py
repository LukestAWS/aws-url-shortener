"""create url_map table

Revision ID: 0001
Revises: 
Create Date: 2025-12-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'url_map',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('target', sa.Text(), nullable=False),
        sa.UniqueConstraint('code', name='uq_url_map_code'),
    )


def downgrade() -> None:
    op.drop_table('url_map')
