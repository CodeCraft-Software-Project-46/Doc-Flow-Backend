from django.contrib import admin
from .external_models import Role, Permission, RolePermission

# Registering these allows you to edit the AWS workflow tables 
# directly from the Notifications section of the Django Admin!
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)