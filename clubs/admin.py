from django.contrib import admin
from django.db import models
from .models import Club
from django_summernote.widgets import SummernoteWidget

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'coordinator_name', 'established_year', 'order', 'is_active']
    list_filter = ['is_active', 'established_year']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'motto', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    formfield_overrides = {
        models.TextField: {'widget': SummernoteWidget}
    }

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
