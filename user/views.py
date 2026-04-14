from django.db import connection, transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from user.utils import generate_role_id


class GetAllPermissionsView(APIView):
    def get(self, request):
        try:
       # open database connection - with(after using automatically closed the connection)

            with connection.cursor() as cursor:

                cursor.execute("SELECT permission_id, permission_name, category FROM permission")
                #fetch all data
                rows = cursor.fetchall()

            grouped_permissions = {} #empty dictionary
            for row in rows:
                p_id, p_name, category = row

                if category not in grouped_permissions:
                    grouped_permissions[category] = []

                grouped_permissions[category].append({
                    "id": p_id,
                    "name": p_name
                })

            return Response(grouped_permissions, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class SaveRoleView(APIView):
    def post(self, request):
        #get inputs
        name = request.data.get('name')
        description = request.data.get('description')
        permissions = request.data.get('permissions')

        if not name:
            return Response({"error": "Role name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                #gerate new id
                role_id = generate_role_id()

                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO workflows_role (id, name, description, created_at) VALUES (%s, %s, %s, NOW())",
                        [role_id, name, description]
                    )

                    if permissions and isinstance(permissions, list):
                        for p_id in permissions:
                            cursor.execute(
                                "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s)",
                                [role_id, p_id]
                            )

            return Response({
                "message": "Role and permissions saved successfully!",
                "role_id": role_id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)