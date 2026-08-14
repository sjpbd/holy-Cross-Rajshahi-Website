from django.contrib import admin
from django import forms
from .models import NewsItem
from django_summernote.widgets import SummernoteWidget


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_featured', 'is_published', 'published_date']
    list_filter = ['is_published', 'is_featured', 'published_date']
    list_editable = ['is_featured', 'is_published']
    search_fields = ['title', 'content', 'excerpt']
    date_hierarchy = 'published_date'
    readonly_fields = ['slug', 'published_date', 'updated_at']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            kwargs['widget'] = SummernoteWidget()
        elif db_field.name == 'excerpt':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


    prepopulated_fields = {}
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'featured_image'),
            'classes': ('modern-editor',),
        }),

        ('Publishing', {
            'fields': ('is_published', 'is_featured', 'published_date', 'updated_at'),
        }),
    )
