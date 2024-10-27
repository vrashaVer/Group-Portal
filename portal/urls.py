from django.urls import path
from portal import views

urlpatterns = [
    path('', views.TestBaseView.as_view(), name='test'),

    ]