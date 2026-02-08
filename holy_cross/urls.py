# holy_cross/urls.py (project's main URL configuration)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import HomeView, AboutView, PrivacyPolicyView, TermsOfServiceView, SitemapView
from people.views import TeacherListView, AdministrationListView
from notices.views import NoticeListView, NoticeDetailView, increment_notice_view
from news.views import NewsListView, NewsDetailView

from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap, NoticeSitemap, NewsSitemap, ClubSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'notices': NoticeSitemap,
    'news': NewsSitemap,
    'clubs': ClubSitemap,
}
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Home
    path('', HomeView.as_view(), name='home'),
    
    # About
    path('about/', AboutView.as_view(), name='about'),
    path('about/<str:page>/', AboutView.as_view(), name='about_page'),
    
    # Legal & Sitemap
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-of-service/', TermsOfServiceView.as_view(), name='terms_of_service'),
    path('sitemap/', SitemapView.as_view(), name='sitemap'),
    
    # People
    path('teachers/', TeacherListView.as_view(), name='teachers'),
    path('administration/', AdministrationListView.as_view(), name='administration'),
    
    # Notices
    path('notices/', NoticeListView.as_view(), name='notice_list'),
    path('notices/<int:pk>/', NoticeDetailView.as_view(), name='notice_detail'),
    path('notices/increment-view/<int:pk>/', increment_notice_view, name='increment_notice_view'),
    
    # News
    path('news/', NewsListView.as_view(), name='news_list'),
    path('news/<slug:slug>/', NewsDetailView.as_view(), name='news_detail'),
    
    # Resources
    path('resources/', include('resources.urls')),
    
    # Clubs
    path('clubs/', include('clubs.urls')),

    # Contact
    path('contact/', include('contact.urls')),

    # SEO
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('summernote/', include('django_summernote.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Static files are served automatically in development from STATICFILES_DIRS
