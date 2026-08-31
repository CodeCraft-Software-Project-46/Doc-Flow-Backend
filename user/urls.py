from django.urls import path
from .views import GetAllPermissionsView, SaveRoleView, GetAllRolesView, CreateUserView, CreateDepartmentView, \
    GetDepartmentsView, UpdateUserView, GetUsersView, DeleteUserView, UpdateRoleView, DeleteRoleView, \
    UpdateDepartmentView, DeleteDepartmentView

urlpatterns = [
    path('permission/getAll/', GetAllPermissionsView.as_view(), name='get-permissions'),
    path('role/save/', SaveRoleView.as_view(), name='save-role'),
    path('role/getAll/', GetAllRolesView.as_view(), name='get-roles'),
    path('role/update/<pk>/', UpdateRoleView.as_view(), name='update-role'),
    path('role/delete/<pk>/', DeleteRoleView.as_view(), name='delete-role'),
    path('department/save/', CreateDepartmentView.as_view(), name='save-department'),
    path('department/getAll/', GetDepartmentsView.as_view(), name='get-all-departments'),
    path('department/update/<pk>/', UpdateDepartmentView.as_view(), name='update-department'),
    path('department/delete/<pk>/', DeleteDepartmentView.as_view(), name='delete-department'),
    path('user/save/',CreateUserView.as_view(),name='save-user'),
    path('user/update/<pk>/',UpdateUserView.as_view(),name='update-user'),
    path('user/getAll/',GetUsersView.as_view(),name='get-user'),
    path('user/delete/<uuid:pk>/',DeleteUserView.as_view(),name='delete-user')
]