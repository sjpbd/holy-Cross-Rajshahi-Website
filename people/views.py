from django.views.generic import ListView, DetailView
from .models import Teacher, Administration, Staff


class TeacherListView(ListView):
    """Teachers listing page"""
    model = Teacher
    template_name = 'people/teachers.html'
    context_object_name = 'teachers'
    
    def get_queryset(self):
        return Teacher.objects.filter(is_active=True).order_by('section', 'order', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Our Teachers - Holy Cross School"
        context['page_description'] = "Meet our dedicated and qualified teaching staff at Holy Cross School and College."
        # Group by section
        teachers = self.get_queryset()
        sections = []
        for section_id, section_name in Teacher.SECTION_CHOICES:
            section_teachers = teachers.filter(section=section_id)
            if section_teachers.exists():
                sections.append({
                    'id': section_id,
                    'name': section_name,
                    'teachers': section_teachers
                })
        context['sections'] = sections
        return context


class TeacherDetailView(DetailView):
    """Teacher detail page"""
    model = Teacher
    template_name = 'people/teacher_detail.html'
    context_object_name = 'teacher'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"{self.object.name} - Holy Cross School"
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


class StaffListView(ListView):
    """Staff listing page"""
    model = Staff
    template_name = 'people/staff.html'
    context_object_name = 'staff_members'

    def get_queryset(self):
        return Staff.objects.filter(is_active=True).order_by('category', 'order', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Our Staff - Holy Cross School"
        # Group by category
        staff = self.get_queryset()
        categories = []
        for cat_id, cat_name in Staff.STAFF_CATEGORY_CHOICES:
            cat_staff = staff.filter(category=cat_id)
            if cat_staff.exists():
                categories.append({
                    'id': cat_id,
                    'name': cat_name,
                    'staff': cat_staff
                })
        context['categories'] = categories
        return context
