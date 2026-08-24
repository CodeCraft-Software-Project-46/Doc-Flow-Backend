from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_sample import WorkflowSample
from .serializers import (
    WorkflowVersionDetailSerializer,
    WorkflowVersionListSerializer,
)


class WorkflowGroupedListView(APIView):

    def get(self, request):
        qs = WorkflowSample.objects.all().order_by("external_id", "-version")

        groups = {}
        order = []

        for wf in qs:
            key = wf.external_id
            if key not in groups:
                groups[key] = {
                    "external_id": wf.external_id,
                    # most recent version's name/category represents the group,
                    # in case those drifted across versions
                    "name": wf.name,
                    "document_category": wf.document_category or "general",
                    "document_type": wf.document_type or "general",
                    "versions": [],
                }
                order.append(key)
            groups[key]["versions"].append(wf)

        result = []
        for key in order:
            group = groups[key]
            result.append(
                {
                    "external_id": group["external_id"],
                    "name": group["name"],
                    "document_category": group["document_category"],
                    "document_type": group["document_type"],
                    "versions": WorkflowVersionListSerializer(
                        group["versions"], many=True
                    ).data,
                }
            )

        return Response(result)


class WorkflowVersionListView(generics.ListAPIView):

    serializer_class = WorkflowVersionListSerializer

    def get_queryset(self):
        return WorkflowSample.objects.filter(
            external_id=self.kwargs["external_id"]
        ).order_by("-version")


class WorkflowVersionBatchDetailView(APIView):


    def get(self, request):
        raw_ids = request.query_params.get("ids", "")
        ids = [v for v in raw_ids.split(",") if v]

        if not ids:
            raise ValidationError({"ids": "Provide one or more comma-separated ids."})

        versions = WorkflowSample.objects.filter(id__in=ids)
        by_id = {v.id: v for v in versions}

        missing = [i for i in ids if i not in by_id]
        if missing:
            return Response(
                {"detail": f"Version(s) not found: {', '.join(missing)}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ordered = [by_id[i] for i in ids]
        data = WorkflowVersionDetailSerializer(ordered, many=True).data
        return Response({"versions": data})


class WorkflowVersionDetailView(generics.RetrieveDestroyAPIView):

    queryset = WorkflowSample.objects.all()
    serializer_class = WorkflowVersionDetailSerializer


class WorkflowVersionRollbackView(APIView):

    def post(self, request, pk):
        try:
            target = WorkflowSample.objects.get(pk=pk)
        except WorkflowSample.DoesNotExist:
            return Response(
                {"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if target.status == "Active":
            return Response(
                {"detail": "This version is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target.status == "Deprecated":
            return Response(
                {"detail": "Cannot rollback to a deprecated version."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        WorkflowSample.objects.filter(
            external_id=target.external_id, status="Active"
        ).update(status="Archived")

        target.status = "Active"
        target.save(update_fields=["status", "updated_at"])

        return Response(WorkflowVersionDetailSerializer(target).data)