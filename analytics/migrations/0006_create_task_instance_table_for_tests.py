from django.db import migrations, models


def create_task_instance_table_if_missing(apps, schema_editor):
    """
    TaskInstance is `managed = False` because the table is owned by another
    part of the system in real deployments, so Django's migrations never
    create it there (by design) — but that also means a *fresh* test
    database (sqlite in CI, or a freshly-created MySQL test DB) has no such
    table at all, which makes every DB-backed SLA test unrunnable.

    This creates a table with the columns the SLA engine actually reads and
    writes, only when the table doesn't already exist (so it's a no-op
    against any database, like the real shared one, where the table is
    already present). It's a plain standalone table rather than the real
    `analytics.models.TaskInstance` for two reasons: that model's migration
    history predates several of its current fields (managed=False models
    never needed migrations to keep the real database in sync, so the
    historical migration state has drifted from models.py), and its
    `workflow_instance` foreign key targets another managed=False model
    that doesn't have a real table here either. Neither the drifted fields
    nor the FK relation are exercised by the SLA code paths under test.
    """

    table_name = "analytics_task_instance"
    existing_tables = schema_editor.connection.introspection.table_names(
        schema_editor.connection.cursor()
    )

    if table_name in existing_tables:
        return

    class TestOnlyTaskInstance(models.Model):
        task_id = models.AutoField(primary_key=True)
        workflow_instance_id = models.IntegerField()
        task_name = models.CharField(max_length=255, null=True)
        created_at = models.DateTimeField()
        status = models.CharField(max_length=50)
        due_at = models.DateTimeField(null=True, blank=True)
        assigned_role_id = models.IntegerField(null=True)
        sla_hours = models.FloatField()
        completed_at = models.DateTimeField(null=True)
        sla_status = models.CharField(max_length=50, null=True)
        sla_evaluated_at = models.DateTimeField(null=True, blank=True)

        class Meta:
            app_label = "analytics"
            db_table = table_name

    schema_editor.create_model(TestOnlyTaskInstance)


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0005_taskinstance_sla_evaluated_at"),
    ]

    operations = [
        migrations.RunPython(
            create_task_instance_table_if_missing,
            # Intentionally a no-op on reverse: this table is externally
            # owned in real deployments, and unmigrating must never risk
            # dropping the real one. A table this migration itself created
            # in a throwaway test database is discarded with the database.
            migrations.RunPython.noop,
        ),
    ]
