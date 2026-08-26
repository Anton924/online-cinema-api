"""add_movie_likes_dislikes_table

Revision ID: 301ffefe2329
Revises: 1ca0c2d72ee3
Create Date: 2026-08-24 18:30:52.673775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '301ffefe2329'
down_revision: Union[str, Sequence[str], None] = '1ca0c2d72ee3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('movie_likes_dislikes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('movie_id', sa.Integer(), nullable=False),
    sa.Column('like_dislike', sa.Enum('LIKE', 'DISLIKE', name='likedislikeenum'), nullable=False),
    sa.ForeignKeyConstraint(['movie_id'], ['movies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'movie_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('movie_likes_dislikes')
