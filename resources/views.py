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
    """Proxy external resources (like large Google Drive PDFs) avoiding CORS and Virus Scan walls.
    Caches the file locally and serves it using FileResponse to support HTTP Range requests for Flipbooks."""
    import urllib.request
    import http.cookiejar
    import re
    import os
    from django.conf import settings
    from django.http import Http404, HttpResponse, FileResponse, HttpResponseRedirect
    
    resource = get_object_or_404(Resource, pk=pk, is_active=True)
    
    # If the file is already uploaded natively, just redirect to it.
    if resource.file:
        return HttpResponseRedirect(resource.file.url)
        
    if not resource.external_link:
        raise Http404("No external link provided.")
        
    # Check if we already cached this external link locally
    cache_dir = os.path.join(settings.MEDIA_ROOT, 'cached_pdfs')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"resource_{pk}.pdf")
    
    # Serve from cache if it exists and is a valid file
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1024:
        return FileResponse(open(cache_path, 'rb'), content_type='application/pdf')
        
    url = resource.external_link
    # Convert Google Drive 'view' links to direct 'download' links
    if "drive.google.com/file/d/" in url:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            url = f"https://drive.google.com/uc?export=download&id={match.group(1)}"
            
    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = opener.open(req)
        
        content_type = response.headers.get('Content-Type', '')
        
        # If Google Drive intercepts large files with a virus scan warning (HTML page)
        if 'text/html' in content_type.lower():
            html_content = response.read().decode('utf-8', errors='ignore')
            
            # gdown logic: look for the download_warning cookie first
            confirm_token = None
            for cookie in cj:
                if cookie.name.startswith('download_warning'):
                    confirm_token = cookie.value
                    break
            
            # fallback to extracting from HTML
            if not confirm_token:
                confirm_match = re.search(r'confirm=([0-9A-Za-z_-]+)', html_content)
                if confirm_match:
                    confirm_token = confirm_match.group(1)
                    
            if confirm_token:
                bypass_url = url + f"&confirm={confirm_token}"
                req_bypass = urllib.request.Request(bypass_url, headers={'User-Agent': 'Mozilla/5.0'})
                response = opener.open(req_bypass)
            else:
                return HttpResponse("Failed to bypass Google Drive virus scan. Please upload file directly.", status=500)
        
        # Download and cache the file locally
        with open(cache_path, 'wb') as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                
        # Serve the cached file using Django's FileResponse which inherently supports HTTP Range requests!
        return FileResponse(open(cache_path, 'rb'), content_type='application/pdf')
    except Exception as e:
        return HttpResponse(f"Error accessing external resource: {str(e)}", status=500)
