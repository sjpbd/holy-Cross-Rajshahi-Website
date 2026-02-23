from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.http import HttpResponse
from .models import Resource


class ResourceListView(ListView):
    """Resources listing grouped by category"""
    model = Resource
    template_name = 'resources/list.html'
    context_object_name = 'resources'
    
    def get_queryset(self):
        return Resource.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Resources - Holy Cross School"
        
        # Get category choices for filtering
        context['categories'] = [
            {'slug': choice[0], 'name': choice[1]} 
            for choice in Resource.CATEGORY_CHOICES
        ]
        
        return context


def track_download(request, pk):
    """Track resource downloads"""
    resource = get_object_or_404(Resource, pk=pk, is_active=True)
    resource.increment_download_count()
    return HttpResponse(status=200)
