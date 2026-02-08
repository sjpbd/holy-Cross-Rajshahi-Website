from django.contrib import admin
from .models import Club
from django_summernote.admin import SummernoteModelAdmin

@admin.register(Club)
class ClubAdmin(SummernoteModelAdmin):
    list_display = ['name', 'coordinator_name', 'established_year', 'order', 'is_active']
    list_filter = ['is_active', 'established_year']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'motto', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    summernote_fields = ('description', 'objectives')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'logo', 'motto', 'established_year')
        }),
        ('Content', {
            'fields': ('description', 'objectives')
        }),
        ('Coordinator', {
            'fields': ('coordinator_name', 'coordinator_email')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )
