# Serializers are acting as translators between Django(Python) and React(JavaScript) 
# and to Validate the data that the frontend sends us. 
# They also help us to control exactly what data we send back to the frontend, and how we format it.

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import UserProfile
from django.utils.crypto import get_random_string

class LoginSerializer(serializers.Serializer): # Used to validate the login credentials that the frontend sends.
    # We expect the frontend to send us a username and password when try to log in, so we define those fields here
    username = serializers.CharField()
    password = serializers.CharField(write_only=True) # write_only means, we NEVER send the password back to the frontend

    def validate(self, data):
        username = data.get('username') # We get the username from the data that the frontend sent us
        password = data.get('password') # We get the password from the data that the frontend sent us

        # authenticate() checks the database to see if this username and password hash match(Built-in Function In Django)
        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid username or password. Please try again.")

        # in enterprice systems, we never delete retired, left users cuz we need to keep their data for historical purposes, 
        # so instead of deleting them, we just deactivate their accounts. So we need to check if the account is active or not.
        if not user.is_active:
            raise serializers.ValidationError("Your account has been deactivated.")

        # If we get here, it means the username and password are correct, and the account is active. We can return the user object to the view.
        data['user'] = user
        return data

class UserProfileSerializer(serializers.ModelSerializer): # Used to send data to the Frontend.
    department = serializers.CharField(source='profile.department', read_only=True)

    class Meta:
        model = User
        # These are the exact fields we will send back to React upon a successful login
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'department']

class UserProvisioningSerializer(serializers.Serializer): # used to receive data from the Frontend when creating a new user.
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    role = serializers.CharField(max_length=50) # We will link this to roles tables later
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def create(self, validated_data):
        # 1. Split the "Full Name" into First and Last for Django
        names = validated_data['full_name'].strip().split(' ', 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ''

        # 2. Generate a temporary password (12 characters, secure)
        temp_password = get_random_string(length=12)

        # 3. Create the User (In enterprise apps, Username is usually the Email)
        user = User.objects.create_user(
            username=validated_data['email'], 
            email=validated_data['email'],
            password=temp_password,
            first_name=first_name,
            last_name=last_name
        )

        # 4. Create the UserProfile linked to this User
        UserProfile.objects.create(
            user=user, 
            department=validated_data.get('department', '')
        )

        # We attach the temp password to the user object temporarily 
        # so our View can read it and send it back to the Admin!
        user.temp_password = temp_password 
        return user