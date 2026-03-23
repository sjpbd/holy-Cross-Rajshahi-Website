# notices/admin.py
from django.contrib import admin
from django.db import models
from .models import Notice
from django_summernote.widgets import SummernoteWidget


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_important', 'is_active', 'view_count', 'created_at']
    list_filter = ['is_active', 'is_important', 'created_at']
    list_editable = ['is_important', 'is_active']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['view_count', 'created_at', 'updated_at']
    formfield_overrides = {
        models.TextField: {'widget': SummernoteWidget}
    }


    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'attachment'),
            'classes': ('modern-editor',),
        }),

        ('Display Settings', {
            'fields': ('is_active', 'is_important')
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
