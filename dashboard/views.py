from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.models import Widget, DashboardWidget, Dashboard
from dashboard.seializers import WidgetSerializer, DashboardSerializer
from user.models import Role


class GetAccessibleWidgets(APIView):

    def get(self, request,role_id):

        print(role_id)
        if not role_id:
            return Response(
                {"error": "role_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response(
                {"error": "Role not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        widgets = Widget.objects.filter(
            widgetpermission__permission__roles=role
        ).distinct()

        serializer = WidgetSerializer(widgets, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class SaveDashboard(APIView):

    def post(self, request):

        data = request.data

        role = Role.objects.get(
            id=data.get("role_id")
        )

        dashboard = Dashboard.objects.create(
            name=data.get("name"),
            description=data.get("description", ""),
            role=role,
            status=data.get("status", "draft"),
        )

        widgets = data.get("widgets", [])

        for w in widgets:

            widget_obj = Widget.objects.get(
                widget_code=w["widget_code"]
            )

            DashboardWidget.objects.create(
                dashboard=dashboard,
                widget=widget_obj,

                widget_code=widget_obj.widget_code,
                category=widget_obj.category,

                pos_x=w["pos_x"],
                pos_y=w["pos_y"],

                width=w["width"],
                height=w["height"],
            )

        return Response({
            "message": "Dashboard created",
            "dashboard_id": dashboard.id
        })
class UpdateDashboard(APIView):

    def put(self, request, id):

        data = request.data

        dashboard = Dashboard.objects.get(id=id)

        role = Role.objects.get(
            id=data.get("role_id")
        )

        dashboard.name = data.get("name")
        dashboard.description = data.get("description", "")
        dashboard.status = data.get("status", dashboard.status)
        dashboard.role = role

        dashboard.save()

        DashboardWidget.objects.filter(
            dashboard=dashboard
        ).delete()

        widgets = data.get("widgets", [])

        for w in widgets:

            widget_obj = Widget.objects.get(
                widget_code=w["widget_code"]
            )

            DashboardWidget.objects.create(
                dashboard=dashboard,
                widget=widget_obj,

                widget_code=widget_obj.widget_code,
                category=widget_obj.category,

                pos_x=w["pos_x"],
                pos_y=w["pos_y"],

                width=w["width"],
                height=w["height"],
            )

        return Response({
            "message": "Dashboard updated"
        })
class GetDashboardList(APIView):

    def get(self, request):
        dashboards = Dashboard.objects.all()

        data = []

        for d in dashboards:
            data.append({
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "role_id": str(d.role_id),
                "status": d.status,
            })

        return Response(data)

class GetDashboard(APIView):

    def get(self, request, dashboard_id):

        dashboard = Dashboard.objects.get(id=dashboard_id)

        widgets = DashboardWidget.objects.filter(dashboard=dashboard)

        return Response({
            "id": dashboard.id,
            "name": dashboard.name,
            "description": dashboard.description,
            "role_id": str(dashboard.role_id),
            "status": dashboard.status,

            "widgets": [
                {
                    "id": w.widget.id,
                    "widget_code": w.widget.widget_code,
                    "name": w.widget.name,
                    "category": w.category,
                    "pos_x": w.pos_x,
                    "pos_y": w.pos_y,
                    "width": w.width,
                    "height": w.height,
                }
                for w in widgets
            ]
        })