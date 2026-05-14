import uuid
from django.db import models


class Permission(models.Model):
    permission_id = models.AutoField(primary_key=True)
    permission_name = models.CharField(max_length=255)
    permission_description=models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.permission_name

class Department(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=100, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank = True
    )


    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name="roles"
    )

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)





class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    name = models.CharField(max_length=150, blank=True)
    username=models.CharField(max_length=20,unique=True)
    role = models.OneToOneField(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
