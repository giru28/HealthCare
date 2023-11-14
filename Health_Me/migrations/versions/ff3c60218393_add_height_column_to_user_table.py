"""Add height column to user table

Revision ID: ff3c60218393
Revises: 755556dc86cb
Create Date: 2023-10-25 12:55:32.536496

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff3c60218393'
down_revision = '755556dc86cb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_activity')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('height', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('weight', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('age', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('gender', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('health_goal', sa.String(length=100), nullable=True))

    op.add_column('user', sa.Column('date', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('health_goal')
        batch_op.drop_column('gender')
        batch_op.drop_column('age')
        batch_op.drop_column('weight')
        batch_op.drop_column('height')

    op.create_table('user_activity',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('username', sa.VARCHAR(length=80), nullable=False),
    sa.Column('password', sa.VARCHAR(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )

    op.drop_column('user', 'date')
    
    # ### end Alembic commands ###
