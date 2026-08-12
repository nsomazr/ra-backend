from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ConsentRecordViewSet,
    EvidenceFileViewSet,
    EvidenceStreamViewSet,
    FrameworkBundleView,
    ProgrammeWorkbookViewSet,
    ProjectSettingsView,
    ReconciliationViewSet,
    RegionViewSet,
    ResultViewSet,
    SchoolReportViewSet,
    SchoolViewSet,
    VerificationQuestionViewSet,
)

router = DefaultRouter()
router.register("regions", RegionViewSet)
router.register("schools", SchoolViewSet)
router.register("results", ResultViewSet)
router.register("questions", VerificationQuestionViewSet)
router.register("evidence-streams", EvidenceStreamViewSet)
router.register("reconciliation", ReconciliationViewSet)
router.register("reports", SchoolReportViewSet)
router.register("programmes", ProgrammeWorkbookViewSet)
router.register("consents", ConsentRecordViewSet)
router.register("evidence", EvidenceFileViewSet)

urlpatterns = [
    path("framework/", FrameworkBundleView.as_view(), name="framework-bundle"),
    path("settings/", ProjectSettingsView.as_view(), name="project-settings"),
    path("", include(router.urls)),
]
