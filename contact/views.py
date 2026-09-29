# contact/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import FormView
from .forms import ContactForm
from .models import ContactInfo


class ContactView(FormView):
    """Contact page view with form submission"""
    template_name = 'contact/contact.html'
    form_class = ContactForm
    success_url = '/contact/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_info'] = ContactInfo.load()
        context['page_title'] = "Contact Us - Holy Cross School and College"
        context['page_description'] = "Get in touch with Holy Cross School and College, Rajshahi. Visit us, call, or send us a message."
        return context

    def form_valid(self, form):
        # Save the submission
        submission = form.save()
        
        # Get school contact info for the recipient email
        contact_info = ContactInfo.load()
        recipient_email = contact_info.email
        
        if recipient_email:
            try:
                from django.core.mail import EmailMessage
                from django.conf import settings

                subject = f"New Contact Form Submission: {submission.subject}"
                email_message = (
                    "You have received a new contact form submission.\n\n"
                    f"Name: {submission.name}\n"
                    f"Email: {submission.email}\n"
                    f"Phone: {submission.phone or 'Not provided'}\n"
                    f"Subject: {submission.subject}\n\n"
                    f"Message:\n{submission.message}\n\n"
                    "---\n"
                    "This message was sent from the Holy Cross School website contact form.\n"
                )

                EmailMessage(
                    subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    reply_to=[submission.email] if submission.email else None,
                ).send(fail_silently=False)
            except Exception as e:
                # Log error or handle it as needed
                print(f"Error sending contact email: {e}")

        messages.success(self.request, 'Thank you for contacting us! We will get back to you soon.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
