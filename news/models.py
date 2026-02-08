from django.db import models
from django.utils.text import slugify


class NewsItem(models.Model):
    """News articles and announcements"""
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, unique=True, blank=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to='news/', blank=True, help_text="Recommended size: 800x600px")
    excerpt = models.TextField(max_length=500, blank=True, help_text="Short summary for listing pages")
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")
    published_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_date']
        verbose_name = "News Item"
        verbose_name_plural = "News Items"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Auto-generate slug from title"""
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while NewsItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_excerpt(self):
        """Return excerpt or truncated content"""
        if self.excerpt:
            return self.excerpt
        # Strip HTML tags and truncate
        from django.utils.html import strip_tags
        return strip_tags(self.content)[:200] + "..."
