from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Dashboard, Widget, DashboardWidget, WidgetPermission


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "role", "status")


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ("id", "widget_code", "name")


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ("dashboard", "widget", "pos_x", "pos_y")


@admin.register(WidgetPermission)
class WidgetPermissionAdmin(admin.ModelAdmin):
    list_display = ("widget", "permission")