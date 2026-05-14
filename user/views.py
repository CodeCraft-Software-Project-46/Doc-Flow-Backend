import uuid

from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from rest_framework import status


from .serializers import UserSerializer, PermissionSerializer, RoleListSerializer, RoleSerializer, DepartmentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Role, Permission, User, Department
from .utils import send_user_credentials
from django.apps import apps

AuthUser = apps.get_model('auth', 'User')
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
    def put(self, request, pk):
        try:
            pk = uuid.UUID(pk)
            role = Role.objects.get(id=pk)

        except Role.DoesNotExist:
            return Response("Role not found", status=404)

        serializer = RoleSerializer(role, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response("Role updated successfully", status=200)

        return Response(serializer.errors, status=400)
class DeleteRoleView(APIView):
    def delete(self, request, pk):
        try:
            pk = uuid.UUID(pk)
            role = Role.objects.get(id=pk)
        except Role.DoesNotExist:
            return Response({"message": "Role not found"}, status=404)

        # If user is assigned, remove role from user
        if hasattr(role, "user") and role.user:
            user = role.user
            user.role = None
            user.save()

        role.delete()

        return Response({"message": "Role deleted successfully"}, status=200)


class CreateUserView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        temp_password = get_random_string(10)


        if serializer.is_valid():

            user = serializer.save()

            AuthUser.objects.create(
                username=user.username,
                email=user.email,
                password=make_password(temp_password),
                is_active=True
            )

            send_user_credentials(user,temp_password)
            return Response({
                "message": "User created",
                "temporary_password": getattr(user, "temp_password", None)
            }, status=201)

        return Response(serializer.errors, status=400)


class UpdateUserView(APIView):
    def put(self, request, pk):
        try:
            pk = uuid.UUID(pk)
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

        return Response(serializer.data)





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

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Department, User


class DeleteDepartmentView(APIView):
    def delete(self, request, pk):
        try:
            department = Department.objects.get(id=pk)
        except Department.DoesNotExist:
            return Response({"error": "Department not found"}, status=404)

        # ✅ CHECK THROUGH ROLE → USER RELATION
        has_users = User.objects.filter(
            role__department=department
        ).exists()

        if has_users:
            return Response(
                {"error": "Cannot delete department. Users are assigned to roles."},
                status=400
            )

        department.delete()
        return Response(
            {"message": "Department deleted successfully"},
            status=200
        )





