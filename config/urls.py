from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    
    path('api/auth/', include('accounts.urls')), # This tells Django: "Any URL that starts with /api/auth/, go look inside accounts.urls to find the rest!"
    path('api/audits/', include('audits.urls')),
]