import uuid
from collections import defaultdict

from rest_framework import status
from rest_framework.views import APIView

from .serializers import UserSerializer, PermissionSerializer, RoleListSerializer, RoleSerializer, DepartmentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Role, Permission, RolePermission, User, Department


class GetAllPermissionsView(APIView):
    def get(self, request):
        permissions = Permission.objects.all()
        serializer = PermissionSerializer(permissions, many=True)

        return Response(serializer.data)


class SaveRoleView(APIView):
    def get(self, request):
        roles = Role.objects.prefetch_related("permissions")
        serializer = RoleListSerializer(roles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role created"}, status=201)

        return Response(serializer.errors, status=400)


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
class UpdateRoleView(APIView):
    def put(self,request,pk):
        try:
            pk=uuid.UUID(pk)
            role=Role.objects.get(id=pk)

        except role.DoesNotExist:
            return Response("Role not found", status=404)

        serializer = RoleSerializer(role, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response("Role updated successfully", status=200)

        return Response(serializer.errors, status=400)

class DeleteRoleView(APIView):
    def delete(self,request,pk):
        try:
            role=Role.objects.get(id=pk)
        except Role.DoesNotExist:
            return Response("Role not found", status=404)

        if role.users.exists():
            return Response("Cannot delete Role assigned to users",400)

        role.delete()
        return Response("Role deleted successfully", status=200)






class CreateUserView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response({
                "message": "User created",
                "temporary_password": getattr(user, "temp_password", None)
            }, status=201)

        return Response(serializer.errors, status=400)


class UpdateUserView(APIView):
    def put(self, request, pk):
        try:
            pk = uuid.UUID(pk)  # normalize
            print("pk ",pk)

            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        serializer = UserSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User updated successfully"})

        return Response(serializer.errors, status=400)


class DeleteUserView(APIView):
    def delete(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        if hasattr(user, "headed_role") and user.headed_role:
            role = user.headed_role
            role.head = None
            role.save()

        user.delete()

        return Response({"message": "User deleted successfully"}, status=200)

class GetUsersView(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class CreateDepartmentView(APIView):
    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Department created successfully"},201
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetDepartmentsView(APIView):
    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdateDepartmentView(APIView):
    def put(self, request, pk):
        try:
            pk = uuid.UUID(pk)  # normalize
            department = Department.objects.get(id=pk)
        except Department.DoesNotExist:
            return Response({"error": "Department not found"}, status=404)
        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Department updated successfully"})
        return Response(serializer.errors, status=400)

class DeleteDepartmentView(APIView):
    def delete(self, request, pk):
        try:
            department = Department.objects.get(id=pk)
        except Department.DoesNotExist:
            return Response({"error": "Department not found"}, status=404)
        if department.users.exists():
            return Response("Cannot delete Department. Users have assigned to it",400)
        department.delete()
        return Response({"message": "Department deleted successfully"}, status=200)





