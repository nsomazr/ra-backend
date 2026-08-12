import json
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from assessment.models import (
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

User = get_user_model()


class Command(BaseCommand):
    help = "Seed reference data from framework seed_data.json and bootstrap admin"

    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[2] / "seed_data.json"
        data = json.loads(path.read_text())

        for row in data["regions"]:
            Region.objects.update_or_create(
                region_id=row["region_id"],
                defaults={
                    "region_name": row["region_name"],
                    "in_scope": row["in_scope"],
                    "roster_status": row["roster_status"],
                    "scope_note": row.get("scope_note", ""),
                    "councils": row.get("councils", ""),
                },
            )
        self.stdout.write(f"Regions: {Region.objects.count()}")

        for row in data["schools"]:
            School.objects.update_or_create(
                school_id=row["school_id"],
                defaults={
                    "region_id": row["region_id"],
                    "school_name": row["school_name"],
                    "name_variant": row.get("name_variant", ""),
                    "council": row.get("council", ""),
                    "ward": row.get("ward", ""),
                    "roster_status": row.get("roster_status", "CONFIRMED"),
                    "pupils": row.get("pupils"),
                    "learners_with_disabilities": row.get("learners_with_disabilities"),
                    "disability_categories": row.get("disability_categories", ""),
                    "audit_headline": row.get("audit_headline", ""),
                    "audit_baseline": row.get("audit_baseline", ""),
                    "planned_modification": row.get("planned_modification", ""),
                    "assessment_focus": row.get("assessment_focus", ""),
                    "priority": row.get("priority", ""),
                    "retest_areas": row.get("retest_areas", []),
                    "active": True,
                },
            )
        self.stdout.write(f"Schools: {School.objects.count()}")

        for row in data["results"]:
            Result.objects.update_or_create(
                result_id=row["result_id"],
                defaults={
                    "result_name": row["result_name"],
                    "intent": row.get("intent", ""),
                    "indicators": row.get("indicators", ""),
                    "project_target": row.get("project_target", ""),
                    "check_in_field": row.get("check_in_field", ""),
                    "evidence_to_request": row.get("evidence_to_request", ""),
                },
            )

        for row in data["questions"]:
            if not Result.objects.filter(pk=row["result_id"]).exists():
                continue
            VerificationQuestion.objects.update_or_create(
                question_id=row["question_id"],
                defaults={
                    "result_id": row["result_id"],
                    "area": row.get("area", ""),
                    "question": row.get("question", ""),
                    "planned_standard": row.get("planned_standard", ""),
                },
            )

        for row in data["evidenceStreams"]:
            EvidenceStream.objects.update_or_create(
                stream_id=row["stream_id"],
                defaults={
                    "stream_name": row["stream_name"],
                    "detail": row.get("detail", ""),
                },
            )

        for row in data["reconciliation"]:
            item, _ = ReconciliationItem.objects.update_or_create(
                item_id=row["item_id"],
                defaults={
                    "issue": row.get("issue", ""),
                    "source_a": row.get("source_a", ""),
                    "source_b": row.get("source_b", ""),
                    "why_it_matters": row.get("why_it_matters", ""),
                    "required_action": row.get("required_action", ""),
                },
            )
            ReconciliationResolution.objects.get_or_create(item=item)

        active_regions = list(
            Region.objects.filter(in_scope=True).values_list("region_id", flat=True)
        )
        ProjectSettings.objects.update_or_create(
            id=1,
            defaults={"active_regions": active_regions},
        )

        for region in Region.objects.filter(in_scope=True):
            ProgrammeWorkbook.objects.get_or_create(region=region)

        username = settings.BOOTSTRAP_ADMIN_USERNAME or "Angel"
        password = settings.BOOTSTRAP_ADMIN_PASSWORD
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "full_name": "System Administrator",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                # When an explicit bootstrap password is provided, allow immediate use.
                "must_change_password": not bool(password),
                "active": True,
            },
        )
        if created:
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created bootstrap admin '{username}'"))
        else:
            changed = False
            if password and not user.has_usable_password():
                user.set_password(password)
                changed = True
            if not user.is_staff or not user.is_superuser or user.role != User.Role.ADMIN:
                user.is_staff = True
                user.is_superuser = True
                user.role = User.Role.ADMIN
                changed = True
            # Local/dev: if password is configured, don't block on first login.
            if password and user.must_change_password:
                user.must_change_password = False
                changed = True
            if not user.active:
                user.active = True
                changed = True
            if changed:
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Updated bootstrap admin '{username}'"))
            else:
                self.stdout.write(f"Bootstrap admin '{username}' already exists")

        # View-only CBM account
        viewer_username = os.getenv("BOOTSTRAP_VIEWER_USERNAME", "viewer")
        viewer_password = os.getenv("BOOTSTRAP_VIEWER_PASSWORD", "ViewOnly123!")
        viewer, viewer_created = User.objects.get_or_create(
            username=viewer_username,
            defaults={
                "full_name": "CBM Viewer",
                "role": User.Role.CBM_VIEWER,
                "is_staff": False,
                "is_superuser": False,
                "must_change_password": False,
                "active": True,
            },
        )
        if viewer_created:
            viewer.set_password(viewer_password)
            viewer.save()
            self.stdout.write(self.style.SUCCESS(f"Created view-only user '{viewer_username}'"))
        else:
            changed = False
            if viewer.role != User.Role.CBM_VIEWER:
                viewer.role = User.Role.CBM_VIEWER
                changed = True
            if viewer.is_staff or viewer.is_superuser:
                viewer.is_staff = False
                viewer.is_superuser = False
                changed = True
            if viewer_password:
                viewer.set_password(viewer_password)
                viewer.must_change_password = False
                changed = True
            if not viewer.active:
                viewer.active = True
                changed = True
            if changed:
                viewer.save()
                self.stdout.write(self.style.SUCCESS(f"Updated view-only user '{viewer_username}'"))
            else:
                self.stdout.write(f"View-only user '{viewer_username}' already exists")

        self.stdout.write(self.style.SUCCESS("Seed complete"))
