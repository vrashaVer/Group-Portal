from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class Announcement(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    video_file = models.FileField(upload_to='announcement_video/', blank=True,null=True)
    video_url = models.URLField(blank=True,null=True)
    edited = models.BooleanField(default=False)

    def __str__(self):
        return self.title
   
class AnnouncementPhoto(models.Model):
    announcement = models.ForeignKey(Announcement,on_delete=models.CASCADE,related_name='images')
    image = models.ImageField(upload_to='post_images/')
    def __str__(self):
        return f"Image for {self.announcement.title}"
    
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.text}'

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')        

class Poll(models.Model):
    question = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)

    def __str__(self):
        return self.question
    
class Choice(models.Model):
    poll = models.ForeignKey(Poll, related_name="choices", on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=100)
    
    def __str__(self):
        return self.choice_text
    
class Vote(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll,on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice,on_delete=models.CASCADE,related_name='votes')
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user','poll')


class PhotoPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Photo(models.Model):
    post = models.ForeignKey(PhotoPost, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='gallery/photos/')

    def __str__(self):
        return f"Photo for {self.post.title}"



