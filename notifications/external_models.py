from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        managed = False 
        db_table = 'workflows_role' 

    def __str__(self):
        return self.name

class Permission(models.Model):
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False 
        db_table = 'user_permission' # <--- THE FIX IS HERE!

    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.DO_NOTHING)
    permission = models.ForeignKey(Permission, on_delete=models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'user_rolepermission' # <--- AND HERE!