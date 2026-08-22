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

    # A start/end time that isn't a real window (start after end, or the
    # same time for both) would let the SLA engine compute a due date of
    # zero-or-negative available hours per day. calculate_due_at() already
    # refuses that with an error — this stops the bad config from ever
    # being saved in the first place, instead of only failing later when a
    # task happens to need its deadline calculated.
    def validate(self, attrs):
        start = attrs.get(
            "work_start_time",
            getattr(self.instance, "work_start_time", None),
        )
        end = attrs.get(
            "work_end_time",
            getattr(self.instance, "work_end_time", None),
        )

        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError(
                "work_start_time must be earlier than work_end_time."
            )

        return attrs

#Database object ↔ JSON
# | Direction    | Purpose            |
# | ------------ | ------------------ |
# | Model → JSON | send to frontend   |
# | JSON → Model | save from frontend |

#bridge between Model/python object ↔ JSON