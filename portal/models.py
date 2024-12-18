from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey,GenericRelation
import random

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

    def delete(self, *args, **kwargs):
        # Перевірка, чи файл фізично існує, і його видалення
        if self.image and self.image.storage.exists(self.image.name):
            self.image.delete()
        super().delete(*args, **kwargs)
    
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

class Event(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    date = models.DateField()
    def __str__(self):
        return self.title
    

class ForumCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)   
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ForumPost(models.Model):
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name='forum_posts')  
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')  
    title = models.CharField(max_length=255)  
    text = models.TextField() 
    image = models.ImageField(upload_to='forum_posts/images/', blank=True, null=True)  
    video = models.FileField(upload_to='forum_posts/videos/', blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    
    comments = GenericRelation(Comment)

    def __str__(self):
        return self.title
    
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)  
    description = models.TextField(blank=True, null=True)  

    def __str__(self):
        return self.name
    
class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')  
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='users')  

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class ProfileType(models.Model):
    USER_TYPE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_type')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"


class ProfilePhoto(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True) 

    def __str__(self):
        return f"{self.user.username}'s Profile Photo"
    


def assign_default_color():
    colors = ["#95b6bd", "#93baaf", "#ffffb3", "#ffd4df", "#fcc386", "#a6e3c4", "#b7bac9", "#c4f8ff", "#9ed8ff", "#cfc1d9"]
    return random.choice(colors)

class ProfileColor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_color')
    color = models.CharField(max_length=7, default=assign_default_color)  

    def __str__(self):
        return f"{self.user.username}'s Profile Color"
    


class Subject(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        limit_choices_to={'profile_type__user_type': 'teacher'}, 
        related_name='subjects'
    )

    def __str__(self):
        return self.name

class Assignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=100)
    due_date = models.DateField()

    def __str__(self):
        return f"{self.title} - {self.subject.name}"

class Grade(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='grades')
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        limit_choices_to={'profile_type__user_type': 'student'}
    )
    grade = models.IntegerField()

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.assignment.title} - {self.student.username}: {self.grade}"