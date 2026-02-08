# notices/admin.py
from django.contrib import admin
from .models import Notice
from django_summernote.admin import SummernoteModelAdmin


@admin.register(Notice)
class NoticeAdmin(SummernoteModelAdmin):
    list_display = ['title', 'is_important', 'is_active', 'view_count', 'created_at']
    list_filter = ['is_active', 'is_important', 'created_at']
    list_editable = ['is_important', 'is_active']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['view_count', 'created_at', 'updated_at']
    summernote_fields = ('description',)
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'attachment')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'is_important')
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
