"""add workflow tables and debug_events

Revision ID: b2c3d4e5f6a7
Revises: ffb68fdb137e
Create Date: 2026-06-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'ffb68fdb137e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('workflow_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='running'),
        sa.Column('final_answer', sa.Text(), nullable=True),
        sa.Column('started_at', sa.String(), nullable=False),
        sa.Column('finished_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['conversation_id'], ['conversations.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['message_id'], ['messages.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Create workflow_steps table
    op.create_table(
        'workflow_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(), nullable=False),
        sa.Column('step_name', sa.String(), nullable=False),
        sa.Column('input', sa.Text(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='running'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.String(), nullable=False),
        sa.Column('finished_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. Create debug_events table (with FK to workflow_steps)
    op.create_table(
        'debug_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('step_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ['conversation_id'], ['conversations.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['message_id'], ['messages.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['step_id'], ['workflow_steps.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # 4. Drop old debug_logs table
    op.drop_table('debug_logs')


def downgrade() -> None:
    op.create_table(
        'debug_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('request_model', sa.String(), nullable=True),
        sa.Column('request_temperature', sa.Float(), nullable=True),
        sa.Column('request_max_tokens', sa.Integer(), nullable=True),
        sa.Column('request_system_prompt', sa.Text(), nullable=True),
        sa.Column('request_user_prompt', sa.Text(), nullable=True),
        sa.Column('response_content', sa.Text(), nullable=True),
        sa.Column('response_finish_reason', sa.String(), nullable=True),
        sa.Column('response_prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('response_completion_tokens', sa.Integer(), nullable=True),
        sa.Column('response_total_tokens', sa.Integer(), nullable=True),
        sa.Column('timing_start', sa.String(), nullable=True),
        sa.Column('timing_end', sa.String(), nullable=True),
        sa.Column('timing_duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['message_id'], ['messages.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.drop_table('debug_events')
    op.drop_table('workflow_steps')
    op.drop_table('workflow_executions')
