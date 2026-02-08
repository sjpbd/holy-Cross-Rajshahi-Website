# core/models.py
from django.db import models
from django.core.validators import FileExtensionValidator


class Slider(models.Model):
    """Hero slider images for homepage"""
    image = models.ImageField(upload_to='slider/', help_text="Recommended size: 1920x800px")
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    link = models.URLField(blank=True, help_text="Optional link when slider is clicked")
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Slider"
        verbose_name_plural = "Sliders"

    def __str__(self):
        return self.title


class SchoolInfo(models.Model):
    """Singleton model for school information"""
    # About Us
    history = models.TextField(blank=True, help_text="History of the school")
    mission = models.TextField(blank=True, help_text="Mission statement")
    vision = models.TextField(blank=True, help_text="Vision statement")
    goal = models.TextField(blank=True, help_text="Goals and objectives")
    
    # Branding
    logo = models.ImageField(
        upload_to='branding/',
        blank=True,
        null=True,
        help_text="School logo (Recommended size: 200x200px, transparent background)"
    )
    
    # Messages
    principal_name = models.CharField(max_length=200, blank=True)
    principal_message = models.TextField(blank=True)
    principal_photo = models.ImageField(upload_to='administration/', blank=True)
    
    vice_principal_name = models.CharField(max_length=200, blank=True)
    vice_principal_message = models.TextField(blank=True)
    vice_principal_photo = models.ImageField(upload_to='administration/', blank=True)
    
    # Contact Information
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    
    # Social Media
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    
    # Meta
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Information"
        verbose_name_plural = "School Information"

    def __str__(self):
        return "Holy Cross School Information"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (Singleton pattern)"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton instance"""
        pass

    @classmethod
    def load(cls):
        """Load the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class FactsFigures(models.Model):
    """Statistics and facts about the school"""
    title = models.CharField(max_length=100, help_text="e.g., 'Students', 'Teachers', 'Years of Excellence'")
    number = models.CharField(max_length=50, help_text="e.g., '5000+', '150+', '75'")
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., 'fa-users')")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Facts & Figures"
        verbose_name_plural = "Facts & Figures"

    def __str__(self):
        return f"{self.title}: {self.number}"
