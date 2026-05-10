from django.urls import path
from .views import ChangePasswordView, LoginView, LogoutView, CurrentUserView, ProfileView, PasswordResetRequestView, PasswordResetConfirmView, ProfileView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('profile/', ProfileView.as_view(), name='profile'),
]

# We wrote as classes. The .as_view() method converts them into functions that can handle HTTP requests.
# We use name parameter to give each URL pattern a unique name so when we want to change it in future
# its easy to change in one place instead of changing it everywhere in the codebase.