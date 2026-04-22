# Views.py is where we write the logic for handling incoming requests and sending responses back to the frontend.
# from workflows.models import Role

from audits.utils import log_action
from rest_framework.views import APIView
from rest_framework.response import Response # To send data back to React Frontend.
from rest_framework import status
from rest_framework.permissions import IsAuthenticated # To check if the user is allowed to use the route.(Valid Token Check)
from rest_framework_simplejwt.tokens import RefreshToken  # Generate Tokens for User
from .serializers import LoginSerializer, UserProfileSerializer
from .serializers import UserProvisioningSerializer
from .permissions import HasDynamicPermission 
from django.db import connection


class LoginView(APIView):
    # Anyone can try to log in, so no permission checks yet
    permission_classes = [] 

    def post(self, request):
        # 1. Hand data to the Bouncer
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            # Log the failed login attempt in the audit log.
            attempted_username = request.data.get('username', 'Unknown')
            log_action(
                action='LOGIN_FAILED',
                description=f"Failed login attempt for username: {attempted_username}"
            )
            # Bouncer says no! Return the error to the user.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Bouncer says yes: Grab the verified user from the serializer's validated_date Dictonary.
        user = serializer.validated_data['user']
        
        # 3. Get the Tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        


       

        try:
            with connection.cursor() as cursor:
                # 1. Fetch the Role and Permissions directly from SQL
                # This query finds the role name and all 24 permission names at once
                query = """
                    SELECT ur.name, up.permission_name
                    FROM user_user uu
                    JOIN user_role ur ON uu.role_id = ur.id
                    JOIN user_rolepermission urp ON ur.id = urp.role_id
                    JOIN user_permission up ON urp.permission_id = up.permission_id
                    WHERE uu.username = %s
                """
                cursor.execute(query, [user.username])
                rows = cursor.fetchall()

                if rows:
                    role_name = rows[0][0]
                    permissions_list = [row[1] for row in rows]
                    
                    access_token['roles'] = [role_name]
                    access_token['permissions'] = permissions_list
                else:
                    # If the query returned nothing
                    access_token['roles'] = ['Guest']
                    access_token['permissions'] = ['can_view_dashboard']

            access_token['username'] = user.username

        except Exception as e:
            print(f"Direct SQL Error: {e}")
            access_token['roles'] = ['Guest']
            access_token['permissions'] = ['can_view_dashboard']

        user_data = UserProfileSerializer(user).data

        # Log the successful login in the audit log
        log_action(
            action='LOGIN',
            user=user,
            description=f"User {user.username} logged in successfully."
        )

        # 5. Deliver it all back to the frontend
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': user_data,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    # You must be logged in to log out!
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Blacklist the token so a hacker can't steal it and use it later
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    # A simple route for React to check "Who am I?" when the page refreshes
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    


class UserProvisioningView(APIView):
    # 1. THE LOCK: Only someone with the 'can_add_user' permission can do this!
    permission_classes = [HasDynamicPermission]
    required_permission = 'can_add_user'

    def post(self, request):
        serializer = UserProvisioningSerializer(data=request.data)
        
        if serializer.is_valid():
            # This triggers the create() method in our serializer
            user = serializer.save() 
            
            # We respond with the auto-generated password so the Admin UI can display it
            return Response({
                "message": "User created successfully.",
                "user": {
                    "email": user.email,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "department": user.profile.department,
                },
                "temp_password": user.temp_password 
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)