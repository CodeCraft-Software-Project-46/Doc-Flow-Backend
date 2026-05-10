from django.urls import path
from .views import NotificationRuleListView, UserInboxView, NotificationRuleDetailView, RecipientOptionsView, MarkNotificationReadView, NotificationMetadataView

urlpatterns = [
    path('rules/', NotificationRuleListView.as_view(), name='notification-rules'), # API for the Admin Dashboard
    
    path('inbox/', UserInboxView.as_view(), name='notification-inbox'),# API for the User's Sidebar Bell

    path('metadata/', NotificationMetadataView.as_view(), name='notification-metadata'), # API for dynamic notification options

    path('rules/<int:pk>/', NotificationRuleDetailView.as_view()), # For toggle/delete

    path('recipient-options/', RecipientOptionsView.as_view()),      # For the dropdown

    path('inbox/<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-mark-read'), # For marking a notification as read
]