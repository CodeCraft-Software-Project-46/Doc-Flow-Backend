from django.urls import path
from .views import ManualUploadView, WorkflowDropdownListView, FolderMappingView, CreateFolderMappingView
from . import views


urlpatterns = [ # Define URL patterns for the documents app, linking to the appropriate views   
    path('upload/manual/', ManualUploadView.as_view(), name='manual-upload'),
    path('workflows/', WorkflowDropdownListView.as_view(), name='workflow-list'),
    path('mappings/', FolderMappingView.as_view(), name='folder-mapping'),
    path('mappings/create/', CreateFolderMappingView.as_view(), name='create-folder-mapping'),
    path('upload/dropdowns/', views.get_upload_dropdowns, name='upload-dropdowns'),
    path('types/', views.DocumentTypeListCreateView.as_view(), name='document-type-list-create'),
    path('list/', views.DocumentListView.as_view(), name='document-list'),

]