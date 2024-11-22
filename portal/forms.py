from django import forms
from .models import Comment,PhotoPost, Announcement, AnnouncementPhoto, ForumPost, ForumCategory

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Write your comment here...', 'rows': 3})
        }



class PostForm(forms.ModelForm):
    class Meta:
        model = PhotoPost
        fields = ['title', 'content']

class PhotoPostEditForm(forms.ModelForm):
    class Meta:
        model = PhotoPost
        fields = ['title', 'content'] 

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'video_file', 'video_url']

    # Додаткові перевірки для відео та фото
    def clean(self):
        cleaned_data = super().clean()
        video_file = cleaned_data.get('video_file')
        video_url = cleaned_data.get('video_url')
        # Фото додається окремо
        photo = cleaned_data.get('image')

        # Перевірка, чи не додано і фото, і відео одночасно
        if video_file and video_url:
            raise forms.ValidationError('You cannot provide both a video file and a video URL. Please provide one or the other.')
        
        # Перевірка, чи не додано фото і відео одночасно
        if video_file and photo:
            raise forms.ValidationError('You cannot upload both a video and a photo at the same time.')

        if video_url and photo:
            raise forms.ValidationError('You cannot provide both a video URL and a photo at the same time.')

        return cleaned_data
    
class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ['title', 'text', 'image', 'video', 'category']

class ForumCategoryForm(forms.ModelForm):
    class Meta:
        model = ForumCategory
        fields = ['name']
