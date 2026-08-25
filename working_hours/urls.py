from django.urls import path
from .views import get_config, save_config

urlpatterns = [
    path('config/', get_config), #GET config
    path('config/save/', save_config), #POST/PUT config
]

# http://127.0.0.1:8000/api/working-hours/config/
# http://127.0.0.1:8000/api/working-hours/config/save/