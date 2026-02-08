from django.db import models

class SEOMetadata(models.Model):
    """
    Model to store SEO metadata for specific paths or views.
    """
    path = models.CharField(max_length=255, unique=True, help_text="URL path (e.g., /about/ or /contact/). Leave empty if using View Name.")
    view_name = models.CharField(max_length=255, blank=True, null=True, help_text="Django view name (e.g., 'home', 'contact'). Optional if Path is set.")
    
    title = models.CharField(max_length=255, help_text="Page Title (appears in browser tab and search results)")
    description = models.TextField(blank=True, help_text="Meta Description (summary for search results)")
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords")
    
    # Open Graph (Social Media)
    og_title = models.CharField(max_length=255, blank=True, help_text="Social Media Title (defaults to Page Title)")
    og_description = models.TextField(blank=True, help_text="Social Media Description (defaults to Meta Description)")
    og_image = models.ImageField(upload_to='seo/og_images/', blank=True, null=True, help_text="Image for social media sharing (1200x630 recommended)")
    og_type = models.CharField(max_length=50, default='website', choices=[
        ('website', 'Website'),
        ('article', 'Article'),
        ('profile', 'Profile'),
    ], help_text="Type of content")
    
    # Robots
    robots = models.CharField(max_length=100, default='index, follow', help_text="Robots meta tag (e.g., 'index, follow', 'noindex, nofollow')")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SEO Metadata"
        verbose_name_plural = "SEO Metadata"
        ordering = ['path']

    def __str__(self):
        return self.path or self.view_name or "Untitled SEO Metadata"

    def get_og_title(self):
        return self.og_title or self.title

    def get_og_description(self):
        return self.og_description or self.description
