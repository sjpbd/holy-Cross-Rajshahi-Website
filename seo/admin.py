from django.contrib import admin
from .models import SEOMetadata

@admin.register(SEOMetadata)
class SEOMetadataAdmin(admin.ModelAdmin):
    list_display = ('path', 'view_name', 'title', 'updated_at')
    search_fields = ('path', 'view_name', 'title', 'description')
    list_filter = ('og_type', 'robots')
    
    fieldsets = (
        ('Target', {
            'fields': ('path', 'view_name'),
            'description': 'Specify either the URL path or the Django view name.'
        }),
        ('Basic SEO', {
            'fields': ('title', 'description', 'keywords', 'robots')
        }),
        ('Social Media (Open Graph)', {
            'fields': ('og_title', 'og_description', 'og_image', 'og_type')
        }),
    )
