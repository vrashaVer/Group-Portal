from django.contrib import admin
from portal.models import Announcement,AnnouncementPhoto,Comment,Like,Poll,Choice,Vote, Photo, PhotoPost, Event, ForumCategory, ForumPost,Role,UserRole, ProfileType

admin.site.register(Announcement)
admin.site.register(AnnouncementPhoto)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Poll)
admin.site.register(Choice)
admin.site.register(Vote)
admin.site.register(PhotoPost)
admin.site.register(Photo)
admin.site.register(Event)
admin.site.register(ForumCategory)
admin.site.register(ForumPost)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

# Реєструємо модель UserRole в адміністративній панелі
@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')

@admin.register(ProfileType)
class ProfileTypeAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type')
