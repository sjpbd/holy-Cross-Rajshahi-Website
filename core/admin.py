from django.contrib import admin
from .models import Slider, SchoolInfo, FactsFigures
from django_summernote.admin import SummernoteModelAdmin


@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'subtitle']
    prepopulated_fields = {}
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'subtitle', 'image', 'link')
        }),
        ('Settings', {
            'fields': ('order', 'is_active')
        }),
    )


@admin.register(SchoolInfo)
class SchoolInfoAdmin(SummernoteModelAdmin):
    """Singleton admin for school information"""
    summernote_fields = ('history', 'mission', 'vision', 'goal', 'principal_message', 'vice_principal_message')
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SchoolInfo.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False
    
    fieldsets = (
        ('Branding', {
            'fields': ('logo', 'favicon'),
            'description': 'Upload school logo and favicon for the website'
        }),
        ('About Us', {
            'fields': ('history', 'mission', 'vision', 'goal')
        }),
        ("Principal's Information", {
            'fields': ('principal_name', 'principal_photo', 'principal_message')
        }),
        ("Vice Principal's Information", {
            'fields': ('vice_principal_name', 'vice_principal_photo', 'vice_principal_message')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'youtube_url', 'instagram_url')
        }),
    )


@admin.register(FactsFigures)
class FactsFiguresAdmin(admin.ModelAdmin):
    list_display = ['title', 'number', 'icon', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title']
