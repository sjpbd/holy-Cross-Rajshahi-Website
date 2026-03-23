from django.contrib import admin
from django.db import models
from .models import Slider, SchoolInfo, FactsFigures, StaticPage, AdmissionBanner
from django_summernote.admin import SummernoteModelAdmin
from django_summernote.widgets import SummernoteWidget


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
class SchoolInfoAdmin(admin.ModelAdmin):
    """Singleton admin for school information"""
    
    formfield_overrides = {
        models.TextField: {'widget': SummernoteWidget}
    }

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
            'fields': ('history', 'mission', 'vision', 'goal'),
            'classes': ('modern-editor',),
        }),

        ("Principal's Information", {
            'fields': ('principal_name', 'principal_photo', 'principal_message'),
            'classes': ('modern-editor',),
        }),

        ("Vice Principal's Information", {
            'fields': ('vice_principal_name', 'vice_principal_photo', 'vice_principal_message'),
            'classes': ('modern-editor',),
        }),

        ('Contact Information', {
            'fields': ('address', 'city', 'postal_code', 'phone', 'email')
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


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_active', 'updated_at']
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'content']

    formfield_overrides = {
        models.TextField: {'widget': SummernoteWidget}
    }


@admin.register(AdmissionBanner)
class AdmissionBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'is_blinking', 'updated_at']
    list_editable = ['is_active', 'is_blinking']

    fieldsets = (
        ('Banner Content', {
            'fields': ('title', 'subtitle', 'button_text')
        }),
        ('Attachments & Links', {
            'description': 'Upload a PDF or image of the admission notice, or provide an external link.',
            'fields': ('notice_pdf', 'notice_image', 'external_link')
        }),
        ('Display Controls', {
            'fields': ('is_active', 'is_blinking')
        }),
    )
