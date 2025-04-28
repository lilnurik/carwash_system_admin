"""change_program_id_to_string

Revision ID: 1d31f23ba161
Revises: 365c0b27d94b
Create Date: 2025-04-28 13:02:52.671362

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '1d31f23ba161'
down_revision = '365c0b27d94b'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Create a new programs table with string IDs
    op.create_table('programs_new',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price_per_second', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Step 2: Copy data from old to new table with string IDs
    op.execute(
        "INSERT INTO programs_new (id, name, price_per_second, is_active, description, created_at, updated_at) "
        "SELECT 'PROGRAM_' || id::text, name, price_per_second, is_active, description, created_at, updated_at FROM programs"
    )

    # Step 3: Create a new device_programs table with string program IDs
    op.create_table('device_programs_new',
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.ForeignKeyConstraint(['program_id'], ['programs_new.id'], ),
        sa.PrimaryKeyConstraint('device_id', 'program_id')
    )

    # Step 4: Copy device_programs associations with string IDs
    op.execute(
        "INSERT INTO device_programs_new (device_id, program_id) "
        "SELECT device_id, 'PROGRAM_' || program_id::text FROM device_programs"
    )

    # Step 5: Drop old tables and constraints
    op.drop_table('device_programs')
    op.drop_table('programs')

    # Step 6: Rename new tables to original names
    op.rename_table('programs_new', 'programs')
    op.rename_table('device_programs_new', 'device_programs')


def downgrade():
    # Reverse the process - convert string IDs back to integers
    # Warning: This can lose data if string IDs don't follow the "PROGRAM_{number}" pattern
    op.create_table('programs_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price_per_second', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Try to extract numeric part from string IDs
    op.execute(
        "INSERT INTO programs_old (id, name, price_per_second, is_active, description, created_at, updated_at) "
        "SELECT CASE WHEN id ~ '^PROGRAM_([0-9]+)$' THEN substring(id from 9)::integer ELSE 999999 END, "
        "name, price_per_second, is_active, description, created_at, updated_at FROM programs"
    )

    # Rest of the downgrade process similar to upgrade
    op.create_table('device_programs_old',
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.ForeignKeyConstraint(['program_id'], ['programs_old.id'], ),
        sa.PrimaryKeyConstraint('device_id', 'program_id')
    )

    # Convert links
    op.execute(
        "INSERT INTO device_programs_old (device_id, program_id) "
        "SELECT device_id, CASE WHEN program_id ~ '^PROGRAM_([0-9]+)$' THEN substring(program_id from 9)::integer ELSE 999999 END "
        "FROM device_programs"
    )

    # Drop and rename
    op.drop_table('device_programs')
    op.drop_table('programs')
    op.rename_table('programs_old', 'programs')
    op.rename_table('device_programs_old', 'device_programs')