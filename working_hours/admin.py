from django.contrib import admin

# Register your models here.
#👉 Register models here to view in admin UI
#from .models import WorkingHoursConfig
# 📌 Django gives you a FREE dashboard:

# 👉 http://127.0.0.1:8000/admin/
# view database tables
# add/edit/delete data

from django.contrib import admin
from .models import WorkingHoursConfig

@admin.register(WorkingHoursConfig)    #Show this table in admin panel so I can view/edit data
class WorkingHoursConfigAdmin(admin.ModelAdmin):
    list_display = ("work_start_time", "work_end_time", "time_zone", "updated_at")