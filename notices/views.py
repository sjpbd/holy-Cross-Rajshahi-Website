# notices/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Notice
from django.db import models


class NoticeListView(ListView):
    """All notices listing with filtering"""
    model = Notice
    template_name = 'notices/list.html'
    context_object_name = 'notices'
    paginate_by = 12

    def get_queryset(self):
        queryset = Notice.objects.filter(is_active=True)
        
        # Filter by importance if requested
        filter_type = self.request.GET.get('filter')
        if filter_type == 'important':
            queryset = queryset.filter(is_important=True)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Notices - Holy Cross School"
        context['page_description'] = "Stay updated with the latest announcements and important information from Holy Cross School and College"
        return context


class NoticeDetailView(DetailView):
    """Single notice detail with view tracking"""
    model = Notice
    template_name = 'notices/detail.html'
    context_object_name = 'notice'

    def get_queryset(self):
        return Notice.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related notices (same importance level, excluding current)
        context['related_notices'] = Notice.objects.filter(
            is_active=True,
            is_important=self.object.is_important
        ).exclude(pk=self.object.pk)[:4]
        
        context['page_title'] = f"{self.object.title} - Holy Cross School"
        context['page_description'] = self.object.description[:160] if self.object.description else "View notice details"
        
        return context
    
    def get(self, request, *args, **kwargs):
        """Increment view count when notice is viewed"""
        response = super().get(request, *args, **kwargs)
        
        # Increment view count
        notice = self.get_object()
        Notice.objects.filter(pk=notice.pk).update(view_count=models.F('view_count') + 1)
        
        return response


@csrf_exempt
@require_POST
def increment_notice_view(request, pk):
    """HTMX endpoint to increment notice view count via AJAX"""
    try:
        notice = get_object_or_404(Notice, pk=pk, is_active=True)
        # Use F() expression to avoid race conditions
        from django.db.models import F
        Notice.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
        return JsonResponse({'success': True, 'view_count': notice.view_count + 1})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)