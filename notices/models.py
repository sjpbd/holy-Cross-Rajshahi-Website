# notices/models.py
from django.db import models
from django.urls import reverse
from django.core.validators import FileExtensionValidator
import os


class Notice(models.Model):
    """Notice board items"""
    title = models.CharField(max_length=300)
    description = models.TextField(help_text="Full notice content")
    attachment = models.FileField(
        upload_to='notices/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])],
        help_text="Attach PDF or image file"
    )
    view_count = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=True, help_text="Show on website")
    is_important = models.BooleanField(default=False, help_text="Highlight in ticker")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notice"
        verbose_name_plural = "Notices"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('notice_detail', kwargs={'pk': self.pk})

    def increment_view_count(self):
        """Increment view count atomically"""
        self.view_count = models.F('view_count') + 1
        self.save(update_fields=['view_count'])
        self.refresh_from_db()

    @property
    def attachment_is_pdf(self):
        if self.attachment:
            name, extension = os.path.splitext(self.attachment.name)
            return extension.lower() == '.pdf'
        return False

    @property
    def attachment_is_image(self):
        if self.attachment:
            name, extension = os.path.splitext(self.attachment.name)
            return extension.lower() in ['.jpg', '.jpeg', '.png']
        return False
