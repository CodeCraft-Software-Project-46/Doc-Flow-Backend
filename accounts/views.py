# Views.py is where we write the logic for handling incoming requests and sending responses back to the frontend.
# from workflows.models import Role

from audits.utils import log_action
from rest_framework.views import APIView
from rest_framework.response import Response # To send data back to React Frontend.
from rest_framework import status
from rest_framework.permissions import IsAuthenticated # To check if the user is allowed to use the route.(Valid Token Check)
from rest_framework_simplejwt.tokens import RefreshToken  # Generate Tokens for User
from .serializers import LoginSerializer, UserProfileSerializer
from django.db import connection
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import update_session_auth_hash
from .models import UserData

class LoginView(APIView):
    # Anyone can try to log in, so no permission checks yet
    permission_classes = [] 

    def post(self, request):
        # 1. Hand data to the Serializer for validation and authentication.
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            # Log the failed login attempt in the audit log.
            attempted_username = request.data.get('username', 'Unknown')
            log_action(
                action='LOGIN_FAILED',
                description=f"Failed login attempt for username: {attempted_username}"
            )
            # Serializer says no! Return the error to the user.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Serializer says yes: Grab the verified user from the serializer's validated_date Dictonary.
        user = serializer.validated_data['user']
        
        # 3. Get the Tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        try:
            with connection.cursor() as cursor:
                # Direct query using the custom user_user table for roles and permissions
                query = """
                    SELECT ur.name as role_name, up.permission_name
                    FROM auth_user au
                    JOIN user_user uu ON au.username = uu.username  -- FIX: Match on username instead of id
                    JOIN user_role ur ON uu.role_id = ur.id
                    JOIN user_rolepermission urp ON ur.id = urp.role_id
                    JOIN user_permission up ON urp.permission_id = up.permission_id
                    WHERE au.username = %s
                """
                cursor.execute(query, [user.username])
                rows = cursor.fetchall()

                if rows:
                    access_token['roles'] = [rows[0][0]] # Role Name
                    access_token['permissions'] = list(set([row[1] for row in rows])) # Attach all unique permissions for that role to the token
                else:
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
    

class PasswordResetRequestView(APIView):
    permission_classes = []  # Publicly accessible

    # If the user successfully resets their password, the hash changes, 
    # which automatically makes this token invalid so it can't be used again.

    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        
        if user:
            # 1. Generate Token and UID
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # 2. Build the React Frontend Link
            # Note: Point this to your React domain, not the Django API
            reset_link = f"http://localhost:5173/reset-password/{uid}/{token}/"
            
            # 3. Send the Email using existing settings
            send_mail(
                subject="DocFlow Password Reset",
                message=f"Click the link to reset your password: {reset_link}",
                from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings.py
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # 4. Log the action
            log_action(action='PASSWORD_RESET_REQUESTED', user=user, description=f"Reset link sent to {email}")

        # Always return 200 to prevent email enumeration attacks
        return Response({"message": "If an account exists with this email, a reset link has been sent."}, status=status.HTTP_200_OK)
    
class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        try:
            # 1. Decode UID to find the user
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            # 2. Validate the token
            if default_token_generator.check_token(user, token):
                # 3. Update auth_user password
                user.set_password(new_password)
                user.save()
                
                # 4. Log successful reset[cite: 2]
                log_action(action='PASSWORD_RESET_SUCCESS', user=user, description="User successfully reset their password.")
                return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated] # Must be logged in

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # 1. Security Check: Verify old password
        if not user.check_password(old_password):
            return Response({"error": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Update auth_user[cite: 6]
        user.set_password(new_password)
        user.save()

        # 3. Important: Keep the session alive after password change
        update_session_auth_hash(request, user)

        # 4. Audit Log[cite: 2]
        log_action(
            action='ACTION_TAKEN', 
            user=user, 
            description="User manually changed their password from the dashboard."
        )

        return Response({"message": "Password updated successfully!"})

class ProfileView(APIView):
    # This route is for both viewing and updating the user's profile.
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            shadow_user = UserData.objects.get(username=request.user.username)
        
            return Response({
                "username": shadow_user.username,
                "email": shadow_user.email,
                "mobile": shadow_user.contact_number,
                "address": shadow_user.address,
                "name": shadow_user.name,
            })
        
        except UserData.DoesNotExist:
            # Helpful debug message for terminal
            print(f"CRITICAL: Username '{request.user.username}' not found in user_user table!")
            return Response({"error": "Profile data not found in custom table."}, status=404)\
        

    def put(self, request):
        data = request.data
        user = request.user
        try:
            shadow_user = UserData.objects.get(username=user.username)
            
            # 2. Update the shadow record
            shadow_user.username = data.get('username', shadow_user.username)
            shadow_user.email = data.get('email', shadow_user.email)
            shadow_user.contact_number = data.get('mobile', shadow_user.contact_number)
            shadow_user.address = data.get('address', shadow_user.address)
            shadow_user.name = data.get('name', shadow_user.name)

            shadow_user.save(force_update=True)

            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            if 'name' in data:
                # Basic logic to split a full name into first/last for auth_user
                names = data.get('name').split(' ', 1)
                user.first_name = names[0]
                user.last_name = names[1] if len(names) > 1 else ""
                
            user.save()

            
            return Response({"message": "Details updated in user_user table!"})
        except Exception as e:
            return Response({"error": str(e)}, status=400)