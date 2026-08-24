from django.urls import path

from .views import (
    WorkflowGroupedListView,
    WorkflowVersionBatchDetailView,
    WorkflowVersionDetailView,
    WorkflowVersionListView,
    WorkflowVersionRollbackView,
)

urlpatterns = [
    path(
        "workflows/",
        WorkflowGroupedListView.as_view(),
        name="workflow-grouped-list",
    ),
    path(
        "workflows/<str:external_id>/versions/",
        WorkflowVersionListView.as_view(),
        name="workflow-version-list",
    ),
    path(
        "workflow-versions/",
        WorkflowVersionBatchDetailView.as_view(),
        name="workflow-version-batch-detail",
    ),
    path(
        "workflow-versions/<str:pk>/",
        WorkflowVersionDetailView.as_view(),
        name="workflow-version-detail",
    ),
    path(
        "workflow-versions/<str:pk>/rollback/",
        WorkflowVersionRollbackView.as_view(),
        name="workflow-version-rollback",
    ),
]