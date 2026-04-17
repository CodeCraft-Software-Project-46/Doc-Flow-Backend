from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # This controls what columns show up in the admin table
    list_display = ('timestamp', 'user', 'action', 'document_id')
    
    # Adds a filter sidebar so you can quickly find specific events
    list_filter = ('action', 'timestamp')
    
    # Adds a search bar to search by username or description
    search_fields = ('user__username', 'description')
    
    # You can't change history!
    readonly_fields = ('timestamp',)