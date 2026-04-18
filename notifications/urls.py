from django.urls import path
from .views import NotificationRuleListView, UserInboxView

urlpatterns = [
    # API for the Admin Dashboard
    path('rules/', NotificationRuleListView.as_view(), name='notification-rules'),
    
    # API for the User's Sidebar Bell
    path('inbox/', UserInboxView.as_view(), name='notification-inbox'),
]