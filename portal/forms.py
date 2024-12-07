from django import forms
from .models import Comment,PhotoPost, Announcement, AnnouncementPhoto, ForumPost, ForumCategory, Role, ProfileType, UserRole, Poll, Choice, ProfilePhoto, Assignment, Grade, Subject
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

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

class PollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['question']

ChoiceFormSet = inlineformset_factory(
    Poll, Choice, fields=['choice_text'], extra=0, min_num=2, max_num=10, validate_min=True, validate_max=True
)


class AnnouncementPhotoEditForm(forms.ModelForm):
    class Meta:
        model = AnnouncementPhoto
        fields = ['image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False
    
class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ['title', 'text', 'image', 'video', 'category']

class ForumCategoryForm(forms.ModelForm):
    class Meta:
        model = ForumCategory
        fields = ['name']

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Підтвердити пароль")
    role = forms.ModelChoiceField(
        queryset=Role.objects.exclude(name='Owner'),  # виключаємо роль 'Owner'
        label="Роль",
        required=False
    )
    user_type = forms.ChoiceField(choices=ProfileType.USER_TYPE_CHOICES, label="Тип користувача", required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            self.add_error('confirm_password', "Паролі не співпадають.")
        return cleaned_data
    def save(self, commit=True):
        user = super().save(commit=False)

        # Установка пароля
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

            # Призначення ролі, якщо вибрана
            role = self.cleaned_data.get('role')
            if role:
                UserRole.objects.create(user=user, role=role)

        return user
    

class AnnouncementPhotoForm(forms.ModelForm):
    class Meta:
        model = AnnouncementPhoto
        fields = ['image']


class ProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = ProfilePhoto
        fields = ['photo']

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['grade']


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'teacher'] 

class UserEditForm(forms.ModelForm):
    password = forms.CharField(
        label="Новий пароль",
        widget=forms.PasswordInput(),
        required=False,
        help_text="Пароль має відповідати стандартам безпеки Django."
    )

    # Додаємо поле для типу користувача (student/teacher)
    user_type = forms.ChoiceField(
        choices=ProfileType.USER_TYPE_CHOICES,
        label="Тип користувача",
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']  # Додаємо first_name та last_name

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.exclude(id=self.instance.id).filter(username=username).exists():
            raise forms.ValidationError("Цей нікнейм вже використовується.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            from django.contrib.auth.password_validation import validate_password
            try:
                validate_password(password, user=self.instance)
            except forms.ValidationError as e:
                raise forms.ValidationError(f"Пароль не відповідає стандартам: {', '.join(e.messages)}")
        return password
    

