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
    favicon = models.ImageField(
        upload_to='branding/',
        blank=True,
        null=True,
        help_text="Website favicon (Recommended size: 32x32px or 16x16px, .ico or .png)"
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
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
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


class StaticPage(models.Model):
    """Generic model for custom content pages (e.g., Holy Cross Brothers)"""
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, help_text="Used in the URL (e.g., 'holy-cross-brothers')")
    banner_image = models.ImageField(upload_to='pages/banners/', blank=True, null=True)
    content = models.TextField(help_text="Main content of the page (supports HTML/Summernote)")
    
    # Meta
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Custom Page"
        verbose_name_plural = "Custom Pages"

    def __str__(self):
        return self.title


class AdmissionBanner(models.Model):
    """Admission announcement banner shown prominently on the homepage."""
    title = models.CharField(
        max_length=200,
        default="Admission is Open!",
        help_text="Main banner headline, e.g. 'Admission is Open 2025-26'"
    )
    subtitle = models.CharField(
        max_length=400,
        blank=True,
        help_text="Short subtitle text below the headline"
    )
    button_text = models.CharField(
        max_length=100,
        default="View Admission Notice",
        help_text="Text shown on the call-to-action button"
    )
    external_link = models.URLField(
        blank=True,
        help_text="Optional external URL to link to (e.g. Google Drive link)"
    )
    # File attachments
    notice_pdf = models.FileField(
        upload_to='admission/notices/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF of admission circular/notice"
    )
    notice_image = models.ImageField(
        upload_to='admission/notices/',
        blank=True,
        null=True,
        help_text="Upload image of admission notice/circular"
    )
    # Control
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle the banner on/off sitewide"
    )
    is_blinking = models.BooleanField(
        default=True,
        help_text="Enable attention-grabbing blink animation on the banner"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Admission Banner"
        verbose_name_plural = "Admission Banner"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Admission Banner ({status}) – {self.title}"

    @property
    def attachment_url(self):
        """Returns the best available attachment URL."""
        if self.notice_pdf:
            return self.notice_pdf.url
        if self.notice_image:
            return self.notice_image.url
        if self.external_link:
            return self.external_link
        return None
