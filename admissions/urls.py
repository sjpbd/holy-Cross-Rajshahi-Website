# admissions/urls.py
from django.urls import path

from . import views

app_name = 'admissions'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('apply/', views.apply, name='apply'),
    path('apply/calendar/', views.calendar_partial, name='calendar'),
    path('continue/', views.resume_application, name='resume'),
    path('lookup/', views.lookup_application, name='lookup'),
    path('payment/<uuid:token>/', views.payment_page, name='payment'),
    path('payment/<uuid:token>/simulate/', views.simulate_payment, name='simulate_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/fail/', views.payment_fail, name='payment_fail'),
    path('payment/ipn/', views.payment_ipn, name='payment_ipn'),
    path('form/<uuid:token>/', views.success, name='success'),
    path('form/<uuid:token>/pdf/', views.pdf_download, name='pdf_download'),
]
