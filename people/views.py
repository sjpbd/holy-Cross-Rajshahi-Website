from django.shortcuts import render
from django.views.generic import ListView
from .models import Teacher, Administration


class TeacherListView(ListView):
    """Teachers listing page"""
    model = Teacher
    template_name = 'people/teachers.html'
    context_object_name = 'teachers'
    
    def get_queryset(self):
        return Teacher.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Our Teachers - Holy Cross School"
        context['page_description'] = "Meet our dedicated and qualified teaching staff at Holy Cross School and College."
        return context


class AdministrationListView(ListView):
    """Administration listing page"""
    model = Administration
    template_name = 'people/administration.html'
    context_object_name = 'administrative_staff'
    
    def get_queryset(self):
        return Administration.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Administration - Holy Cross School"
        return context
