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
        
        # Group resources by category
        from collections import defaultdict
        resources_by_category = defaultdict(list)
        for resource in context['resources']:
            resources_by_category[resource.get_category_display()].append(resource)
        
        context['resources_by_category'] = dict(resources_by_category)
        return context


def track_download(request, pk):
    """Track resource downloads"""
    resource = get_object_or_404(Resource, pk=pk, is_active=True)
    resource.increment_download_count()
    return HttpResponse(status=200)
