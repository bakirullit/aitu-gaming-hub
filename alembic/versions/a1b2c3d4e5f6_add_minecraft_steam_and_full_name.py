"""Add minecraft_nickname, steam_id, full_name and convert role to varchar

Revision ID: a1b2c3d4e5f6
Revises: 62f206feeeb8
Create Date: 2026-10-06 05:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '62f206feeeb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add missing columns to users table
    op.add_column('users', sa.Column('minecraft_nickname', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('steam_id', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_steam_id'), 'users', ['steam_id'], unique=True)

    # 2. Convert role column to varchar(32) to support guest, verified_guest, student, etc.
    op.alter_column(
        'users',
        'role',
        type_=sa.String(length=32),
        postgresql_using='role::text',
        server_default='guest',
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_users_steam_id'), table_name='users')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'steam_id')
    op.drop_column('users', 'minecraft_nickname')
