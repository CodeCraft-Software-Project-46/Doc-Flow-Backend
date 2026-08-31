import re
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from django.utils.crypto import get_random_string

from user.models import Permission, Role, Department, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["permission_id", "permission_name", "permission_description", "category"]





class UserSerializer(serializers.ModelSerializer):
   # password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            #"username",
            "name",
            "email",
            "contact_number",
            "address",
            "role",
            #"password",
        ]


    def validate_username(self, value):
        #if not value or not value.strip():
            #raise serializers.ValidationError("Username is required.")

        # uniqueness (handle update)
        #user_id = self.instance.id if self.instance else None
        #if User.objects.filter(username=value).exclude(id=user_id).exists():
            #raise serializers.ValidationError("Username already exists.")

        return True

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Email already exists.")

        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")

        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Email already exists.")

        return value

    def validate_contact_number(self, value):
        if not value:
            raise serializers.ValidationError("Contact number is required.")


        if not re.match(r"^\d{10}$", value):
            raise serializers.ValidationError(
                "Enter a valid 10-digit contact number."
            )

        return value

    def validate_address(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Address is required.")
        return value


    def validate(self, attrs):
        role = attrs.get("role")

        if not role:
            raise serializers.ValidationError({"role": "Role is required."})

        # Only one user per role
        existing_user = User.objects.filter(role=role).first()
        if existing_user:
            if not self.instance or existing_user.id != self.instance.id:
                raise serializers.ValidationError({
                    "role": "This role is already assigned to another user."
                })

        return attrs

    def create(self, validated_data):
        #temp_password = get_random_string(10)
        user = User(**validated_data)
        #user.set_password(temp_password)
        temp_username = get_random_string(10)
        user.username = temp_username
        user.save()

        #user.temp_password = temp_password
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        slug_field="permission_name"
    )

    class Meta:
        model = Role
        fields = ["id", "name", "description", "department", "permissions"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Role name is required.")

        if len(value.strip()) < 2:
            raise serializers.ValidationError("Role name must be at least 2 characters.")

        role_id = self.instance.id if self.instance else None
        if Role.objects.filter(name__iexact=value.strip()).exclude(id=role_id).exists():
            raise serializers.ValidationError("Role already exists.")

        return value.strip()

    def validate_description(self, value):
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError("Description must be at least 3 characters.")
        return value.strip() if value else value

    def validate(self, attrs):
        permissions = attrs.get("permissions")
        department = attrs.get("department")

        if not department:
            raise serializers.ValidationError({
                "department": "Department is required."
            })

        if not permissions or len(permissions) == 0:
            raise serializers.ValidationError({
                "permissions": "At least one permission is required."
            })

        return attrs

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        role = Role.objects.create(**validated_data)
        role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)

        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.department = validated_data.get("department", instance.department)
        instance.save()

        if permissions is not None:
            instance.permissions.set(permissions)

        return instance

class RoleListSerializer(serializers.ModelSerializer):
    permissions = serializers.StringRelatedField(many=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]

class DepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = ["id", "name", "description"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Department name is required.")

        if len(value.strip()) < 2:
            raise serializers.ValidationError("Department name must be at least 2 characters.")

        department_id = self.instance.id if self.instance else None
        if Department.objects.filter(name__iexact=value.strip()).exclude(id=department_id).exists():
            raise serializers.ValidationError("Department already exists.")

        return value.strip()

    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description is required.")

        if len(value.strip()) < 3:
            raise serializers.ValidationError("Description must be at least 3 characters.")

        return value.strip()


