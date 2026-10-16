"""add pending_staff_members and user lootbox fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-16 14:17:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create pending_staff_members table
    op.create_table(
        'pending_staff_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('first_name', sa.String(length=128), nullable=False),
        sa.Column('last_name', sa.String(length=128), nullable=False),
        sa.Column('academic_group', sa.String(length=32), nullable=True),
        sa.Column('barcode', sa.String(length=64), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('corp_email', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=32), nullable=True),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('staff_role', sa.String(length=32), server_default='none', nullable=False),
        sa.Column('discipline_id', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['discipline_id'], ['disciplines.slug'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pending_staff_members_barcode'), 'pending_staff_members', ['barcode'], unique=True)
    op.create_index(op.f('ix_pending_staff_members_email'), 'pending_staff_members', ['email'], unique=True)
    op.create_index(op.f('ix_pending_staff_members_corp_email'), 'pending_staff_members', ['corp_email'], unique=True)
    op.create_index(op.f('ix_pending_staff_members_username'), 'pending_staff_members', ['username'], unique=True)

    # 2. Add columns to users table
    op.add_column('users', sa.Column('staff_role', sa.String(length=32), server_default='none', nullable=False))
    op.add_column('users', sa.Column('discipline_id', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('is_role_revealed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('role_revealed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_users_discipline_id',
        'users',
        'disciplines',
        ['discipline_id'],
        ['slug'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_discipline_id', 'users', type_='foreignkey')
    op.drop_column('users', 'role_revealed_at')
    op.drop_column('users', 'is_role_revealed')
    op.drop_column('users', 'discipline_id')
    op.drop_column('users', 'staff_role')

    op.drop_index(op.f('ix_pending_staff_members_username'), table_name='pending_staff_members')
    op.drop_index(op.f('ix_pending_staff_members_corp_email'), table_name='pending_staff_members')
    op.drop_index(op.f('ix_pending_staff_members_email'), table_name='pending_staff_members')
    op.drop_index(op.f('ix_pending_staff_members_barcode'), table_name='pending_staff_members')
    op.drop_table('pending_staff_members')
