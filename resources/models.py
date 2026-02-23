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

    def get_extension(self):
        """Return file extension without dot"""
        if self.file:
            import os
            return os.path.splitext(self.file.name)[1][1:].lower()
        return None

    def get_file_size(self):
        """Return human readable file size"""
        if self.file:
            try:
                size = self.file.size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
            except:
                return None
        return None

    def increment_download_count(self):
        """Increment download count atomically"""
        from django.db.models import F
        self.download_count = F('download_count') + 1
        self.save(update_fields=['download_count'])
        self.refresh_from_db()
