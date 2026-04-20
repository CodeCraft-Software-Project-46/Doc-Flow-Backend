from django.db import models

# Create your models here.
#This becomes a table in MySQL
#database schema 
class WorkingHoursConfig(models.Model):
    #store time as HH:MM:SS
    work_start_time = models.TimeField()
    work_end_time = models.TimeField()

    # store array as JSON
    work_days = models.JSONField(default=list)
    holidays = models.JSONField(default=list)

    time_zone = models.CharField(max_length=50, default="UTC")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "working_hoursconfig"   # 👈 custom table name

    def __str__(self):
        return f"Working Hours ({self.work_start_time} - {self.work_end_time})" #self means current object, this is just for better representation in admin panel and debugging