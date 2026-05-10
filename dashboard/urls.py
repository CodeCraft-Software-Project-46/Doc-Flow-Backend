from django.urls import path

from dashboard.views import GetAccessibleWidgets, SaveDashboard, GetDashboardList, GetDashboard, UpdateDashboard, \
    ChangeDashboardStatus

urlpatterns = [
    path('getAccessibleWidgets/<role_id>/',GetAccessibleWidgets.as_view(),name='getAccessibleWidgets'),
    path('saveDashboard/',SaveDashboard.as_view(),name='saveDashboard'),
    path('updateDashboard/<id>/',UpdateDashboard.as_view(),name='updateDashboard'),
    path('getAllDashboard/',GetDashboardList.as_view(),name='getAllDashboard'),
    path('getDashboard/<dashboard_id>/',GetDashboard.as_view(),name='getDashboard'),
    path('changeDashboardStatus/<dashboard_id>/',ChangeDashboardStatus.as_view(),name='changeDashboardStatus'),
]