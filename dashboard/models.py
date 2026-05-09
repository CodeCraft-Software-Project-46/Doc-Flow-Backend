from django.db import models

from user.models import Permission, Role

class Dashboard(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ]

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="dashboards"
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Widget(models.Model):
    id = models.AutoField(primary_key=True)

    widget_code = models.CharField(max_length=50, unique=True)  # W001
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    min_width = models.IntegerField(default=2)
    max_width = models.IntegerField(default=6)
    min_height = models.IntegerField(default=2)
    max_height = models.IntegerField(default=6)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.widget_code} - {self.name}"


class DashboardWidget(models.Model):
    id = models.AutoField(primary_key=True)

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="dashboard_widgets"
    )

    widget = models.ForeignKey(
        Widget,
        on_delete=models.CASCADE
    )
    widget_code = models.CharField(max_length=50)
    category=models.CharField(max_length=100)
    pos_x = models.IntegerField()
    pos_y = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()

    class Meta:
        unique_together = ('dashboard', 'widget')


class WidgetPermission(models.Model):
    id = models.AutoField(primary_key=True)

    widget = models.ForeignKey(Widget, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('widget', 'permission')