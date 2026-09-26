"""initial_schema

Revision ID: c2e19c6f1fa6
Revises: 
Create Date: 2026-09-10 02:47:12.945432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e19c6f1fa6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        'users',
        sa.Column('telegram_id', sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('student_id', sa.String(length=32), nullable=True),
        sa.Column('barcode', sa.String(length=64), nullable=True),
        sa.Column(
            'role',
            sa.Enum('STUDENT', 'DISCIPLINE_ADMIN', 'HEAD_ADMIN', name='user_role_enum'),
            nullable=False,
            server_default='STUDENT',
        ),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_users_barcode'), 'users', ['barcode'], unique=True)
    op.create_index(op.f('ix_users_student_id'), 'users', ['student_id'], unique=True)

    # 2. Minecraft whitelist table
    op.create_table(
        'minecraft_whitelist',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('nickname', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_minecraft_whitelist_nickname'), 'minecraft_whitelist', ['nickname'], unique=True)

    # 3. Helpdesk tickets table
    op.create_table(
        'helpdesk_tickets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False),
        sa.Column('admin_message_id', sa.BigInteger(), nullable=True),
        sa.Column('subject', sa.String(length=128), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='ticket_status_enum'),
            nullable=False,
            server_default='OPEN',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_helpdesk_tickets_user_id'), 'helpdesk_tickets', ['user_id'], unique=False)
    op.create_index(op.f('ix_helpdesk_tickets_admin_message_id'), 'helpdesk_tickets', ['admin_message_id'], unique=False)

    # 4. Discipline admins table
    op.create_table(
        'discipline_admins',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('telegram_id', sa.BigInteger(), sa.ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False),
        sa.Column(
            'discipline',
            sa.Enum('CS2', 'DOTA2', 'VALORANT', 'FIFA', 'PUBG', 'MLBB', 'OTHER', name='discipline_type_enum'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('telegram_id', 'discipline', name='uq_admin_discipline'),
    )
    op.create_index(op.f('ix_discipline_admins_telegram_id'), 'discipline_admins', ['telegram_id'], unique=False)

    # 5. Tournament bookings table
    op.create_table(
        'tournament_bookings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('creator_id', sa.BigInteger(), sa.ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False),
        sa.Column(
            'discipline',
            sa.Enum('CS2', 'DOTA2', 'VALORANT', 'FIFA', 'PUBG', 'MLBB', 'OTHER', name='discipline_type_enum'),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=False),
        sa.Column('event_format', sa.String(length=32), nullable=False),
        sa.Column('rulebook_file_id', sa.String(length=255), nullable=True),
        sa.Column('rulebook_url', sa.String(length=512), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', name='tournament_status_enum'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('approval_msg_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_tournament_bookings_creator_id'), 'tournament_bookings', ['creator_id'], unique=False)
    op.create_index(op.f('ix_tournament_bookings_booking_date'), 'tournament_bookings', ['booking_date'], unique=False)


def downgrade() -> None:
    op.drop_table('tournament_bookings')
    op.drop_table('discipline_admins')
    op.drop_table('helpdesk_tickets')
    op.drop_table('minecraft_whitelist')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS tournament_status_enum')
    op.execute('DROP TYPE IF EXISTS discipline_type_enum')
    op.execute('DROP TYPE IF EXISTS ticket_status_enum')
    op.execute('DROP TYPE IF EXISTS user_role_enum')
