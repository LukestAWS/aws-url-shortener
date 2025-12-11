"""resolve multiple heads

Revision ID: 424296272c0d
Revises: 2362d2854bf7, 0001
Create Date: 2025-12-11 20:18:23.515744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '424296272c0d'
down_revision: Union[str, None] = ('2362d2854bf7', '0001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
