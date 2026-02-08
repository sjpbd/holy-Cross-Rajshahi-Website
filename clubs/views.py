from django.shortcuts import render
from django.views.generic import ListView, DetailView
from .models import Club


class ClubListView(ListView):
    """Clubs listing page"""
    model = Club
    template_name = 'clubs/list.html'
    context_object_name = 'clubs'
    
    def get_queryset(self):
        return Club.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Clubs & Organizations - Holy Cross School"
        context['page_description'] = "Explore the various clubs and organizations at Holy Cross School and College."
        return context


class ClubDetailView(DetailView):
    """Single club detail page"""
    model = Club
    template_name = 'clubs/detail.html'
    context_object_name = 'club'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Club.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"{self.object.name} - Holy Cross School"
        context['page_description'] = self.object.motto
        return context
