from __future__ import annotations

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from workflows.models import Department, Role, UserProfile


DEMO_SETUP = [
    ("Engineering", "Engineer", "user1"),
    ("Finance", "Finance Officer", "user2"),
    ("Procurement", "Procurement Officer", "user3"),
    ("Legal", "Legal Officer", "user4"),
    ("Operations", "Operations Manager", "user5"),
]


class Command(BaseCommand):
    help = "Seed demo departments, roles, and users for role-based workflow testing"

    def handle(self, *args, **options):
        for department_name, role_name, username in DEMO_SETUP:
            department, _ = Department.objects.get_or_create(name=department_name)
            role, _ = Role.objects.get_or_create(
                department=department,
                name=role_name,
                defaults={"description": f"{role_name} role for workflow testing"},
            )

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@docflow.local",
                    "is_active": True,
                },
            )
            if created:
                user.set_password("1234")
                user.save(update_fields=["password"])

            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.role_id != role.id:
                profile.role = role
                profile.save(update_fields=["role", "updated_at"])

            if not role.users.filter(id=user.id).exists():
                role.users.add(user)

            self.stdout.write(self.style.SUCCESS(f"Seeded {department_name} / {role_name} / {username}"))

        self.stdout.write(self.style.SUCCESS("Demo workflow user seed complete."))
