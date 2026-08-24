from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0006_create_task_instance_table_for_tests"),
    ]

    operations = [
        migrations.CreateModel(
            name="BottleneckScoreWeights",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time_weight", models.FloatField(default=0.45)),
                ("breach_weight", models.FloatField(default=0.45)),
                ("volume_weight", models.FloatField(default=0.10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "analytics_bottleneck_score_weights",
            },
        ),
    ]
