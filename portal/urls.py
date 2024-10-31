from django.urls import path
from portal import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.MainPageView.as_view(), name='main'),
    path('vote/<int:poll_id>/<int:choice_id>/', views.MainPageView.as_view(), name='vote'),
    path('like/announcement/<int:announcement_id>/', views.MainPageView.as_view(), name='like_announcement'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)