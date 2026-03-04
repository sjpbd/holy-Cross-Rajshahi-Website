from django.contrib import admin
from .models import Teacher, Administration, Staff
from django_summernote.admin import SummernoteModelAdmin


@admin.register(Teacher)
class TeacherAdmin(SummernoteModelAdmin):
    list_display = ['name', 'designation', 'section', 'department', 'order', 'is_active']
    list_filter = ['section', 'department', 'is_active', 'joined_date']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'designation', 'department']
    date_hierarchy = 'created_at'
    summernote_fields = ('bio',)
    
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }
        js = ('js/admin_fix.js',)

    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'designation', 'section', 'department', 'photo')
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
    
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }
        js = ('js/admin_fix.js',)

    
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


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'designation', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'designation']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'designation', 'photo')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )
