from rest_framework import serializers

from .models import (
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


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class SchoolSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.region_name", read_only=True)

    class Meta:
        model = School
        fields = (
            "school_id", "region", "region_name", "school_name", "name_variant",
            "council", "ward", "roster_status", "pupils", "learners_with_disabilities",
            "disability_categories", "audit_headline", "audit_baseline", "planned_modification",
            "assessment_focus", "priority", "retest_areas", "active",
        )


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = "__all__"


class VerificationQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationQuestion
        fields = "__all__"


class EvidenceStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceStream
        fields = "__all__"


class ReconciliationResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationResolution
        fields = "__all__"


class ReconciliationItemSerializer(serializers.ModelSerializer):
    resolution = ReconciliationResolutionSerializer(read_only=True)

    class Meta:
        model = ReconciliationItem
        fields = "__all__"


class SchoolReportSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.school_name", read_only=True)
    region_id = serializers.CharField(source="school.region_id", read_only=True)

    class Meta:
        model = SchoolReport
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class SchoolReportListSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="school.school_name", read_only=True)
    region_id = serializers.CharField(source="school.region_id", read_only=True)

    class Meta:
        model = SchoolReport
        fields = (
            "report_id", "school", "school_name", "region_id", "status", "version",
            "visit_start", "visit_end", "updated_at", "submitted_at",
        )


class ProgrammeWorkbookSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.region_name", read_only=True)

    class Meta:
        model = ProgrammeWorkbook
        fields = "__all__"
        read_only_fields = ("updated_at",)


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = "__all__"
        read_only_fields = ("recorded_at",)


class EvidenceFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceFile
        fields = "__all__"
        read_only_fields = ("created_at",)


class ProjectSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSettings
        fields = "__all__"
        read_only_fields = ("id", "updated_at")
