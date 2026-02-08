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
        form.save()
        messages.success(self.request, 'Thank you for contacting us! We will get back to you soon.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
