from rest_framework import serializers

from .models import BottleneckScoreWeights


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
