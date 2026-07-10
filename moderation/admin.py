from django.contrib import admin

from .models import AuditLog, ContentReport

admin.site.register(ContentReport)
admin.site.register(AuditLog)
