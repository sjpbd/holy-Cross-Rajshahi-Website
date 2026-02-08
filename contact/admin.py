# contact/admin.py
from django.contrib import admin
from .models import ContactInfo, ContactSubmission


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    """Singleton admin for contact information"""
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not ContactInfo.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False
    
    fieldsets = (
        ('Contact Details', {
            'fields': ('address', 'city', 'postal_code', 'phone', 'email')
        }),
        ('Office Hours', {
            'fields': ('office_hours',)
        }),
        ('Google Maps', {
            'fields': ('map_latitude', 'map_longitude', 'map_embed_url'),
            'description': 'Add map coordinates and Google Maps embed URL'
        }),
    )


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    """Admin for contact form submissions"""
    list_display = ['name', 'email', 'subject', 'submitted_at', 'is_read']
    list_filter = ['is_read', 'submitted_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['name', 'email', 'phone', 'subject', 'message', 'submitted_at']
    list_editable = ['is_read']
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Submission Details', {
            'fields': ('name', 'email', 'phone', 'subject', 'message', 'submitted_at')
        }),
        ('Admin', {
            'fields': ('is_read', 'notes')
        }),
    )
    
    def has_add_permission(self, request):
        # Prevent adding submissions from admin
        return False
