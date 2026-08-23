from django.urls import path
from .views import DocumentTypeDetailView, ManualUploadView, FolderMappingView
from . import views


urlpatterns = [ # Define URL patterns for the documents app, linking to the appropriate views   
    path('upload/manual/', ManualUploadView.as_view(), name='manual-upload'),
    path('mappings/', FolderMappingView.as_view(), name='folder-mapping'),
    path('mappings/create/', FolderMappingView.as_view(), name='create-folder-mapping'),
    path('mappings/<int:pk>/', views.FolderMappingDetailView.as_view(), name='folder-mapping-detail'),
    path('upload/dropdowns/', views.get_upload_dropdowns, name='upload-dropdowns'),
    path('types/', views.DocumentTypeListCreateView.as_view(), name='document-type-list-create'),
    path('list/', views.DocumentListView.as_view(), name='document-list'),
    path('types/<int:pk>/', DocumentTypeDetailView.as_view(), name='document-type-detail'),

    path('upload-links/', views.ListUploadLinksView.as_view(), name='list-upload-links'),
    path('upload-links/generate/', views.GenerateUploadLinkView.as_view(), name='generate-upload-link'),
    path('upload-links/<uuid:link_id>/revoke/', views.RevokeUploadLinkView.as_view(), name='revoke-upload-link'),
    path('upload-links/<uuid:link_id>/upload/', views.LinkBasedUploadView.as_view(), name='link-based-upload'),
    
]