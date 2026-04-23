from django.urls import path
from .views import GetAllPermissionsView, SaveRoleView, GetAllRolesView, CreateUserView, CreateDepartmentView, \
    GetDepartmentsView, UpdateUserView, GetUsersView, DeleteUserView, UpdateRoleView, DeleteRoleView, \
    UpdateDepartmentView, DeleteDepartmentView

urlpatterns = [
    path('permissions/', GetAllPermissionsView.as_view(), name='get-permissions'),
    path('save-role/', SaveRoleView.as_view(), name='save-role'),
    path('get-roles/', GetAllRolesView.as_view(), name='get-roles'),
    path('update-role/<pk>/', UpdateRoleView.as_view(), name='update-role'),
    path('delete-role/<pk>/', DeleteRoleView.as_view(), name='delete-role'),
    path('department/save/', CreateDepartmentView.as_view(), name='save-department'),
    path('department/getAll/', GetDepartmentsView.as_view(), name='get-all-departments'),
    path('department/update/<pk>/', UpdateDepartmentView.as_view(), name='update-department'),
    path('department/delete/<pk>/', DeleteDepartmentView.as_view(), name='delete-department'),
    path('save-user/',CreateUserView.as_view(),name='save-user'),
    path('update-user/<pk>/',UpdateUserView.as_view(),name='update-user'),
    path('get-users/',GetUsersView.as_view(),name='get-user'),
    path('delete-user/<uuid:pk>/',DeleteUserView.as_view(),name='delete-user')
]