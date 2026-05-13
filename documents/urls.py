from django.urls import path
from .views import DocumentTypeDetailView, ManualUploadView, FolderMappingView
from . import views


urlpatterns = [ # Define URL patterns for the documents app, linking to the appropriate views   
    path('upload/manual/', ManualUploadView.as_view(), name='manual-upload'),
    path('mappings/', FolderMappingView.as_view(), name='folder-mapping'),
    path('mappings/create/', FolderMappingView.as_view(), name='create-folder-mapping'),
    path('upload/dropdowns/', views.get_upload_dropdowns, name='upload-dropdowns'),
    path('types/', views.DocumentTypeListCreateView.as_view(), name='document-type-list-create'),
    path('list/', views.DocumentListView.as_view(), name='document-list'),
    path('types/<int:pk>/', DocumentTypeDetailView.as_view(), name='document-type-detail'),


]