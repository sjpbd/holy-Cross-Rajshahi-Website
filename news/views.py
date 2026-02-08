from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from .models import NewsItem


class NewsListView(ListView):
    """News listing with HTMX pagination"""
    model = NewsItem
    template_name = 'news/list.html'
    context_object_name = 'news_list'
    paginate_by = 6
    
    def get_queryset(self):
        return NewsItem.objects.filter(is_published=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "News & Events - Holy Cross School"
        
        # Add featured news items
        context['featured_news'] = NewsItem.objects.filter(
            is_published=True, 
            is_featured=True
        )[:2]
        
        # For HTMX requests, use partial template
        if self.request.htmx:
            self.template_name = 'news/partials/news_items.html'
        
        return context


class NewsDetailView(DetailView):
    """Single news article detail"""
    model = NewsItem
    template_name = 'news/detail.html'
    context_object_name = 'news'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return NewsItem.objects.filter(is_published=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"{self.object.title} - Holy Cross School"
        context['page_description'] = self.object.get_excerpt()
        
        # Related news (same category or recent)
        context['related_news'] = NewsItem.objects.filter(
            is_published=True
        ).exclude(pk=self.object.pk)[:3]
        
        return context
