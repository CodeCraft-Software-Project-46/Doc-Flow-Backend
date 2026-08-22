from django.db import migrations


def drop_time_zone_column_if_present(apps, schema_editor):
    """
    Drop the column only if it's actually there.

    On the real shared database the column was already dropped manually
    (outside Django's migration history) once the team decided the system
    only ever runs in Sri Lanka — there, this is a no-op. On a database
    built fresh from migration 0001 onward (a test database, a new
    developer's local setup), the column still physically exists and needs
    to be dropped here so the table matches the current model.
    """

    table_name = "working_hoursconfig"
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }

    if "time_zone" in existing_columns:
        schema_editor.execute(
            "ALTER TABLE working_hoursconfig DROP COLUMN time_zone"
        )


class Migration(migrations.Migration):
    """
    Remove WorkingHoursConfig.time_zone.
    """

    dependencies = [
        ("working_hours", "0002_alter_workinghoursconfig_table"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="workinghoursconfig",
                    name="time_zone",
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    drop_time_zone_column_if_present,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
