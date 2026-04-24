import re
from rest_framework import serializers
from .models import WorkingHoursConfig

class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHoursConfig            
        fields = '__all__'                #Take ALL columns from model n covert to JSON (or vice versa) and seend to frontend (or save from frontend)

#validation for work days and holidays
    def validate_work_days(self, value):
            if not value:
                raise serializers.ValidationError("At least one working day required")

            for day in value:
                if day < 0 or day > 6:
                    raise serializers.ValidationError("Work days must be between 0 and 6")
            return value

    def validate_holidays(self, value):
        pattern = r"^\d{4}-\d{2}-\d{2}$"

        for h in value:
            if not re.match(pattern, h):
                raise serializers.ValidationError(
                    "Invalid holiday format (YYYY-MM-DD required)"
                )
        return value

#Database object ↔ JSON
# | Direction    | Purpose            |
# | ------------ | ------------------ |
# | Model → JSON | send to frontend   |
# | JSON → Model | save from frontend |

#bridge between Model/python object ↔ JSON