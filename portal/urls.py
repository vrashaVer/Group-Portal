from django.urls import path
from portal import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.MainPageView.as_view(), name='main'),
    path('vote/<int:poll_id>/<int:choice_id>/', views.MainPageView.as_view(), name='vote'),
    path('like/announcement/<int:announcement_id>/', views.MainPageView.as_view(), name='like_announcement'),
    path('add_comment/', views.AddCommentView.as_view(), name='add_comment'),
    path('load_comments/', views.LoadCommentsView.as_view(), name='load_comments'),
    path('gallery/', views.GalleryView.as_view(), name='gallery'),
    path('create/', views.CreatePostWithPhotosView.as_view(), name='create_post_with_photos'),
    path('post/<int:pk>/edit/', views.PhotoPostEditView.as_view(), name='edit_post'),
    path('delete_post/<int:pk>/', views.PhotoPostDeleteView.as_view(), name='delete_post'),
    path('add-announcement/', views.AddAnnouncementView.as_view(), name='add_announcement'),
    path('events/', views.EventListView.as_view(), name='event_list'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)