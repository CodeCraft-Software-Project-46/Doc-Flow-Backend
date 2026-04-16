from django.urls import path
from .views import LoginView, LogoutView, CurrentUserView, UserProvisioningView

urlpatterns = [
    path('provision-user/', UserProvisioningView.as_view(), name='provision-user'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
]

# We wrote as classes. The .as_view() method converts them into functions that can handle HTTP requests.
# We use name parameter to give each URL pattern a unique name so when we want to change it in future
# its easy to change in one place instead of changing it everywhere in the codebase.