from rest_framework import serializers
from .models import WorkingHoursConfig

class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHoursConfig            
        fields = '__all__'                #Send ALL columns from database to frontend”

#Database object ↔ JSON
# | Direction    | Purpose            |
# | ------------ | ------------------ |
# | Model → JSON | send to frontend   |
# | JSON → Model | save from frontend |
