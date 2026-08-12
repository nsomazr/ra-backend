import uuid

from django.conf import settings
from django.db import models


class Region(models.Model):
    region_id = models.CharField(max_length=32, primary_key=True)
    region_name = models.CharField(max_length=128)
    in_scope = models.BooleanField(default=False)
    roster_status = models.CharField(max_length=32, default="UNCONFIRMED")
    scope_note = models.TextField(blank=True)
    councils = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["region_name"]

    def __str__(self):
        return self.region_name


class School(models.Model):
    school_id = models.CharField(max_length=32, primary_key=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="schools")
    school_name = models.CharField(max_length=255)
    name_variant = models.CharField(max_length=255, blank=True)
    council = models.CharField(max_length=255, blank=True)
    ward = models.CharField(max_length=255, blank=True)
    roster_status = models.CharField(max_length=32, default="CONFIRMED")
    pupils = models.IntegerField(null=True, blank=True)
    learners_with_disabilities = models.IntegerField(null=True, blank=True)
    disability_categories = models.TextField(blank=True)
    audit_headline = models.TextField(blank=True)
    audit_baseline = models.TextField(blank=True)
    planned_modification = models.TextField(blank=True)
    assessment_focus = models.TextField(blank=True)
    priority = models.CharField(max_length=64, blank=True)
    retest_areas = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["school_id"]

    def __str__(self):
        return self.school_name


class Result(models.Model):
    result_id = models.CharField(max_length=16, primary_key=True)
    result_name = models.CharField(max_length=255)
    intent = models.TextField(blank=True)
    indicators = models.TextField(blank=True)
    project_target = models.TextField(blank=True)
    check_in_field = models.TextField(blank=True)
    evidence_to_request = models.TextField(blank=True)

    def __str__(self):
        return self.result_id


class VerificationQuestion(models.Model):
    question_id = models.CharField(max_length=16, primary_key=True)
    result = models.ForeignKey(Result, on_delete=models.PROTECT, related_name="questions")
    area = models.CharField(max_length=255)
    question = models.TextField()
    planned_standard = models.TextField(blank=True)

    def __str__(self):
        return self.question_id


class EvidenceStream(models.Model):
    stream_id = models.CharField(max_length=32, primary_key=True)
    stream_name = models.CharField(max_length=128)
    detail = models.TextField(blank=True)

    def __str__(self):
        return self.stream_id


class ReconciliationItem(models.Model):
    item_id = models.CharField(max_length=16, primary_key=True)
    issue = models.TextField()
    source_a = models.TextField(blank=True)
    source_b = models.TextField(blank=True)
    why_it_matters = models.TextField(blank=True)
    required_action = models.TextField(blank=True)

    def __str__(self):
        return self.item_id


class ReconciliationResolution(models.Model):
    item = models.OneToOneField(ReconciliationItem, on_delete=models.CASCADE, related_name="resolution", primary_key=True)
    status = models.CharField(max_length=32, default="OPEN")
    agreed_value = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class SchoolAssignment(models.Model):
    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="school_assignments")
    assignment_role = models.CharField(max_length=32)
    active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("school", "user", "assignment_role")


class SchoolReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "DRAFT"
        IN_PROGRESS = "IN PROGRESS", "IN PROGRESS"
        READY = "READY FOR SUBMISSION", "READY FOR SUBMISSION"
        SUBMITTED = "SUBMITTED", "SUBMITTED"
        UNDER_REVIEW = "UNDER REVIEW", "UNDER REVIEW"
        CLARIFICATION = "REQUIRES CLARIFICATION", "REQUIRES CLARIFICATION"
        QA_APPROVED = "QA APPROVED", "QA APPROVED"
        FINALIZED = "FINALIZED", "FINALIZED"

    report_id = models.CharField(max_length=64, primary_key=True)
    school = models.OneToOneField(School, on_delete=models.PROTECT, related_name="report")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    field_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    auditor_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    auditor_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    team_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    safeguarding_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    visit_start = models.DateField(null=True, blank=True)
    visit_end = models.DateField(null=True, blank=True)
    gps_lat = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    head_teacher = models.CharField(max_length=255, blank=True)
    focal_person = models.CharField(max_length=255, blank=True)
    school_committee = models.CharField(max_length=255, blank=True)
    teachers_total = models.IntegerField(null=True, blank=True)
    teachers_trained_ie = models.IntegerField(null=True, blank=True)
    learners_total = models.IntegerField(null=True, blank=True)
    learners_with_disabilities = models.IntegerField(null=True, blank=True)
    girls_with_disabilities = models.IntegerField(null=True, blank=True)
    roster_confirmed = models.CharField(max_length=64, blank=True)
    roster_note = models.TextField(blank=True)
    overall_findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    evidence_limitations = models.TextField(blank=True)
    # Nested instrument payloads (mirrors field client structure)
    results = models.JSONField(default=dict, blank=True)
    field_questions = models.JSONField(default=dict, blank=True)
    accessibility = models.JSONField(default=dict, blank=True)
    child_journey = models.JSONField(default=list, blank=True)
    interviews = models.JSONField(default=list, blank=True)
    evidence_register = models.JSONField(default=list, blank=True)
    findings = models.JSONField(default=list, blank=True)
    debriefs = models.JSONField(default=list, blank=True)
    history = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["report_id"]

    def __str__(self):
        return self.report_id


class ProgrammeWorkbook(models.Model):
    region = models.OneToOneField(Region, on_delete=models.CASCADE, related_name="programme", primary_key=True)
    baseline = models.JSONField(default=dict, blank=True)
    activities = models.JSONField(default=dict, blank=True)
    dac = models.JSONField(default=dict, blank=True)
    stakeholders = models.JSONField(default=dict, blank=True)
    sustainability = models.JSONField(default=dict, blank=True)
    learning = models.JSONField(default=dict, blank=True)
    vfm = models.JSONField(default=dict, blank=True)
    data_quality = models.JSONField(default=list, blank=True)
    evidence_map = models.JSONField(default=list, blank=True)
    team_leader_summary = models.JSONField(default=dict, blank=True)
    deliverables = models.JSONField(default=dict, blank=True)
    gates = models.JSONField(default=dict, blank=True)
    history = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Programme {self.region_id}"


class ConsentRecord(models.Model):
    consent_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(SchoolReport, null=True, blank=True, on_delete=models.SET_NULL, related_name="consents")
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="consents")
    respondent_code = models.CharField(max_length=64)
    participation_type = models.CharField(max_length=16)
    language = models.CharField(max_length=64)
    adult_status = models.CharField(max_length=32, blank=True)
    caregiver_code = models.CharField(max_length=64, blank=True)
    caregiver_status = models.CharField(max_length=32, blank=True)
    child_assent_status = models.CharField(max_length=64, blank=True)
    photography_consent = models.BooleanField(default=False)
    audio_consent = models.BooleanField(default=False)
    cleared = models.BooleanField(default=False)
    withdrawn = models.BooleanField(default=False)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    payload = models.JSONField(default=dict, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]


class EvidenceFile(models.Model):
    evidence_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(SchoolReport, on_delete=models.CASCADE, related_name="evidence_files")
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=512)
    file = models.FileField(upload_to="evidence/%Y/%m/", blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    byte_size = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    stream_id = models.CharField(max_length=32, blank=True)
    detached = models.BooleanField(default=False)
    sync_status = models.CharField(max_length=32, default="PENDING SYNC")
    meta = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    audit_log_id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=128)
    report = models.ForeignKey(SchoolReport, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    field_name = models.CharField(max_length=128, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]


class ProjectSettings(models.Model):
    """Singleton project-level settings and reconciliation state."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    allow_unassessed = models.BooleanField(default=True)
    require_triangulation = models.BooleanField(default=True)
    block_unconfirmed_roster = models.BooleanField(default=True)
    active_regions = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
