from django.db import models
from django.core.validators import FileExtensionValidator


class Resource(models.Model):
    """Downloadable resources for students and parents"""
    CATEGORY_CHOICES = [
        ('syllabus', 'Syllabus'),
        ('rules', 'Rules & Regulations'),
        ('yearbook', 'Yearbook'),
        ('forms', 'Forms'),
        ('calendar', 'Academic Calendar'),
        ('handbook', 'Handbook'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=300)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, help_text="Brief description of the resource")
    file = models.FileField(
        upload_to='resources/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx'])],
        help_text="Upload file or provide external link below"
    )
    external_link = models.URLField(blank=True, help_text="External link if not uploading file")
    download_count = models.PositiveIntegerField(default=0, editable=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order', '-created_at']
        verbose_name = "Resource"
        verbose_name_plural = "Resources"

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def get_link(self):
        """Return file URL or external link"""
        if self.file:
            return self.file.url
        return self.external_link

    def increment_download_count(self):
        """Increment download count atomically"""
        self.download_count = models.F('download_count') + 1
        self.save(update_fields=['download_count'])
        self.refresh_from_db()
