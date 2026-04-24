from django.db import models

# Create your models here.
#This becomes a table in MySQL
#database schema 
class WorkingHoursConfig(models.Model): #class=table
    #store time as HH:MM:SS
    work_start_time = models.TimeField()#variable=column
    work_end_time = models.TimeField() #"09:00:00"

    # store array as JSON
    work_days = models.JSONField(default=list) #[1,2,3,4,5]
    holidays = models.JSONField(default=list) #["2026-01-01", "2026-12-25"] 

    time_zone = models.CharField(max_length=50, default="UTC") #"UTC"

    updated_at = models.DateTimeField(auto_now=True) #every time you save

    class Meta:
        db_table = "working_hoursconfig"   # 👈 custom table name

    def __str__(self):
        return f"Working Hours ({self.work_start_time} - {self.work_end_time})" #self means current object, this is just for better representation in admin panel and debugging