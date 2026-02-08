# core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from .models import Slider, SchoolInfo, FactsFigures
from notices.models import Notice
from news.models import NewsItem


class HomeView(TemplateView):
    """Homepage view with all necessary context"""
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Hero Slider
        context['sliders'] = Slider.objects.filter(is_active=True)[:5]
        
        # Latest Notices for Ticker (important ones)
        context['ticker_notices'] = Notice.objects.filter(
            is_active=True, 
            is_important=True
        )[:5]
        
        # Notice Board (latest 5)
        context['notices'] = Notice.objects.filter(is_active=True)[:5]
        
        # Facts & Figures
        context['facts'] = FactsFigures.objects.filter(is_active=True)[:4]
        
        # Latest News (featured or latest 3)
        context['latest_news'] = NewsItem.objects.filter(
            is_published=True
        ).filter(is_featured=True)[:3] or NewsItem.objects.filter(
            is_published=True
        )[:3]
        
        # SEO
        context['page_title'] = "Holy Cross School and College, Rajshahi"
        context['page_description'] = "Welcome to Holy Cross School and College, Rajshahi - A premier educational institution dedicated to excellence in education."
        
        return context


class AboutView(TemplateView):
    """About pages (history, mission, vision)"""
    template_name = 'about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = self.kwargs.get('page', 'history')
        return context


class PrivacyPolicyView(TemplateView):
    template_name = 'pages/privacy.html'

class TermsOfServiceView(TemplateView):
    template_name = 'pages/terms.html'

class SitemapView(TemplateView):
    template_name = 'pages/sitemap.html'
