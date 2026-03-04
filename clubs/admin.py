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
    summernote_fields = ('description', 'mission', 'vision', 'objectives')
    
    class Media:
        css = {
            'all': ('css/admin_modern.css',)
        }
        js = ('js/admin_fix.js',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'logo', 'motto', 'established_year')
        }),
        ('Content', {
            'fields': ('description', 'mission', 'vision', 'objectives'),
            'classes': ('modern-editor',),
        }),
        ('Coordinator', {
            'fields': ('coordinator_name', 'coordinator_email')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )
