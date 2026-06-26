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

def proxy_external_resource(request, pk):
    """Proxy external resources (like Google Drive PDFs) to avoid CORS issues with Flipbook"""
    import urllib.request
    import re
    from django.http import Http404, StreamingHttpResponse
    
    resource = get_object_or_404(Resource, pk=pk, is_active=True)
    if not resource.external_link:
        raise Http404("No external link provided.")
        
    url = resource.external_link
    # Convert Google Drive 'view' links to direct 'download' links
    if "drive.google.com/file/d/" in url:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        content_type = response.headers.get('Content-Type', 'application/pdf')
        
        # Stream the response chunk by chunk to avoid loading large PDFs into memory
        def file_iterator(resp, chunk_size=8192):
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        return StreamingHttpResponse(file_iterator(response), content_type=content_type)
    except Exception as e:
        return HttpResponse(f"Error accessing external resource: {str(e)}", status=500)
