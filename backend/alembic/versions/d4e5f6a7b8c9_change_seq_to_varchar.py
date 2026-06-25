"""change debug_events seq from integer to varchar

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'debug_events', 'seq',
        existing_type=sa.Integer(),
        type_=sa.String(),
        existing_nullable=False,
        existing_server_default=sa.text("'0'"),
    )


def downgrade() -> None:
    op.alter_column(
        'debug_events', 'seq',
        existing_type=sa.String(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default=sa.text("'0'"),
    )
