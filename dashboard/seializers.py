from rest_framework import serializers
from .models import Widget, Dashboard, DashboardWidget


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = [
            "id",
            "widget_code",
            "name",
            "category",
            "min_width",
            "max_width",
            "min_height",
            "max_height",
        ]

class DashboardWidgetSerializer(serializers.ModelSerializer):

    widget_code = serializers.CharField(source="widget.widget_code", read_only=True)
    name = serializers.CharField(source="widget.name", read_only=True)
    category = serializers.CharField(source="widget.category", read_only=True)

    class Meta:
        model = DashboardWidget
        fields = [
            "id",
            "widget",
            "widget_code",
            "name",
            "category",
            "pos_x",
            "pos_y",
            "width",
            "height",
        ]


class DashboardSerializer(serializers.ModelSerializer):

    widgets = DashboardWidgetSerializer(
        source="dashboard_widgets",
        many=True,
        read_only=True
    )

    class Meta:
        model = Dashboard
        fields = [
            "id",
            "name",
            "description",
            "status",
            "role",
            "created_at",
            "widgets",
        ]