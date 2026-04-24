from django.urls import path
from .views import NotificationRuleListView, UserInboxView, NotificationRuleDetailView, RecipientOptionsView, MarkNotificationReadView

urlpatterns = [
    # API for the Admin Dashboard
    path('rules/', NotificationRuleListView.as_view(), name='notification-rules'),
    
    # API for the User's Sidebar Bell
    path('inbox/', UserInboxView.as_view(), name='notification-inbox'),

    path('rules/<int:pk>/', NotificationRuleDetailView.as_view()), # For toggle/delete

    path('recipient-options/', RecipientOptionsView.as_view()),      # For the dropdown

    path('inbox/<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-mark-read'), # For marking a notification as read
]