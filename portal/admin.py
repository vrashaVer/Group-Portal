from django.contrib import admin
from portal.models import Announcement,AnnouncementPhoto,Comment,Like,Poll,Choice,Vote, Photo, PhotoPost

admin.site.register(Announcement)
admin.site.register(AnnouncementPhoto)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Poll)
admin.site.register(Choice)
admin.site.register(Vote)
admin.site.register(PhotoPost)
admin.site.register(Photo)


