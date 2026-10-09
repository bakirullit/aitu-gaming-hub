"""Add creator_steam_id and make creator_id nullable ondelete SET NULL

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-09 04:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add creator_steam_id column
    op.add_column(
        'tournament_bookings',
        sa.Column('creator_steam_id', sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f('ix_tournament_bookings_creator_steam_id'),
        'tournament_bookings',
        ['creator_steam_id'],
        unique=False,
    )

    # 2. Make creator_id nullable
    op.alter_column(
        'tournament_bookings',
        'creator_id',
        existing_type=sa.BigInteger(),
        nullable=True,
    )

    # 3. Drop CASCADE foreign key and recreate with SET NULL
    op.drop_constraint('tournament_bookings_creator_id_fkey', 'tournament_bookings', type_='foreignkey')
    op.create_foreign_key(
        'tournament_bookings_creator_id_fkey',
        'tournament_bookings',
        'users',
        ['creator_id'],
        ['telegram_id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('tournament_bookings_creator_id_fkey', 'tournament_bookings', type_='foreignkey')
    op.create_foreign_key(
        'tournament_bookings_creator_id_fkey',
        'tournament_bookings',
        'users',
        ['creator_id'],
        ['telegram_id'],
        ondelete='CASCADE',
    )
    op.alter_column(
        'tournament_bookings',
        'creator_id',
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.drop_index(op.f('ix_tournament_bookings_creator_steam_id'), table_name='tournament_bookings')
    op.drop_column('tournament_bookings', 'creator_steam_id')
