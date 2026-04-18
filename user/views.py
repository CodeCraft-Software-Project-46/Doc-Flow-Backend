

from collections import defaultdict
from rest_framework.views import APIView



class GetAllPermissionsView(APIView):
    def get(self, request):
        try:
            permissions = Permission.objects.all()

            grouped_permissions = defaultdict(list)

            for p in permissions:
                grouped_permissions[p.category].append({
                    "id": p.permission_id,
                    "name": p.permission_name
                })

            return Response(grouped_permissions, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Role, Permission, RolePermission


class SaveRoleView(APIView):
    def post(self, request):
        name = request.data.get('name')
        description = request.data.get('description')
        permissions = request.data.get('permissions', [])

        if not name:
            return Response(
                {"error": "Role name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(permissions, list):
            return Response(
                {"error": "Permissions must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():

                role = Role.objects.create(
                    name=name,
                    description=description
                )

                permission_objs = list(
                    Permission.objects.filter(
                        permission_name__in=permissions
                    )
                )

                found_names = {p.permission_name for p in permission_objs}

                missing = set(permissions) - found_names
                if missing:
                    return Response(
                        {
                            "error": "Invalid permissions found",
                            "missing": list(missing)
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                RolePermission.objects.bulk_create([
                    RolePermission(role=role, permission=p)
                    for p in permission_objs
                ])

            return Response({
                "message": "Role created successfully"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class GetAllRolesView(APIView):
    def get(self, request):
        try:
            roles = Role.objects.prefetch_related('permissions').all()

            data = []

            for role in roles:
                data.append({
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                    "permissions": list(
                        role.permissions.values_list(
                            "permission_name",
                            flat=True
                        )
                    )
                })

            return Response(data, status=200)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=500
            )