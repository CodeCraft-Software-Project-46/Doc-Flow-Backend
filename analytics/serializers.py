from rest_framework import serializers

from .models import BottleneckScoreWeights


class CreateTaskSerializer(serializers.Serializer):
    """
    Manual task-creation form used by the analytics dashboard's "New Task"
    button — a dev/testing convenience for exercising the SLA engine without
    hand-writing SQL. created_at is intentionally not a field here: it is
    always stamped server-side with the current time, never taken from the
    client, so the SLA due_at calculation can't be seeded with an arbitrary
    timestamp.
    """

    task_name = serializers.CharField(max_length=255, allow_blank=False)
    sla_hours = serializers.FloatField(min_value=0.0001)


class BottleneckScoreWeightsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottleneckScoreWeights
        fields = ["id", "time_weight", "breach_weight", "volume_weight", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate(self, attrs):
        for field in ("time_weight", "breach_weight", "volume_weight"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value is not None and value < 0:
                raise serializers.ValidationError({field: "Weight cannot be negative."})
        return attrs
