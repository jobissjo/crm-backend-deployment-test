"""Initial CRM tables. Schema is frozen here independently of application models."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def columns(owned=False):
    result = [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]
    if owned:
        result.append(sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    return result


def upgrade():
    op.create_table("users", *columns(), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("password_hash", sa.Text(), nullable=False))
    op.create_table("companies", *columns(True), sa.Column("name", sa.String(200), nullable=False), sa.Column("website", sa.String(500)))
    op.create_table("contacts", *columns(True), sa.Column("name", sa.String(200), nullable=False), sa.Column("email", sa.String(320)), sa.Column("phone", sa.String(50)), sa.Column("company_id", sa.Uuid(), sa.ForeignKey("companies.id", ondelete="SET NULL")))
    op.create_table("deals", *columns(True), sa.Column("title", sa.String(200), nullable=False), sa.Column("value", sa.Numeric(14, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("stage", sa.String(20), nullable=False), sa.Column("contact_id", sa.Uuid(), sa.ForeignKey("contacts.id", ondelete="SET NULL")), sa.CheckConstraint("value >= 0", name="ck_deal_value"), sa.CheckConstraint("stage IN ('lead', 'qualified', 'proposal', 'won', 'lost')", name="ck_deal_stage"))
    op.create_table("tasks", *columns(True), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(20), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id", ondelete="SET NULL")), sa.CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_task_status"))
    for table in ("companies", "contacts", "deals", "tasks"):
        op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])
    for table, field in (("contacts", "company_id"), ("deals", "contact_id"), ("tasks", "deal_id")):
        op.create_index(f"ix_{table}_{field}", table, [field])


def downgrade():
    for table in ("tasks", "deals", "contacts", "companies", "users"):
        op.drop_table(table)
