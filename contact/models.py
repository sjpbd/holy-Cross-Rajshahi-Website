# contact/models.py
from django.db import models


class ContactInfo(models.Model):
    """Singleton model for school contact information"""
    # Contact Details
    address = models.TextField(help_text="School address")
    city = models.CharField(max_length=100,blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=100, help_text="Primary phone number")
    email = models.EmailField(help_text="Primary email address")
    
    # Office Hours
    office_hours = models.TextField(blank=True, help_text="Office hours (e.g., Mon-Fri: 8:00 AM - 4:00 PM)")
    
    # Map Coordinates
    map_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text="Latitude for Google Maps")
    map_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text="Longitude for Google Maps")
    map_embed_url = models.TextField(blank=True, help_text="Google Maps embed iframe URL")
    
    # Meta
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"

    def __str__(self):
        return "School Contact Information"

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


class ContactSubmission(models.Model):
    """Model to store contact form submissions"""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Admin notes")

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"

    def __str__(self):
        return f"{self.name} - {self.subject} ({self.submitted_at.strftime('%Y-%m-%d')})"
