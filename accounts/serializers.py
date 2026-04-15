# Serializers are acting as translators between Django(Python) and React(JavaScript).

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class LoginSerializer(serializers.Serializer): # Used to receive Data from the Frontend.
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