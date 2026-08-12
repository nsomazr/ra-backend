from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuditLog,
    ConsentRecord,
    EvidenceFile,
    EvidenceStream,
    ProgrammeWorkbook,
    ProjectSettings,
    ReconciliationItem,
    ReconciliationResolution,
    Region,
    Result,
    School,
    SchoolReport,
    VerificationQuestion,
)
from .serializers import (
    ConsentRecordSerializer,
    EvidenceFileSerializer,
    EvidenceStreamSerializer,
    ProgrammeWorkbookSerializer,
    ProjectSettingsSerializer,
    ReconciliationItemSerializer,
    RegionSerializer,
    ResultSerializer,
    SchoolReportListSerializer,
    SchoolReportSerializer,
    SchoolSerializer,
    VerificationQuestionSerializer,
)


def write_audit(actor, entity_type, entity_id, report=None, field_name="", old_value=None, new_value=None, reason=""):
    AuditLog.objects.create(
        actor=actor,
        entity_type=entity_type,
        entity_id=str(entity_id),
        report=report,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    lookup_field = "region_id"


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = School.objects.select_related("region").all()
    serializer_class = SchoolSerializer
    lookup_field = "school_id"

    def get_queryset(self):
        qs = super().get_queryset()
        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(region_id=region)
        return qs


class ResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    lookup_field = "result_id"


class VerificationQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VerificationQuestion.objects.select_related("result").all()
    serializer_class = VerificationQuestionSerializer
    lookup_field = "question_id"


class EvidenceStreamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EvidenceStream.objects.all()
    serializer_class = EvidenceStreamSerializer
    lookup_field = "stream_id"


class ReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationItem.objects.select_related("resolution").all()
    serializer_class = ReconciliationItemSerializer
    lookup_field = "item_id"

    @action(detail=True, methods=["patch"])
    def resolve(self, request, item_id=None):
        item = self.get_object()
        resolution, _ = ReconciliationResolution.objects.get_or_create(item=item)
        old = ReconciliationItemSerializer(item).data
        status_value = request.data.get("status", resolution.status)
        resolution.status = status_value
        resolution.agreed_value = request.data.get("agreed_value", resolution.agreed_value)
        if status_value == "RESOLVED":
            resolution.resolved_by = request.user
            resolution.resolved_at = timezone.now()
        resolution.save()
        write_audit(
            request.user, "reconciliation", item.item_id,
            old_value=old, new_value=ReconciliationItemSerializer(item).data,
            reason=request.data.get("reason", ""),
        )
        return Response(ReconciliationItemSerializer(item).data)


class SchoolReportViewSet(viewsets.ModelViewSet):
    queryset = SchoolReport.objects.select_related("school", "school__region").all()
    lookup_field = "report_id"

    def get_serializer_class(self):
        if self.action == "list":
            return SchoolReportListSerializer
        return SchoolReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        region = self.request.query_params.get("region")
        school = self.request.query_params.get("school")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if region:
            qs = qs.filter(school__region_id=region)
        if school:
            qs = qs.filter(school_id=school)
        return qs

    def perform_update(self, serializer):
        instance = self.get_object()
        old_status = instance.status
        report = serializer.save()
        if old_status != report.status:
            write_audit(
                self.request.user, "school_report", report.report_id, report=report,
                field_name="status", old_value=old_status, new_value=report.status,
            )
        if report.status == SchoolReport.Status.SUBMITTED and not report.submitted_at:
            report.submitted_at = timezone.now()
            report.save(update_fields=["submitted_at"])

    @action(detail=True, methods=["post"])
    def submit(self, request, report_id=None):
        report = self.get_object()
        school = report.school
        settings_obj = ProjectSettings.objects.first()
        if settings_obj and settings_obj.block_unconfirmed_roster and school.roster_status == "UNCONFIRMED":
            return Response(
                {"detail": "Cannot submit report for an unconfirmed school roster."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        old = report.status
        report.status = SchoolReport.Status.SUBMITTED
        report.submitted_at = timezone.now()
        history = list(report.history or [])
        history.append({
            "at": timezone.now().isoformat(),
            "event": "Report submitted",
            "actor": request.user.username,
        })
        report.history = history
        report.save()
        write_audit(request.user, "school_report", report.report_id, report=report,
                    field_name="status", old_value=old, new_value=report.status)
        return Response(SchoolReportSerializer(report).data)


class ProgrammeWorkbookViewSet(viewsets.ModelViewSet):
    queryset = ProgrammeWorkbook.objects.select_related("region").all()
    serializer_class = ProgrammeWorkbookSerializer
    lookup_field = "region_id"
    http_method_names = ["get", "put", "patch", "head", "options"]


class ConsentRecordViewSet(viewsets.ModelViewSet):
    queryset = ConsentRecord.objects.select_related("school", "report").all()
    serializer_class = ConsentRecordSerializer
    lookup_field = "consent_id"

    def get_queryset(self):
        qs = super().get_queryset()
        school = self.request.query_params.get("school")
        if school:
            qs = qs.filter(school_id=school)
        return qs

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class EvidenceFileViewSet(viewsets.ModelViewSet):
    queryset = EvidenceFile.objects.select_related("report").all()
    serializer_class = EvidenceFileSerializer
    lookup_field = "evidence_id"

    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user)

    @action(detail=True, methods=["post"])
    def detach(self, request, evidence_id=None):
        evidence = self.get_object()
        evidence.detached = True
        evidence.save(update_fields=["detached"])
        write_audit(
            request.user, "evidence_file", evidence.evidence_id, report=evidence.report,
            field_name="detached", old_value=False, new_value=True,
            reason="Detached from report; blob retained.",
        )
        return Response(EvidenceFileSerializer(evidence).data)


class ProjectSettingsView(APIView):
    def get(self, request):
        obj, _ = ProjectSettings.objects.get_or_create(id=1)
        return Response(ProjectSettingsSerializer(obj).data)

    def patch(self, request):
        if not request.user.is_staff and request.user.role != "ADMIN":
            return Response({"detail": "Admin only."}, status=status.HTTP_403_FORBIDDEN)
        obj, _ = ProjectSettings.objects.get_or_create(id=1)
        serializer = ProjectSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class FrameworkBundleView(APIView):
    """Reference data bundle for the field client."""

    def get(self, request):
        return Response({
            "regions": RegionSerializer(Region.objects.all(), many=True).data,
            "schools": SchoolSerializer(School.objects.select_related("region").all(), many=True).data,
            "results": ResultSerializer(Result.objects.all(), many=True).data,
            "questions": VerificationQuestionSerializer(
                VerificationQuestion.objects.select_related("result").all(), many=True
            ).data,
            "evidence_streams": EvidenceStreamSerializer(EvidenceStream.objects.all(), many=True).data,
            "reconciliation": ReconciliationItemSerializer(
                ReconciliationItem.objects.select_related("resolution").all(), many=True
            ).data,
            "settings": ProjectSettingsSerializer(ProjectSettings.objects.get_or_create(id=1)[0]).data,
        })
