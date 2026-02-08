from django.contrib import admin
from .models import Resource


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'order', 'download_count', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['download_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'category', 'description')
        }),
        ('File/Link', {
            'fields': ('file', 'external_link'),
            'description': 'Upload a file OR provide an external link'
        }),
        ('Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Statistics', {
            'fields': ('download_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
