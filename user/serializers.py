from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from user.models import Permission, Role, Department

User = get_user_model()

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["permission_id", "permission_name", "permission_description", "category"]

class UserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, required=False)
    is_lead = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "contact_number",
            "address",
            "role",
            "department",
            "password",
            "is_lead"
        ]


    def create(self, validated_data):
        validated_data.pop("is_lead", None)

        temp_password = get_random_string(10)

        user = User(**validated_data)
        user.set_password(temp_password)
        user.save()

        user.temp_password = temp_password
        return user

    def update(self, instance, validated_data):
        is_lead = validated_data.pop("is_lead", None)
        password = validated_data.pop("password", None)

        old_role = instance.role


        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()


        if old_role and old_role != instance.role:
            if old_role.head == instance:
                old_role.head = None
                old_role.save()


        if is_lead is not None:
            role = instance.role

            if not role:
                raise serializers.ValidationError({
                    "error": "User must have a role to be a lead"
                })

            if is_lead:
                if role.head and role.head != instance:
                    raise serializers.ValidationError({
                        "error": "This role already has a lead. Remove current lead first."
                    })

                role.head = instance
                role.save()

            else:

                if role.head == instance:
                    role.head = None
                    role.save()

        return instance



class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        slug_field="permission_name"
    )

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        role = Role.objects.create(**validated_data)
        role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)

        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
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
        fields = ["id", "name"]
