from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, NotificationViewSet, RoleViewSet, TaskInstanceViewSet, UserProfileViewSet, WorkflowInstanceViewSet, WorkflowViewSet, csrf_cookie

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"profiles", UserProfileViewSet, basename="profile")
router.register(r"workflows", WorkflowViewSet, basename="workflow")
router.register(r"workflow-instances", WorkflowInstanceViewSet, basename="workflow-instance")
router.register(r"task-instances", TaskInstanceViewSet, basename="task-instance")
router.register(r"tasks", TaskInstanceViewSet, basename="task")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
	path("csrf/", csrf_cookie, name="csrf-cookie"),
	path("", include(router.urls)),
]