from django.views.generic import ListView, DetailView
from .models import Teacher, Administration, Staff, GoverningBodyMember


class TeacherListView(ListView):
    """Teachers listing page"""
    model = Teacher
    template_name = 'people/teachers.html'
    context_object_name = 'teachers'
    paginate_by = 16
    
    def get_queryset(self):
        queryset = Teacher.objects.filter(is_active=True).order_by('section', 'order', 'name')
        section = self.request.GET.get('section')
        if section and any(section == choice[0] for choice in Teacher.SECTION_CHOICES):
            queryset = queryset.filter(section=section)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Our Teachers - Holy Cross School"
        context['page_description'] = "Meet our dedicated and qualified teaching staff at Holy Cross School and College."
        
        # For the filter tabs
        context['sections'] = Teacher.SECTION_CHOICES
        context['current_section'] = self.request.GET.get('section', '')
        context['total_teachers'] = Teacher.objects.filter(is_active=True).count()
        
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


class GoverningBodyListView(ListView):
    """Governing Body / Board of Directors page"""
    model = GoverningBodyMember
    template_name = 'people/governing_body.html'
    context_object_name = 'members'

    def get_queryset(self):
        return GoverningBodyMember.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Governing Body - Holy Cross School & College"
        context['page_description'] = "Meet the esteemed members of the Governing Body of Holy Cross School and College, Rajshahi."
        members = self.get_queryset()
        context['chairman'] = members.filter(role='chairman').first()
        context['other_members'] = members.exclude(role='chairman')
        return context
