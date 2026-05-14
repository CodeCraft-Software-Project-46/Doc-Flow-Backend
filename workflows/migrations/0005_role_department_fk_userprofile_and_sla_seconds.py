# Generated manually for department-role normalization and profile support.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_role_departments(apps, schema_editor):
    Role = apps.get_model("workflows", "Role")
    Department = apps.get_model("workflows", "Department")

    for role in Role.objects.all():
        raw_name = (getattr(role, "department", "") or "").strip()
        if not raw_name:
            continue
        department, _ = Department.objects.get_or_create(name=raw_name)
        role.department_ref_id = department.id
        role.save(update_fields=["department_ref"])


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("workflows", "UserProfile")

    existing_user_ids = set(UserProfile.objects.values_list("user_id", flat=True))
    for user in User.objects.all():
        if user.id not in existing_user_ids:
            UserProfile.objects.create(user_id=user.id)


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0004_role_department"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="role",
            name="department_ref",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="roles", to="workflows.department"),
        ),
        migrations.RunPython(migrate_role_departments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="role",
            name="department",
        ),
        migrations.RenameField(
            model_name="role",
            old_name="department_ref",
            new_name="department",
        ),
        migrations.AlterField(
            model_name="role",
            name="name",
            field=models.CharField(max_length=120),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(fields=("department", "name"), name="unique_role_name_per_department"),
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_profiles", to="workflows.role")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["user__username"],
            },
        ),
        migrations.RunPython(create_missing_profiles, migrations.RunPython.noop),
        migrations.AddField(
            model_name="taskinstance",
            name="sla_seconds",
            field=models.IntegerField(default=5),
        ),
    ]
