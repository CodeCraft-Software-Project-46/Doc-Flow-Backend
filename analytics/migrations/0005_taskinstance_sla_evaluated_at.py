from django.db import migrations


def add_sla_evaluated_at_column(apps, schema_editor):
    """Add the audit column only when this database does not have it yet."""
    table_name = "analytics_task_instance"

    existing_tables = schema_editor.connection.introspection.table_names(
        schema_editor.connection.cursor()
    )
    if table_name not in existing_tables:
        # Fresh test database: the table doesn't exist yet at all. The
        # later 0006 migration creates it with this column already
        # included, so there's nothing for this migration to add.
        return

    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }

    if "sla_evaluated_at" not in existing_columns:
        schema_editor.execute(
            "ALTER TABLE analytics_task_instance "
            "ADD COLUMN sla_evaluated_at DATETIME(6) NULL"
        )


class Migration(migrations.Migration):
    """Add the SLA audit timestamp to the externally managed task table."""

    dependencies = [
        ("analytics", "0004_department_document_role_user"),
    ]

    operations = [
        migrations.RunPython(add_sla_evaluated_at_column, migrations.RunPython.noop),
    ]
