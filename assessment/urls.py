from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .sync import (
    AdminBackupView,
    AdminRestoreView,
    EvidenceDownloadView,
    EvidenceUploadView,
    PresenceView,
    SyncConflictResolveView,
    SyncConflictsView,
    SyncPullView,
    SyncPushView,
)
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
    path("sync/push/", SyncPushView.as_view(), name="sync-push"),
    path("sync/pull/", SyncPullView.as_view(), name="sync-pull"),
    path("sync/conflicts/", SyncConflictsView.as_view(), name="sync-conflicts"),
    path("sync/conflicts/resolve/", SyncConflictResolveView.as_view(), name="sync-conflicts-resolve"),
    path("presence/", PresenceView.as_view(), name="presence"),
    path("admin/backup/", AdminBackupView.as_view(), name="admin-backup"),
    path("admin/restore/", AdminRestoreView.as_view(), name="admin-restore"),
    path("evidence/upload/", EvidenceUploadView.as_view(), name="evidence-upload-list"),
    path("evidence/upload/<str:evidence_id>/", EvidenceUploadView.as_view(), name="evidence-upload-detail"),
    path("evidence/download/<str:evidence_id>/", EvidenceDownloadView.as_view(), name="evidence-download"),
    path("", include(router.urls)),
]
