import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Permission(models.Model):
    permission_id = models.AutoField(primary_key=True)
    permission_name = models.CharField(max_length=255)
    permission_description=models.CharField(max_length=255)
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.permission_name


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default="")
    head = models.OneToOneField(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_role"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    permissions = models.ManyToManyField(Permission, through='RolePermission')

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

class Department(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    name = models.CharField(max_length=150, blank=True)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, related_name="users")
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, related_name="users")

    def __str__(self):
        return self.username
