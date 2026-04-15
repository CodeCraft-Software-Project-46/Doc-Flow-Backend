# Views.py is where we write the logic for handling incoming requests and sending responses back to the frontend.

from rest_framework.views import APIView
from rest_framework.response import Response # To send data back to React Frontend.
from rest_framework import status
from rest_framework.permissions import IsAuthenticated # To check if the user is allowed to use the route.(Valid Token Check)
from rest_framework_simplejwt.tokens import RefreshToken  # Generate Tokens for User
from .serializers import LoginSerializer, UserProfileSerializer


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
        
        # We can attach the user's role and username directly to the token so 
        # frontend can read it without making an extra API call to get the user's profile. 
        # This is optional but can save time and reduce the number of requests.
        access_token['role'] = user.role.name if user.role else 'No Role'
        access_token['username'] = user.username

        # 4. Get the Welcome Package (User Profile)
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