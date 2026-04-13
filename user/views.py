from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


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