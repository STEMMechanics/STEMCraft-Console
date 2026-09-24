"""Replace automatic plugin mappings with explicit source/extraction settings."""
from alembic import op
import sqlalchemy as sa

revision = '49d32eaf51c6'
down_revision = '38c21d9e40b5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('plugin_monitoring_settings') as batch:
        batch.alter_column('project', existing_type=sa.String(150), type_=sa.Text(), existing_nullable=False)
        for name in ('version_pattern', 'link_pattern', 'installed_pattern'):
            batch.add_column(sa.Column(name, sa.Text(), nullable=False, server_default=''))
    # Retain explicit generic configurations, but never silently choose a source
    # or carry forward a removed plugin-specific adapter.
    op.execute("UPDATE plugin_monitoring_settings SET mode='disabled', provider='', project='' "
               "WHERE mode='automatic' OR provider NOT IN ('github', 'modrinth', '')")
    op.execute("DELETE FROM server_update_checks WHERE component != '@paper'")


def downgrade():
    op.execute("UPDATE plugin_monitoring_settings SET mode='disabled', provider='', project='' "
               "WHERE provider NOT IN ('github', 'modrinth', '') OR length(project) > 150")
    with op.batch_alter_table('plugin_monitoring_settings') as batch:
        for name in ('version_pattern', 'link_pattern', 'installed_pattern'):
            batch.drop_column(name)
        batch.alter_column('project', existing_type=sa.Text(), type_=sa.String(150), existing_nullable=False)
