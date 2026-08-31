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

        # CHECK EXISTING DASHBOARDS FOR ROLE
        dashboard_count = Dashboard.objects.filter(
            role=role
        ).count()

        # AUTO STATUS
        dashboard_status = (
            "active"
            if dashboard_count == 0
            else "draft"
        )

        # CREATE DASHBOARD
        dashboard = Dashboard.objects.create(

            name=data.get("name"),

            description=data.get(
                "description",
                ""
            ),

            role=role,

            status=dashboard_status,
        )

        widgets = data.get("widgets", [])

        # SAVE WIDGETS
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

            "dashboard_id": dashboard.id,

            "status": dashboard.status

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

class ChangeDashboardStatus(APIView):

    def put(self, request, dashboard_id):

        try:
            dashboard = Dashboard.objects.get(id=dashboard_id)
        except Dashboard.DoesNotExist:
            return Response({"error": "Dashboard not found"}, status=404)

        new_status = request.data.get("status")

        if new_status == "active":

            Dashboard.objects.filter(
                role=dashboard.role
            ).exclude(id=dashboard.id).update(status="disabled")

            dashboard.status = "active"
            dashboard.save()

            return Response({
                "message": "Dashboard activated",
                "dashboard_id": dashboard.id,
                "status": dashboard.status
            })


        if new_status == "disabled":

            role_dashboards = Dashboard.objects.filter(
                role=dashboard.role
            )

            # only one dashboard exists , block disable
            if role_dashboards.count() == 1:
                return Response({
                    "error": "Cannot disable the only dashboard. At least one active dashboard is required."
                }, status=400)

            # disable current
            dashboard.status = "disabled"
            dashboard.save()

            # ensure one remains active
            active_exists = Dashboard.objects.filter(
                role=dashboard.role,
                status="active"
            ).exists()

            if not active_exists:

                fallback = role_dashboards.exclude(id=dashboard.id).first()

                if fallback:
                    fallback.status = "active"
                    fallback.save()

            return Response({
                "message": "Dashboard disabled",
                "dashboard_id": dashboard.id,
                "status": dashboard.status
            })

        return Response({"error": "Invalid status"}, status=400)

class DeleteDashboard(APIView):

    def delete(self, request, dashboard_id):

        try:
            dashboard = Dashboard.objects.get(id=dashboard_id)
        except Dashboard.DoesNotExist:
            return Response({"error": "Dashboard not found"}, status=404)

        role = dashboard.role
        # IF DASHBOARD IS ACTIVE

        if dashboard.status == "active":

            fallback = Dashboard.objects.filter(
                role=role
            ).exclude(id=dashboard.id).first()

            # no fallback available → block delete
            if not fallback:
                return Response({
                    "error": "Cannot delete the only active dashboard for this role.",
                    "hint": "Create another dashboard first."
                }, status=400)

            # promote fallback to active
            fallback.status = "active"
            fallback.save()

        # delete
        dashboard.delete()

        return Response({
            "message": "Dashboard deleted successfully"
        })


class GetActiveDashboard(APIView):

    def get(self, request, role_id):

        dashboard = Dashboard.objects.filter(
            role_id=role_id,
            status="active"
        ).first()

        if not dashboard:
            return Response(
                {"error": "No active dashboard"},
                status=404
            )

# to get  widgets related to dashboard object
        widgets = DashboardWidget.objects.filter(
            dashboard=dashboard
        )

        return Response({
            "id": dashboard.id,
            "name": dashboard.name,
            "widgets": list(widgets.values())
        })