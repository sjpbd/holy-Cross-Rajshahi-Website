from django.urls import path
from .views import ClubListView, ClubDetailView

urlpatterns = [
    path('', ClubListView.as_view(), name='club_list'),
    path('<slug:slug>/', ClubDetailView.as_view(), name='club_detail'),
]
