from django.contrib import admin
from .models import NewsItem
from django_summernote.admin import SummernoteModelAdmin


@admin.register(NewsItem)
class NewsItemAdmin(SummernoteModelAdmin):
    list_display = ['title', 'is_featured', 'is_published', 'published_date']
    list_filter = ['is_published', 'is_featured', 'published_date']
    list_editable = ['is_featured', 'is_published']
    search_fields = ['title', 'content', 'excerpt']
    date_hierarchy = 'published_date'
    readonly_fields = ['slug', 'published_date', 'updated_at']
    summernote_fields = ('content',)
    prepopulated_fields = {}
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'featured_image')
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured', 'published_date', 'updated_at'),
        }),
    )
