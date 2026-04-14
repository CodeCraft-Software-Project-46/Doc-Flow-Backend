from django.urls import path
from .views import GetAllPermissionsView, SaveRoleView

urlpatterns = [
    path('permissions/', GetAllPermissionsView.as_view(), name='get-permissions'),
    path('save-role/', SaveRoleView.as_view(), name='save-role'),
]