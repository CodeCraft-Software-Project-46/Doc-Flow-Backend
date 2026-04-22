from django.urls import path
from .views import ManualUploadView

urlpatterns = [ # Define URL patterns for the documents app, linking to the appropriate views   
    path('upload/manual/', ManualUploadView.as_view(), name='manual-upload'),
]