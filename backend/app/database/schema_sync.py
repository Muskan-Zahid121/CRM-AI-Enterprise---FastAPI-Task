"""Add missing DB columns when Tortoise models change (dev-safe)."""
from tortoise import Tortoise

from app.config import settings


def _sql_type(field) -> str | None:
    cls_name = type(field).__name__
    if cls_name == "IntField":
        return "INTEGER"
    if cls_name == "CharField":
        return f"VARCHAR({field.max_length})"
    if cls_name == "TextField":
        return "TEXT"
    if cls_name == "BooleanField":
        return "BOOLEAN"
    if cls_name == "DecimalField":
        return f"NUMERIC({field.max_digits},{field.decimal_places})"
    if cls_name == "DateField":
        return "DATE"
    if cls_name == "DatetimeField":
        return "TIMESTAMPTZ"
    if cls_name == "JSONField":
        return "JSONB"
    if cls_name == "ForeignKeyFieldInstance" or cls_name.endswith("ForeignKeyField"):
        return "INTEGER"
    return None


async def sync_schema() -> None:
    from app.models import ai, crm, user  # noqa: F401

    conn = Tortoise.get_connection("default")
    models = [
        user.User,
        crm.Customer, crm.Contact, crm.Lead, crm.Deal, crm.Note,
        crm.Document, crm.Meeting, crm.Task, crm.Activity,
        ai.ChatSession, ai.ChatMessage, ai.EmailHistory, ai.Notification,
        ai.AuditLog, ai.Workflow, ai.WorkflowExecution,
    ]

    for model in models:
        table = model._meta.db_table
        existing = await conn.execute_query_dict(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            """,
            [table],
        )
        if not existing:
            continue

        existing_names = {r["column_name"] for r in existing}
        for name, field in model._meta.fields_map.items():
            col_name = getattr(field, "source_field", None) or name
            if col_name in existing_names or name in existing_names:
                continue
            sql_type = _sql_type(field)
            if not sql_type:
                continue
            default = ""
            ftype = type(field).__name__
            if ftype == "BooleanField":
                default = " DEFAULT FALSE"
            elif ftype == "IntField" and getattr(field, "default", None) is not None:
                default = f" DEFAULT {field.default}"
            elif ftype == "CharField" and field.default is not None:
                default = f" DEFAULT '{field.default}'"
            elif ftype == "JSONField":
                default = " DEFAULT '[]'::jsonb" if name in ("tags", "action_items", "participants", "steps") else " DEFAULT '{}'::jsonb"

            await conn.execute_query(f'ALTER TABLE "{table}" ADD COLUMN "{col_name}" {sql_type}{default}')
