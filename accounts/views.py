# Views.py is where we write the logic for handling incoming requests and sending responses back to the frontend.
# from workflows.models import Role

from rest_framework.views import APIView
from rest_framework.response import Response # To send data back to React Frontend.
from rest_framework import status
from rest_framework.permissions import IsAuthenticated # To check if the user is allowed to use the route.(Valid Token Check)
from rest_framework_simplejwt.tokens import RefreshToken  # Generate Tokens for User
from .serializers import LoginSerializer, UserProfileSerializer
from .serializers import UserProvisioningSerializer
from .permissions import HasDynamicPermission 



class LoginView(APIView):
    # Anyone can try to log in, so no permission checks yet
    permission_classes = [] 

    def post(self, request):
        # 1. Hand data to the Bouncer
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            # Bouncer says no! Return the error to the user.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Bouncer says yes: Grab the verified user from the serializer's validated_date Dictonary.
        user = serializer.validated_data['user']
        
        # 3. Get the Tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        


        # 4.1. Find all roles attached to this specific user
        #user_roles = Role.objects.filter(users=user)

        # 4.2. Extract just the names of the roles into a list: ['Admin', 'Manager']
        #role_names = list(user_roles.values_list('name', flat=True))

        # 4.3. Extract all unique permissions attached to those roles: ['can_approve', 'can_edit']
        #permissions_list = list(user_roles.values_list('permissions__name', flat=True).distinct())

        # 4.4. Clean up any empty values just in case a role has no permissions
        #permissions_list = [p for p in permissions_list if p is not None]

        # 4.5. Pack them securely into the access token
        access_token['username'] = user.username
        access_token['roles'] = ['Super Admin']   # = role_names
        access_token['permissions'] = ['can_view_dashboard']  # = permissions_list

        user_data = UserProfileSerializer(user).data

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