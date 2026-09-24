"""Offline field-client snapshot sync → SQLite models.

Accepts the browser snapshot shape from data.js and upserts SchoolReport,
ProgrammeWorkbook, ConsentRecord, ProjectSettings, and reconciliation
resolutions. Merge rule: last-updatedAt-wins.
"""

from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsNotViewer

from .models import (
    ConsentRecord,
    EvidenceFile,
    ProgrammeWorkbook,
    ProjectSettings,
    ReconciliationItem,
    ReconciliationResolution,
    Region,
    School,
    SchoolReport,
    SyncMeta,
)
from .serializers import EvidenceFileSerializer


def _parse_ts(value) -> float:
    if not value:
        return 0.0
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        dt = parse_datetime(str(value))
        if dt:
            return dt.timestamp()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _newer(a, b):
    """Return the record with the later updatedAt (or `at`). Prefer b on ties."""
    ta = _parse_ts((a or {}).get("updatedAt") or (a or {}).get("at") or (a or {}).get("recorded_at"))
    tb = _parse_ts((b or {}).get("updatedAt") or (b or {}).get("at") or (b or {}).get("recorded_at"))
    return b if tb >= ta else a


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _to_date(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    parsed = parse_date(str(value)[:10])
    return parsed


def _parse_gps(gps_str):
    if not gps_str:
        return None, None
    text = str(gps_str).strip()
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None, None
    try:
        return Decimal(match.group(1)), Decimal(match.group(2))
    except (InvalidOperation, ValueError):
        return None, None


def report_to_client(report: SchoolReport) -> dict:
    school = report.school
    gps = ""
    if report.gps_lat is not None and report.gps_lng is not None:
        gps = f"{report.gps_lat},{report.gps_lng}"
    return {
        "id": report.report_id,
        "schoolId": school.school_id,
        "region": school.region.region_name if school.region_id else "",
        "status": report.status,
        "version": report.version,
        "createdAt": report.created_at.isoformat() if report.created_at else "",
        "updatedAt": report.updated_at.isoformat() if report.updated_at else "",
        "submittedAt": report.submitted_at.isoformat() if report.submitted_at else "",
        "team": report.team or {
            "fieldAgent": "",
            "auditor1": "",
            "auditor2": "",
            "teamLeader": "",
            "safeguardingLead": "",
        },
        "profile": {
            "headTeacher": report.head_teacher or "",
            "focalPerson": report.focal_person or "",
            "schoolCommittee": report.school_committee or "",
            "teachersTotal": "" if report.teachers_total is None else str(report.teachers_total),
            "teachersTrainedIE": "" if report.teachers_trained_ie is None else str(report.teachers_trained_ie),
            "learners": "" if report.learners_total is None else str(report.learners_total),
            "learnersWithDisabilities": "" if report.learners_with_disabilities is None else str(report.learners_with_disabilities),
            "girlsWithDisabilities": "" if report.girls_with_disabilities is None else str(report.girls_with_disabilities),
            "gps": gps,
            "visitDate": report.visit_start.isoformat() if report.visit_start else "",
            "visitEndDate": report.visit_end.isoformat() if report.visit_end else "",
            "rosterConfirmed": report.roster_confirmed or "",
            "rosterNote": report.roster_note or "",
        },
        "results": report.results or {},
        "fieldQuestions": report.field_questions or {},
        "accessibility": report.accessibility or {},
        "childJourney": report.child_journey or [],
        "interviews": report.interviews or [],
        "evidenceRegister": report.evidence_register or [],
        "findings": report.findings or [],
        "debriefs": report.debriefs or [],
        "narrative": {
            "overall": report.overall_findings or "",
            "recommendations": report.recommendations or "",
            "limitations": report.evidence_limitations or "",
        },
        "history": report.history or [],
    }


def programme_to_client(prog: ProgrammeWorkbook) -> dict:
    return {
        "regionId": prog.region_id,
        "updatedAt": prog.updated_at.isoformat() if prog.updated_at else "",
        "baseline": prog.baseline or {},
        "activities": prog.activities or {},
        "dac": prog.dac or {},
        "stakeholders": prog.stakeholders or {},
        "sustainability": prog.sustainability or {},
        "learning": prog.learning or {},
        "vfm": prog.vfm or {},
        "dataQuality": prog.data_quality or [],
        "evidenceMap": prog.evidence_map or [],
        "teamLeaderSummary": prog.team_leader_summary or {},
        "deliverables": prog.deliverables or {},
        "gates": prog.gates or {},
        "history": prog.history or [],
    }


def consent_to_client(c: ConsentRecord) -> dict:
    payload = c.payload or {}
    return {
        "id": str(c.consent_id),
        "schoolId": c.school_id,
        "type": c.participation_type or payload.get("type", "ADULT"),
        "code": c.respondent_code,
        "language": c.language or "",
        "status": payload.get("status") or c.adult_status or "",
        "caregiverCode": c.caregiver_code or "",
        "photo": "YES" if c.photography_consent else "NO",
        "audio": "YES" if c.audio_consent else "NO",
        "recordedBy": payload.get("recordedBy", ""),
        "allowed": c.cleared,
        "withdrawn": c.withdrawn,
        "withdrawnAt": c.withdrawn_at.isoformat() if c.withdrawn_at else "",
        "at": c.recorded_at.isoformat() if c.recorded_at else payload.get("at", ""),
        "caregiverStatus": c.caregiver_status or "",
        "assent": c.child_assent_status or "",
        "adultStatus": c.adult_status or "",
    }


def build_server_snapshot() -> dict:
    reports = {
        r.school_id: report_to_client(r)
        for r in SchoolReport.objects.select_related("school", "school__region").all()
    }
    programmes = {
        p.region_id: programme_to_client(p)
        for p in ProgrammeWorkbook.objects.all()
    }
    consents = {
        str(c.consent_id): consent_to_client(c)
        for c in ConsentRecord.objects.select_related("school").all()
    }
    settings_obj, _ = ProjectSettings.objects.get_or_create(id=1)
    reconciliation = {}
    for item in ReconciliationItem.objects.select_related("resolution").all():
        res = getattr(item, "resolution", None)
        reconciliation[item.item_id] = {
            "agreed": (res.agreed_value if res else "") or "",
            "resolvedBy": (res.resolved_by.username if res and res.resolved_by_id else "") or "",
            "resolvedAt": res.resolved_at.isoformat() if res and res.resolved_at else "",
            "status": (res.status if res else "OPEN") or "OPEN",
        }
    project = {
        "updatedAt": settings_obj.updated_at.isoformat() if settings_obj.updated_at else "",
        "reconciliation": reconciliation,
        "history": [],
        "settings": {
            "allowUnassessed": settings_obj.allow_unassessed,
            "requireTriangulation": settings_obj.require_triangulation,
            "blockUnconfirmedRoster": settings_obj.block_unconfirmed_roster,
            "activeRegions": settings_obj.active_regions or [],
        },
    }
    return {
        "schemaVersion": 5,
        "project": project,
        "reports": reports,
        "programmes": programmes,
        "consents": consents,
        "settings": project["settings"],
    }


def _upsert_report(client_report: dict, conflicts: list) -> None:
    school_id = client_report.get("schoolId")
    if not school_id:
        return
    try:
        school = School.objects.get(pk=school_id)
    except School.DoesNotExist:
        conflicts.append({"record": school_id, "winner": "skip", "reason": "unknown school"})
        return

    report_id = client_report.get("id") or f"CBM-P10354-{school_id}"
    existing = SchoolReport.objects.filter(school=school).first()
    if existing:
        server_client = report_to_client(existing)
        chosen = _newer(server_client, client_report)
        if chosen is server_client:
            conflicts.append({"record": school_id, "winner": "server"})
            return
        if existing.report_id != report_id and not SchoolReport.objects.filter(pk=report_id).exists():
            # Keep PK stable if already assigned
            report_id = existing.report_id
        conflicts.append({"record": school_id, "winner": "incoming"})
        report = existing
        report.report_id = existing.report_id
    else:
        if SchoolReport.objects.filter(pk=report_id).exists():
            report_id = f"{report_id}-{school_id}"
        report = SchoolReport(report_id=report_id, school=school)

    profile = client_report.get("profile") or {}
    narrative = client_report.get("narrative") or {}
    gps_lat, gps_lng = _parse_gps(profile.get("gps"))

    report.status = client_report.get("status") or report.status or SchoolReport.Status.DRAFT
    report.version = int(client_report.get("version") or report.version or 1)
    report.team = client_report.get("team") or report.team or {}
    report.head_teacher = str(profile.get("headTeacher") or "")[:255]
    report.focal_person = str(profile.get("focalPerson") or "")[:255]
    report.school_committee = str(profile.get("schoolCommittee") or "")[:255]
    report.teachers_total = _to_int(profile.get("teachersTotal"))
    report.teachers_trained_ie = _to_int(profile.get("teachersTrainedIE"))
    report.learners_total = _to_int(profile.get("learners"))
    report.learners_with_disabilities = _to_int(profile.get("learnersWithDisabilities"))
    report.girls_with_disabilities = _to_int(profile.get("girlsWithDisabilities"))
    report.visit_start = _to_date(profile.get("visitDate"))
    report.visit_end = _to_date(profile.get("visitEndDate"))
    report.gps_lat = gps_lat
    report.gps_lng = gps_lng
    report.roster_confirmed = str(profile.get("rosterConfirmed") or "")[:64]
    report.roster_note = str(profile.get("rosterNote") or "")
    report.overall_findings = str(narrative.get("overall") or "")
    report.recommendations = str(narrative.get("recommendations") or "")
    report.evidence_limitations = str(narrative.get("limitations") or "")
    report.results = client_report.get("results") or {}
    report.field_questions = client_report.get("fieldQuestions") or {}
    report.accessibility = client_report.get("accessibility") or {}
    report.child_journey = client_report.get("childJourney") or []
    report.interviews = client_report.get("interviews") or []
    report.evidence_register = client_report.get("evidenceRegister") or []
    report.findings = client_report.get("findings") or []
    report.debriefs = client_report.get("debriefs") or []
    report.history = client_report.get("history") or []

    submitted = client_report.get("submittedAt")
    if submitted:
        dt = parse_datetime(str(submitted).replace("Z", "+00:00"))
        if dt:
            report.submitted_at = dt

    report.save()


def _upsert_programme(client_prog: dict, conflicts: list) -> None:
    region_id = client_prog.get("regionId")
    if not region_id:
        return
    # Client uses region names like "Katavi"; DB uses region_id like "KATAVI" or similar
    region = Region.objects.filter(pk=region_id).first()
    if not region:
        region = Region.objects.filter(region_name__iexact=region_id).first()
    if not region:
        # Try uppercase id match
        region = Region.objects.filter(pk=str(region_id).upper()).first()
    if not region:
        conflicts.append({"record": f"programme:{region_id}", "winner": "skip", "reason": "unknown region"})
        return

    existing = ProgrammeWorkbook.objects.filter(pk=region.region_id).first()
    if existing:
        server_client = programme_to_client(existing)
        chosen = _newer(server_client, client_prog)
        if chosen is server_client:
            conflicts.append({"record": f"programme:{region.region_id}", "winner": "server"})
            return
        conflicts.append({"record": f"programme:{region.region_id}", "winner": "incoming"})
        prog = existing
    else:
        prog = ProgrammeWorkbook(region=region)

    prog.baseline = client_prog.get("baseline") or {}
    prog.activities = client_prog.get("activities") or {}
    prog.dac = client_prog.get("dac") or {}
    prog.stakeholders = client_prog.get("stakeholders") or {}
    prog.sustainability = client_prog.get("sustainability") or {}
    prog.learning = client_prog.get("learning") or {}
    prog.vfm = client_prog.get("vfm") or {}
    prog.data_quality = client_prog.get("dataQuality") or []
    prog.evidence_map = client_prog.get("evidenceMap") or []
    prog.team_leader_summary = client_prog.get("teamLeaderSummary") or {}
    prog.deliverables = client_prog.get("deliverables") or {}
    prog.gates = client_prog.get("gates") or {}
    prog.history = client_prog.get("history") or []
    prog.save()


def _upsert_consent(client_consent: dict, conflicts: list) -> None:
    school_id = client_consent.get("schoolId")
    if not school_id:
        return
    try:
        school = School.objects.get(pk=school_id)
    except School.DoesNotExist:
        conflicts.append({"record": f"consent:{client_consent.get('id')}", "winner": "skip", "reason": "unknown school"})
        return

    raw_id = client_consent.get("id") or ""
    try:
        consent_uuid = uuid.UUID(str(raw_id))
    except (ValueError, TypeError):
        consent_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"p10354-consent:{raw_id or school_id}:{client_consent.get('code')}")

    existing = ConsentRecord.objects.filter(pk=consent_uuid).first()
    if existing:
        server_client = consent_to_client(existing)
        chosen = _newer(server_client, client_consent)
        if chosen is server_client:
            conflicts.append({"record": f"consent:{consent_uuid}", "winner": "server"})
            return
        conflicts.append({"record": f"consent:{consent_uuid}", "winner": "incoming"})
        rec = existing
    else:
        rec = ConsentRecord(consent_id=consent_uuid, school=school)

    report = SchoolReport.objects.filter(school=school).first()
    participation = str(client_consent.get("type") or "ADULT")[:16]
    rec.report = report
    rec.respondent_code = str(client_consent.get("code") or "")[:64]
    rec.participation_type = participation
    rec.language = str(client_consent.get("language") or "")[:64]
    rec.adult_status = str(client_consent.get("adultStatus") or client_consent.get("status") or "")[:32]
    rec.caregiver_code = str(client_consent.get("caregiverCode") or "")[:64]
    rec.caregiver_status = str(client_consent.get("caregiverStatus") or "")[:32]
    rec.child_assent_status = str(client_consent.get("assent") or "")[:64]
    rec.photography_consent = str(client_consent.get("photo") or "").upper() == "YES"
    rec.audio_consent = str(client_consent.get("audio") or "").upper() == "YES"
    rec.cleared = bool(client_consent.get("allowed"))
    rec.withdrawn = bool(client_consent.get("withdrawn"))
    withdrawn_at = client_consent.get("withdrawnAt")
    if withdrawn_at:
        dt = parse_datetime(str(withdrawn_at).replace("Z", "+00:00"))
        rec.withdrawn_at = dt
    rec.payload = {
        **(rec.payload or {}),
        "status": client_consent.get("status") or "",
        "recordedBy": client_consent.get("recordedBy") or "",
        "at": client_consent.get("at") or "",
        "clientId": raw_id,
    }
    rec.save()


def _apply_project(project: dict, settings_blob: dict | None, conflicts: list) -> None:
    settings_obj, _ = ProjectSettings.objects.get_or_create(id=1)
    src = settings_blob or (project or {}).get("settings") or {}
    if src:
        if "allowUnassessed" in src:
            settings_obj.allow_unassessed = bool(src["allowUnassessed"])
        if "requireTriangulation" in src:
            settings_obj.require_triangulation = bool(src["requireTriangulation"])
        if "blockUnconfirmedRoster" in src:
            settings_obj.block_unconfirmed_roster = bool(src["blockUnconfirmedRoster"])
        if "activeRegions" in src and isinstance(src["activeRegions"], list):
            settings_obj.active_regions = src["activeRegions"]
        settings_obj.save()

    reconciliation = (project or {}).get("reconciliation") or {}
    for item_id, data in reconciliation.items():
        item = ReconciliationItem.objects.filter(pk=item_id).first()
        if not item:
            continue
        resolution, _ = ReconciliationResolution.objects.get_or_create(item=item)
        resolution.status = str(data.get("status") or resolution.status or "OPEN")[:32]
        resolution.agreed_value = str(data.get("agreed") or "")
        if resolution.status == "RESOLVED" and data.get("resolvedAt"):
            dt = parse_datetime(str(data["resolvedAt"]).replace("Z", "+00:00"))
            if dt:
                resolution.resolved_at = dt
        resolution.save()


def apply_client_snapshot(snapshot: dict) -> tuple[dict, list]:
    conflicts: list = []
    if not snapshot:
        return build_server_snapshot(), conflicts

    with transaction.atomic():
        for report in (snapshot.get("reports") or {}).values():
            if isinstance(report, dict):
                _upsert_report(report, conflicts)
        for prog in (snapshot.get("programmes") or {}).values():
            if isinstance(prog, dict):
                _upsert_programme(prog, conflicts)
        for consent in (snapshot.get("consents") or {}).values():
            if isinstance(consent, dict):
                _upsert_consent(consent, conflicts)
        _apply_project(snapshot.get("project") or {}, snapshot.get("settings"), conflicts)

        meta, _ = SyncMeta.objects.select_for_update().get_or_create(id=1)
        meta.version = int(meta.version or 0) + 1
        meta.save(update_fields=["version", "updated_at"])

    return build_server_snapshot(), conflicts


def get_sync_version() -> int:
    meta, _ = SyncMeta.objects.get_or_create(id=1)
    return int(meta.version or 0)


class SyncPushView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotViewer]

    def post(self, request):
        snapshot = request.data.get("snapshot") or {}
        device_id = request.data.get("deviceId") or ""
        merged, conflicts = apply_client_snapshot(snapshot)
        version = get_sync_version()
        return Response({
            "ok": True,
            "deviceId": device_id,
            "serverVersion": version,
            "snapshot": merged,
            "conflicts": conflicts,
        })


class SyncPullView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return Response({
            "ok": True,
            "serverVersion": get_sync_version(),
            "snapshot": build_server_snapshot(),
        })

    def get(self, request):
        return self.post(request)


class EvidenceUploadView(APIView):
    """Accept base64 evidence payloads from the offline field client."""

    permission_classes = [permissions.IsAuthenticated, IsNotViewer]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        qs = EvidenceFile.objects.filter(detached=False).order_by("-created_at")[:500]
        files = []
        for ev in qs:
            files.append({
                "id": str(ev.evidence_id),
                "name": ev.filename,
                "type": ev.mime_type,
                "size": ev.byte_size,
                "meta": ev.meta or {},
                "sync_status": ev.sync_status,
            })
        return Response({"files": files})

    def post(self, request, evidence_id=None):
        data = request.data
        eid = evidence_id or data.get("id") or data.get("evidence_id")
        if not eid:
            return Response({"error": "evidence id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            evidence_uuid = uuid.UUID(str(eid))
        except (ValueError, TypeError):
            evidence_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"p10354-evidence:{eid}")

        report_id = data.get("reportId") or data.get("report_id") or (data.get("meta") or {}).get("reportId")
        school_id = data.get("schoolId") or (data.get("meta") or {}).get("schoolId")
        report = None
        if report_id:
            report = SchoolReport.objects.filter(pk=report_id).first()
        if not report and school_id:
            report = SchoolReport.objects.filter(school_id=school_id).first()
        if not report:
            # Fall back to any report referenced in meta path
            report = SchoolReport.objects.first()
        if not report:
            return Response({"error": "No school report available for evidence"}, status=status.HTTP_400_BAD_REQUEST)

        filename = data.get("name") or data.get("filename") or f"{eid}.bin"
        mime = data.get("type") or data.get("mime_type") or "application/octet-stream"
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}

        content = None
        if request.FILES.get("file"):
            uploaded = request.FILES["file"]
            content = uploaded.read()
            filename = uploaded.name or filename
            mime = uploaded.content_type or mime
        elif data.get("base64"):
            try:
                content = base64.b64decode(data["base64"])
            except Exception:
                return Response({"error": "Invalid base64"}, status=status.HTTP_400_BAD_REQUEST)

        ev, created = EvidenceFile.objects.get_or_create(
            evidence_id=evidence_uuid,
            defaults={
                "report": report,
                "uploader": request.user,
                "filename": str(filename)[:255],
                "storage_key": str(eid),
                "mime_type": str(mime)[:128],
                "byte_size": len(content) if content else None,
                "meta": meta,
                "sync_status": "SYNCED",
            },
        )
        if not created:
            ev.report = report
            ev.filename = str(filename)[:255]
            ev.mime_type = str(mime)[:128]
            ev.meta = {**(ev.meta or {}), **meta}
            ev.sync_status = "SYNCED"
            if content is not None:
                ev.byte_size = len(content)

        if content is not None:
            ev.file.save(filename, ContentFile(content), save=False)
            ev.sync_status = "SYNCED"
        ev.uploader = request.user
        ev.save()
        return Response(EvidenceFileSerializer(ev).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class EvidenceDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, evidence_id):
        try:
            evidence_uuid = uuid.UUID(str(evidence_id))
        except (ValueError, TypeError):
            evidence_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"p10354-evidence:{evidence_id}")

        ev = EvidenceFile.objects.filter(pk=evidence_uuid).first()
        if not ev and EvidenceFile.objects.filter(storage_key=str(evidence_id)).exists():
            ev = EvidenceFile.objects.filter(storage_key=str(evidence_id)).first()
        if not ev or not ev.file:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        from django.http import FileResponse

        return FileResponse(ev.file.open("rb"), as_attachment=False, filename=ev.filename or "evidence.bin")
