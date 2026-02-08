from django.contrib import sitemaps
from django.urls import reverse
from notices.models import Notice
from news.models import NewsItem
from clubs.models import Club

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return [
            'home', 'about', 'teachers', 'administration', 
            'notice_list', 'news_list', 'club_list', 'contact'
        ]

    def location(self, item):
        return reverse(item)

class NoticeSitemap(sitemaps.Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Notice.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.created_at

class NewsSitemap(sitemaps.Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return NewsItem.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.published_at

class ClubSitemap(sitemaps.Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Club.objects.filter(is_active=True)
