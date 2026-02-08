from django.contrib import admin
from .models import Teacher, Administration
from django_summernote.admin import SummernoteModelAdmin


@admin.register(Teacher)
class TeacherAdmin(SummernoteModelAdmin):
    list_display = ['name', 'designation', 'department', 'order', 'is_active']
    list_filter = ['department', 'is_active', 'joined_date']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'designation', 'department']
    date_hierarchy = 'created_at'
    summernote_fields = ('bio',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'designation', 'department', 'photo')
        }),
        ('Details', {
            'fields': ('bio', 'email', 'phone', 'joined_date')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )


@admin.register(Administration)
class AdministrationAdmin(SummernoteModelAdmin):
    list_display = ['name', 'role', 'designation', 'order', 'is_active']
    list_filter = ['role', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'designation']
    summernote_fields = ('bio', 'message')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'role', 'designation', 'photo')
        }),
        ('Content', {
            'fields': ('bio', 'message')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )
