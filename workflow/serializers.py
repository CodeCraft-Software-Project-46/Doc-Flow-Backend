from rest_framework import serializers

from .compareutils import step_count, total_sla_seconds
from .models_sample import WorkflowSample


class WorkflowVersionListSerializer(serializers.ModelSerializer):
    """Lightweight — powers the version table. No `definition` payload."""

    version = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    total_sla_seconds = serializers.SerializerMethodField()
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowSample
        fields = [
            "id",
            "version",
            "status",
            "description",
            "updated_at",
            "created_by",
            "total_sla_seconds",
            "step_count",
        ]

    def get_version(self, obj):
        return f"v{obj.version}"

    def get_created_by(self, obj):
        # adjust to whatever your user model exposes (e.g. get_full_name())
        return getattr(obj.created_by, "email", None) or str(obj.created_by_id)

    def get_total_sla_seconds(self, obj):
        return total_sla_seconds(obj.definition)

    def get_step_count(self, obj):
        return step_count(obj.definition)


class WorkflowVersionDetailSerializer(WorkflowVersionListSerializer):
    """Full payload — includes the raw `definition` json for diffing."""

    class Meta(WorkflowVersionListSerializer.Meta):
        fields = WorkflowVersionListSerializer.Meta.fields + [
            "external_id",
            "name",
            "definition",
        ]


class WorkflowGroupSerializer(serializers.Serializer):
    """
    One entry per distinct `external_id` — the "Contract Flow" /
    "Custom Decision Test Flow" rows in the UI — with its versions
    (newest first) nested underneath.
    """

    external_id = serializers.CharField()
    name = serializers.CharField()
    document_category = serializers.CharField()
    document_type = serializers.CharField()
    versions = WorkflowVersionListSerializer(many=True)