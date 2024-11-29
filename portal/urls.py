from django.urls import path
from portal import views
from django.contrib.auth.views import LogoutView
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
    path('add-poll/', views.CreatePollView.as_view(), name='add_poll'),
    path('delete_polls/<int:pk>/', views.PollDeleteView.as_view(), name='poll_delete'),
    path('delete_announcement/<int:pk>/', views.AnnouncementDeleteView.as_view(), name='announcement_delete'),
    path('announcement/<int:pk>/edit/', views.EditAnnouncementView.as_view(), name='edit_announcement'),
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('forum-topics-list', views.CategoryListView.as_view(), name='category_list'),
    path('forum/topics/<int:category_id>/',views.ForumPostListView.as_view(), name='forum_post_list'),
    path('forum-post/<int:pk>/', views.ForumPostDetailView.as_view(), name='forum_post_detail'),
    path('forum/post/<int:post_id>/add_comment/', views.AddCommentForumView.as_view(), name='add_comment'),
    path('forum/categories/create/', views.ForumCategoryCreateView.as_view(), name='create_category'),
    path('forum/posts/edit/<int:pk>/', views.ForumPostUpdateView.as_view(), name='edit_forum_post'),
    path('forum/posts/delete/<int:pk>/', views.ForumPostDeleteView.as_view(), name='delete_forum_post'),
    path('forum/categories/delete/<int:pk>/', views.ForumCategoryDeleteView.as_view(), name='delete_forum_category'),
    path('forum/categories/edit/<int:pk>/', views.ForumCategoryEditView.as_view(), name='edit_category'),
    path('forum/categories/<int:category_id>/add_post/', views.ForumPostCreateView.as_view(), name='add_forum_post'),
    path('login/', views.CustomLoginView.as_view(), name='login'), 
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('user/<int:pk>/', views.UserProfileView.as_view(), name='an_user_profile'),
    path('register-user/', views.UserRegistrationView.as_view(), name='register_user'),
    path('user-list/', views.UserDataListView.as_view(), name='users_data_list'),
    path('user-edit/<int:pk>/', views.UserEditView.as_view(), name='user_edit'),

    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)