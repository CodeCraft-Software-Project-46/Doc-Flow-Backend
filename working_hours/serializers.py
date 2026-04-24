from rest_framework import serializers
from .models import WorkingHoursConfig

class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHoursConfig            
        fields = '__all__'                #Take ALL columns from model n covert to JSON (or vice versa) and seend to frontend (or save from frontend)

#Database object ↔ JSON
# | Direction    | Purpose            |
# | ------------ | ------------------ |
# | Model → JSON | send to frontend   |
# | JSON → Model | save from frontend |

#bridge between Model/python object ↔ JSON