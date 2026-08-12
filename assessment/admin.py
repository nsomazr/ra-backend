from django.contrib import admin

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
    SchoolAssignment,
    SchoolReport,
    VerificationQuestion,
)

admin.site.register(Region)
admin.site.register(School)
admin.site.register(Result)
admin.site.register(VerificationQuestion)
admin.site.register(EvidenceStream)
admin.site.register(ReconciliationItem)
admin.site.register(ReconciliationResolution)
admin.site.register(SchoolAssignment)
admin.site.register(SchoolReport)
admin.site.register(ProgrammeWorkbook)
admin.site.register(ConsentRecord)
admin.site.register(EvidenceFile)
admin.site.register(AuditLog)
admin.site.register(ProjectSettings)
