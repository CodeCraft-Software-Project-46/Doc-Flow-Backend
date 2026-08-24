from django.contrib import admin

from .models import BottleneckScoreWeights


@admin.register(BottleneckScoreWeights)
class BottleneckScoreWeightsAdmin(admin.ModelAdmin):
    list_display = ("time_weight", "breach_weight", "volume_weight", "updated_at")
