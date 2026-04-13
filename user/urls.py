from django.urls import path
from .views import GetAllPermissionsView

urlpatterns = [
    path('permissions/', GetAllPermissionsView.as_view(), name='get-permissions'),
]