from django.views.generic import ListView, View, CreateView, UpdateView, DetailView
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormMixin
from .models import Announcement, Poll,Vote,Choice,Like,Comment, PhotoPost, Photo, AnnouncementPhoto, Event, ForumCategory, ForumPost, Role, UserRole, ProfileType
from .models import ProfileColor, ProfilePhoto
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from .forms import CommentForm, PostForm, PhotoPostEditForm, AnnouncementForm,ProfilePhotoForm, ForumCategoryForm, UserRegistrationForm,AnnouncementPhotoEditForm,ChoiceFormSet, PollForm
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.db.models import Count
from django.db.models import Q
import re
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

class MainPageView(LoginRequiredMixin, ListView):
    template_name = 'portal/main_page.html'
    context_object_name = 'items'
    login_url = reverse_lazy('login')
    

    def get_queryset(self):
        announcements = Announcement.objects.prefetch_related('images').all()
        polls = Poll.objects.all()

        query = self.request.GET.get('search')
        if query:
            announcements = announcements.filter(Q(title__icontains=query) | Q(content__icontains=query))
            polls = polls.filter(question__icontains=query)
        # Комбінуємо оголошення та голосування в один список і сортуємо
        combined = sorted(
            list(announcements) + list(polls),
            key=lambda x: x.created_at,
            reverse=True
        )
        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')

        user = self.request.user

        like_counts = {}
        announcement_type = ContentType.objects.get_for_model(Announcement)
        for announcement in Announcement.objects.all():
            like_counts[announcement.id] = Like.objects.filter(
                content_type=announcement_type,
                object_id=announcement.id
            ).count()

        context['like_counts'] = like_counts

        # Отримання голосів користувача
        user_votes = Vote.objects.filter(user=user)
        user_voted_polls = {vote.poll_id for vote in user_votes}
        context['user_voted_polls'] = user_voted_polls

        # Оголошення та лайки для відображення
        announcement_type = ContentType.objects.get_for_model(Announcement)
        user_likes = Like.objects.filter(user=user, content_type=announcement_type)
        liked_announcements = {like.object_id for like in user_likes}
        context['liked_announcements'] = liked_announcements
        # Завантаження коментарів для кожного оголошення
        comments_by_announcement = {
            announcement.id: list(Comment.objects.filter(
                content_type=announcement_type,
                object_id=announcement.id
            ).order_by('created_at')) for announcement in Announcement.objects.all()
        }
        
        context['comments_by_announcement'] = comments_by_announcement
        context['comment_form'] = CommentForm()

        polls = Poll.objects.annotate(choice_count=Count('choices')).filter(choice_count__gte=2)
        context['polls'] = polls
        poll_results = {}
        for poll in polls:
            total_votes = Vote.objects.filter(poll=poll).count()
            choice_votes = {
                choice.choice_text: choice.votes.count() for choice in poll.choices.all()
            }
            poll_results[poll.id] = {
                "total_votes": total_votes,
                "choice_votes": choice_votes
            }

        context['poll_results'] = poll_results
        return context

    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            if 'announcement_id' in request.POST:
                # Логіка лайків
                announcement_id = request.POST.get('announcement_id')
                announcement = get_object_or_404(Announcement, id=announcement_id)
            
                # Отримати content_type для Announcement
                announcement_type = ContentType.objects.get_for_model(Announcement)

                # Логіка для лайків
                like, created = Like.objects.get_or_create(user=request.user, content_type=announcement_type, object_id=announcement.id)
                if not created:
                    like.delete()
                    liked = False
                else:
                    liked = True

                like_count = Like.objects.filter(content_type=announcement_type, object_id=announcement.id).count()

                return JsonResponse({
                    "success": True,
                    "liked": liked,
                    "announcement_id": announcement.id,
                    "like_count": like_count
                })
            elif 'poll_id' in request.POST and 'choice_id' in request.POST:
                poll_id = request.POST.get('poll_id')
                choice_id = request.POST.get('choice_id')

                if not poll_id or not choice_id:
                    return JsonResponse({'success': False, 'error': 'Invalid poll or choice ID.'}, status=400)

                poll = get_object_or_404(Poll, id=poll_id)
                choice = get_object_or_404(Choice, id=choice_id)

                # Перевірка голосу
                if Vote.objects.filter(user=request.user, poll=poll).exists():
                    return JsonResponse({'success': False, 'error': 'You have already voted.'}, status=400)

                Vote.objects.create(user=request.user, poll=poll, choice=choice)


                total_votes = Vote.objects.filter(poll=poll).count()

                # Отримання результатів для кожного вибору
                results = [
                    {
                        "choice_text": c.choice_text,
                        "votes_count": c.votes.count()
                    } for c in poll.choices.all()
                ]

                

                return JsonResponse({
                    "success": True,
                    "poll_id": poll.id,
                    "choice_id": choice.id,
                    "results": results,
                    "total_votes": total_votes
                    
                })
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    

class AddAnnouncementView(LoginRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'portal/add_announcement.html'
    success_url = 'main'  # Направляти після успішного додавання

    def form_valid(self, form):
        # Створення оголошення
        announcement = form.save(commit=False)
        announcement.creator = self.request.user

        # Перевірка на відео - чи є відеофайл або відео URL
        video_file = form.cleaned_data.get('video_file')
        video_url = form.cleaned_data.get('video_url')
        image = form.cleaned_data.get('image')

        # Перевірка на наявність одночасно фото та відео
        if (video_file or video_url) and image:
            form.add_error(None, 'You cannot add both an image and a video at the same time.')
            return self.form_invalid(form)
       

        # Якщо є відео URL, перевіряємо, чи є правильний ID відео
        if video_url:
            video_id = self.extract_youtube_video_id(video_url)
            if video_id:
                announcement.video_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                form.add_error('video_url', 'Invalid YouTube URL.')
                return self.form_invalid(form)

        if video_file:
            announcement.video_file = video_file

        if video_file and video_url:
            form.add_error(None, 'You cannot add both a video file and a video URL.')
            return self.form_invalid(form)

        # Зберігаємо оголошення
        announcement.save()

        # Якщо додано фото
        if 'image' in self.request.FILES:
            photo = AnnouncementPhoto(announcement=announcement, image=image)
            photo.save()

        return redirect(self.success_url)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {'form': form})

    def extract_youtube_video_id(self, url):
        youtube_regex = r"(https?://)?(www\.)?(youtube|youtu|vimeo)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^?&/]+)"
        match = re.match(youtube_regex, url)
        if match:
            return match.group(6)  # ID відео
        return None
    



class AddCommentView(View):
    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            announcement_id = request.POST.get('announcement_id')
            text = request.POST.get('text')

            try:
                # Отримати оголошення за ID
                announcement = Announcement.objects.get(id=announcement_id)
                
                # Створення коментаря
                comment = Comment.objects.create(
                    user=request.user,
                    content_type=ContentType.objects.get_for_model(Announcement),
                    object_id=announcement_id,
                    text=text,
                    created_at=timezone.now()
                )
                
                # Повернення даних нового коментаря
                return JsonResponse({
                    'success': True,
                    'user': request.user.username,
                    'text': comment.text,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
                })
            except Announcement.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Announcement not found.'}, status=404)

        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    

class LoadCommentsView(View):
    def get(self, request, *args, **kwargs):
        announcement_id = request.GET.get('announcement_id')
        
        try:
            # Отримання оголошення та його коментарів
            announcement = Announcement.objects.get(id=announcement_id)
            comments = Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Announcement),
                object_id=announcement_id
            ).order_by('created_at')

            # Формування даних коментарів у форматі JSON
            comments_data = [
                {
                    'user': comment.user.username,
                    'text': comment.text,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
                }
                for comment in comments
            ]

            return JsonResponse({'success': True, 'comments': comments_data})
        
        except Announcement.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Announcement not found.'}, status=404)
        
class GalleryView(View):
    template_name = 'portal/gallery_list.html'

    def get(self, request):
        posts = PhotoPost.objects.all().order_by('-created_at')  # Сортуємо пости від нових до старих
        return render(request, self.template_name, {'posts': posts})
    
class CreatePollView(View):
    template_name = 'portal/create_poll.html'

    def get(self, request, *args, **kwargs):
        poll_form = PollForm()
        choice_formset = ChoiceFormSet(queryset=Choice.objects.none())
        return render(request, self.template_name, {'poll_form': poll_form, 'choice_formset': choice_formset})

    def post(self, request, *args, **kwargs):
        poll_form = PollForm(request.POST)
        choice_formset = ChoiceFormSet(request.POST)

        if poll_form.is_valid() and choice_formset.is_valid():
            poll = poll_form.save()
            choices = choice_formset.save(commit=False)
            for choice in choices:
                choice.poll = poll
                choice.save()
            return redirect('main')  

        return render(request, self.template_name, {'poll_form': poll_form, 'choice_formset': choice_formset}) 




class CreatePostWithPhotosView(View):
    def get(self, request):
        post_form = PostForm()
        return render(request, 'portal/create_photopost.html', {'post_form': post_form})

    def post(self, request):
        post_form = PostForm(request.POST)
        photos = request.FILES.getlist('photos')  # Отримання файлів фото з форми
        
        # Перевіряємо, що хоча б одне фото додано
        if post_form.is_valid() and photos:
            post = post_form.save(commit=False)
            post.author = request.user  # Додаємо автора
            post.save()
            
            # Збереження фотографій, максимум 10
            for photo in photos[:10]:
                Photo.objects.create(post=post, image=photo)
            
            return redirect('gallery')
        
        # Додаємо повідомлення про помилку, якщо фотографії відсутні
        if not photos:
            post_form.add_error(None, 'Please add at least one photo.')

        return render(request, 'portal/create_post_with_photos.html', {'post_form': post_form})
    
class PhotoPostEditView(UpdateView):
    model = PhotoPost
    form_class = PhotoPostEditForm
    template_name = 'portal/edit_post.html'

    # Метод для визначення success_url після успішного збереження
    def get_success_url(self):
        return reverse_lazy('gallery')  # Перенаправлення на галерею після успішного редагування

    # Перевірка прав доступу перед редагуванням
    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return HttpResponseForbidden("Ви не можете редагувати цей пост.")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Спочатку зберігаємо сам пост
        post = form.save(commit=False)

        # Якщо поле 'edited' False, змінюємо на True
        if not post.edited:
            post.edited = True

        post.save()

        return super().form_valid(form)
    
class PhotoPostDeleteView(View):
    def post(self, request, pk):
        # Отримуємо пост
        post = get_object_or_404(PhotoPost, pk=pk)
        # Видаляємо пост
        post.delete()

        # Перенаправляємо на сторінку галереї після видалення
        return HttpResponseRedirect(reverse_lazy('gallery'))
class PollDeleteView(View):
    def post(self, request, pk):
        # Отримуємо пост
        poll = get_object_or_404(Poll, pk=pk)

        # Видаляємо пост
        poll.delete()

        # Перенаправляємо на сторінку галереї після видалення
        return HttpResponseRedirect(reverse_lazy('main'))
    
class AnnouncementDeleteView(View):
    def post(self, request, pk):
        # Отримуємо пост
        announcement = get_object_or_404(Announcement, pk=pk)

        # Видаляємо пост
        announcement.delete()

        # Перенаправляємо на сторінку галереї після видалення
        return HttpResponseRedirect(reverse_lazy('main'))
    

class EditAnnouncementView(LoginRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'portal/edit_announcement.html'
    context_object_name = 'announcement'

    def get_queryset(self):
        return Announcement.objects.filter(creator=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context['photo_form'] = AnnouncementPhotoEditForm(self.request.POST, self.request.FILES)
        else:
            context['photo_form'] = AnnouncementPhotoEditForm()
        context['photos'] = self.object.images.all()

        form = self.get_form()  # Отримуємо форму
        if form.errors:
            context['video_url'] = None  # Якщо є помилки, очищаємо video_url
        else:
            context['video_url'] = self.object.video_url
           

        return context

    def form_valid(self, form):
        announcement = form.save(commit=False)

        # Видалення фото, якщо вказано
        delete_photo_ids = self.request.POST.get('delete_photo_ids', '')
        if delete_photo_ids:  # Перевіряємо, чи є передані ID
            photo_ids = [int(photo_id) for photo_id in delete_photo_ids.split(',') if photo_id.isdigit()]
            photos_to_delete = AnnouncementPhoto.objects.filter(id__in=photo_ids, announcement=announcement)
            for photo in photos_to_delete:
                photo.delete()

        # Перевірка на видалення відео
        if 'delete_video' in self.request.POST:
            announcement.video_file = None
            announcement.video_url = None

        # Перевірка обмежень на медіа
        new_video_file = form.cleaned_data.get('video_file')
        new_video_url = form.cleaned_data.get('video_url')
        new_image = self.request.FILES.get('image')

        if (announcement.images.exists() or new_image) and (new_video_file or new_video_url):
            form.add_error(None, 'You cannot have both photos and a video (file or URL) at the same time.')
            form.cleaned_data['video_file'] = None
            form.cleaned_data['video_url'] = ''
            return self.form_invalid(form)
    
        if new_video_file and new_video_url:
            form.add_error(None, 'You cannot provide both a video file and a video URL. Please choose one.')
            form.cleaned_data['video_file'] = None
            form.cleaned_data['video_url'] = ''
            return self.form_invalid(form)

        announcement.edited = True
        announcement.save()

        # Додавання нового фото, якщо є
        if new_image:
            photo_form = AnnouncementPhotoEditForm(self.request.POST, self.request.FILES)
            if photo_form.is_valid():
                photo = photo_form.save(commit=False)
                photo.announcement = announcement
                photo.save()

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # Повертаємо форму з помилками без рекурсії
        context = self.get_context_data(form=form)
        context['photo_form'] = AnnouncementPhotoEditForm(self.request.POST, self.request.FILES)
        context['video_url'] = ''  # Очищаємо URL відео при помилці
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse_lazy('main')  # Перенаправлення після редагування
    
class DeleteAnnouncementPhotoView(LoginRequiredMixin, View):
    def delete(self, request, *args, **kwargs):
        photo_id = kwargs.get('photo_id')
        photo = get_object_or_404(AnnouncementPhoto, id=photo_id)

        # Перевірка, чи користувач має доступ до видалення
        if photo.announcement.creator != request.user:
            return JsonResponse({'error': 'Permission denied.'}, status=403)

        # Видалення фото
        photo.delete()
        return JsonResponse({'message': 'Photo deleted successfully.'}, status=200)
    
class CategoryListView(ListView):
    model = ForumCategory
    template_name = 'portal/forum/category_list.html'
    context_object_name = 'categories'


class ForumPostListView(ListView):
    model = ForumPost
    template_name = 'portal/forum/forum_post_list.html'
    context_object_name = 'forum_posts'

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        if not ForumCategory.objects.filter(id=category_id).exists():
            return ForumPost.objects.none()  # Якщо категорія не існує
        return ForumPost.objects.filter(category_id=category_id).order_by('-created_at')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_id'] = self.kwargs['category_id']  # Додаємо category_id у контекст
        return context

class ForumPostDetailView(FormMixin, DetailView):
    model = ForumPost
    template_name = 'portal/forum/forum_post_detail.html'
    context_object_name = 'forum_posts'
    form_class = CommentForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['comments'] = self.object.comments.all().order_by('-created_at')
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.content_object = self.object  # Прив’язуємо коментар до поста
            comment.save()
            return redirect('forum_post_detail', pk=self.object.pk)
        else:
            return self.form_invalid(form)


class AddCommentForumView(LoginRequiredMixin, View):
    def post(self, request, post_id):
        text = request.POST.get('text')
        forum_post = ForumPost.objects.get(id=post_id)

        # Додаємо коментар, прив’язаний до ForumPost через GenericRelation
        comment = Comment.objects.create(
            user=request.user,
            content_type=ContentType.objects.get_for_model(ForumPost),
            object_id=forum_post.id,
            text=text)

        return JsonResponse({
            'success': True,
            'username': comment.user.username,
            'created_at': comment.created_at.strftime("%d %b %Y %H:%M"),
            'text': comment.text,
        })
    
class ForumCategoryCreateView(CreateView):
    model = ForumCategory
    template_name = 'portal/forum/create_category.html'  # Вкажіть ваш шаблон
    fields = ['name']  # Поля, які будуть у формі
    success_url = reverse_lazy('category_list')  # URL, куди перенаправити після створення

    def form_valid(self, form):
        # Додаткові дії перед збереженням, якщо необхідно
        return super().form_valid(form)
    

class ForumPostDeleteView(View):
    def post(self, request, pk):
        # Отримуємо пост
        post = get_object_or_404(ForumPost, pk=pk)

        # Перевіряємо, чи автор поста є поточним користувачем
        if post.author != request.user:
            return HttpResponseForbidden("Ви не можете видалити цей пост.")

        # Зберігаємо ID категорії для перенаправлення
        category_id = post.category_id

        # Видаляємо пост
        post.delete()

        # Перенаправляємо на список постів категорії
        return HttpResponseRedirect(reverse('forum_post_list', kwargs={'category_id': category_id}))
    
class ForumPostUpdateView(LoginRequiredMixin, UpdateView):
    model = ForumPost
    template_name = 'portal/forum/edit_forum_post.html'
    fields = ['title', 'text', 'image', 'video']

    def get_queryset(self):
        # Обмежуємо редагування постів лише автору
        return super().get_queryset().filter(author=self.request.user)

    def get_success_url(self):
        # Повертає URL для детальної сторінки поста після редагування
        return reverse_lazy('forum_post_detail', kwargs={'pk': self.object.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаємо URL сторінки деталей поста
        context['post_detail_url'] = reverse_lazy('forum_post_detail', kwargs={'pk': self.object.pk})
        return context


class ForumCategoryDeleteView(View):
    def post(self, request, pk):
        # Отримуємо пост
        category = get_object_or_404(ForumCategory, pk=pk)


        # Видаляємо пост
        category.delete()

        # Перенаправляємо на сторінку галереї після видалення
        return HttpResponseRedirect(reverse_lazy('category_list'))
    
class ForumCategoryEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        category = get_object_or_404(ForumCategory, pk=pk)

        # Перевірка на дозволи, можна редагувати тільки адміністратору
        if not request.user.is_staff:
            return HttpResponseForbidden("Ви не можете редагувати цю категорію.")

        form = ForumCategoryForm(instance=category)
        return render(request, 'portal/forum/category_edit.html', {'form': form, 'category': category})

    def post(self, request, pk):
        category = get_object_or_404(ForumCategory, pk=pk)

        # Перевірка на дозволи
        if not request.user.is_staff:
            return HttpResponseForbidden("Ви не можете редагувати цю категорію.")

        form = ForumCategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()  # Зберігаємо зміни
            return redirect('category_list')  # Після успішного редагування перенаправляємо на список категорій
        return render(request, 'portal/forum/category_edit.html', {'form': form, 'category': category})
    
class ForumPostCreateView(LoginRequiredMixin, CreateView):
    model = ForumPost
    template_name = 'portal/forum/add_forum_post.html'
    fields = ['title', 'text', 'image', 'video']

    def form_valid(self, form):
        # Отримуємо категорію за ID
        category = get_object_or_404(ForumCategory, pk=self.kwargs['category_id'])
        form.instance.category = category  # Прив’язуємо пост до категорії
        form.instance.author = self.request.user  # Додаємо автора
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(ForumCategory, pk=self.kwargs['category_id'])
        return context

    def get_success_url(self):
        # Повертаємо на список постів у категорії після створення
        return reverse_lazy('forum_post_list', kwargs={'category_id': self.kwargs['category_id']})


# class RegisterView(CreateView):
#     form_class = CustomUserCreationForm
#     template_name = 'portal/registration/register.html'
#     success_url = reverse_lazy('home')  # Замість 'home' вставте вашу цільову URL-адресу

#     def form_valid(self, form):
#         user = form.save()
#         login(self.request, user)  # Автоматично увійти після реєстрації
#         return redirect(self.success_url)
    
class CustomLoginView(LoginView):
    template_name = 'portal/registration/login.html'  # Вкажіть свій шаблон для входу
    success_url = reverse_lazy('main')  # URL для перенаправлення після успішного входу


class UserListView(LoginRequiredMixin,ListView):

    model = User
    template_name = 'portal/users/user_list.html'
    context_object_name = 'users'

    def test_func(self):
        # Перевірка, чи є користувач адміністратором
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Отримуємо власника, адміністраторів та модераторів
        owner = User.objects.filter(is_superuser=True).first()  # Власник сайту
        admin_role = Role.objects.get(name='Admin')
        moderator_role = Role.objects.get(name='Moderator')

        # Групуємо користувачів за ролями
        admins = User.objects.filter(roles__role=admin_role)
        moderators = User.objects.filter(roles__role=moderator_role)

        # Виключаємо власника, адміністраторів і модераторів зі списку звичайних користувачів
        users = User.objects.exclude(id__in=admins).exclude(id__in=moderators)
        if owner:
            users = users.exclude(id=owner.id)

        context['owner'] = owner
        context['admins'] = admins
        context['moderators'] = moderators
        context['users'] = users
        context['roles'] = [admin_role, moderator_role]
        return context

    def post(self, request, *args, **kwargs):
        # Перевірка, чи користувач має право на зміну ролей
        if not (request.user.is_superuser or 
                UserRole.objects.filter(user=request.user, role__name='Admin').exists()):
            return HttpResponseForbidden("У вас немає прав для виконання цієї дії.")

        user_id = request.POST.get('user_id')
        action = request.POST.get('action')  # 'add_role' або 'remove_role'
        role_name = request.POST.get('role')  # Назва ролі, яку додаємо або забираємо

        # Перевірка, чи існує користувач
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponseForbidden("Користувач не знайдений.")

        # Власника не можна змінювати
        if user.is_superuser:
            return HttpResponseForbidden("Ви не можете змінювати права власника.")

        # Перевірка, чи існує роль
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            return HttpResponseForbidden(f"Роль '{role_name}' не знайдена в системі.")

        # Обмеження дій залежно від ролі
        if action == 'add_role':
            # Власник може додати будь-яку роль
            # Адміністратор може додати тільки роль модератора
            if role.name == 'Admin' and not request.user.is_superuser:
                return HttpResponseForbidden("Тільки власник може призначати адміністраторів.")
            
            if UserRole.objects.filter(user=user, role=role).exists():
                return HttpResponseForbidden("Користувач вже має цю роль.")
            UserRole.objects.create(user=user, role=role)

        elif action == 'remove_role':
        # Видалення ролі (тут `role_name` може бути пустим)
            try:
                user_role = UserRole.objects.filter(user=user, role__name=role_name).first()  # Отримуємо будь-яку роль
                if user_role:
                    role = user_role.role
                    # Тільки власник може знімати роль адміністратора
                    if role.name == 'Admin' and not request.user.is_superuser:
                        return HttpResponseForbidden("Тільки власник може знімати адміністратора.")
                    user_role.delete()
                else:
                    return HttpResponseForbidden("У користувача немає ролей для видалення.")
            except Exception as e:
                return HttpResponseForbidden(f"Помилка: {str(e)}")
            
        return redirect('user_list')
    

class UserProfileView(LoginRequiredMixin, View):
    template_name = 'portal/users/user_profile.html'

    def get(self, request):
        
        profile_photo = ProfilePhoto.objects.filter(user=request.user).first()
        profile_color = ProfileColor.objects.filter(user=request.user).first()
        available_colors = ["#95b6bd", "#93baaf", "#ffffb3", "#ffd4df", "#fcc386", 
                        "#a6e3c4", "#b7bac9", "#c4f8ff", "#9ed8ff", "#cfc1d9"]

        context = {
            'profile_photo': profile_photo,
            'profile_color': profile_color.color if profile_color else '#cccccc',
            'user': request.user,
            'form': ProfilePhotoForm(),
            'available_colors': available_colors,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if 'photo' in request.FILES:
            profile_photo, created = ProfilePhoto.objects.get_or_create(user=request.user)
            form = ProfilePhotoForm(request.POST, request.FILES, instance=profile_photo)

            if form.is_valid():
                form.save()
                # Повернення URL завантаженого фото
                return JsonResponse({
                    'success': True,
                    'message': 'Photo updated successfully',
                    'new_photo_url': profile_photo.photo.url
                })

            return JsonResponse({'success': False, 'message': 'Error updating photo'})
        elif 'first_name' in request.POST or 'last_name' in request.POST or 'email' in request.POST:
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.save()

            return JsonResponse({
                'success': True,
                'message': 'User information updated successfully'
            }, status=200)
        elif request.is_ajax() and request.method == "POST":
            try:
                data = json.loads(request.body.decode('utf-8'))
                user = request.user

                # Оновлення даних користувача
                user.first_name = request.POST.get('first_name') or user.first_name
                user.last_name = request.POST.get('last_name') or user.last_name
                user.email = request.POST.get('email') or user.email

                user.save()

                return JsonResponse({"success": True, "message": "User information updated successfully"})

            except Exception as e:
                return JsonResponse({"success": False, "message": str(e)}, status=400)

        # Інший випадок
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    @method_decorator(csrf_exempt)
    def delete(self, request):
        # Видалення фотографії
        profile_photo = ProfilePhoto.objects.filter(user=request.user).first()
        if profile_photo and profile_photo.photo:
            profile_photo.photo.delete()
            profile_photo.delete()
            return JsonResponse({'success': True, 'message': 'Photo deleted successfully'})
        return JsonResponse({'success': False, 'message': 'No photo to delete'})

    def put(self, request):
        data = json.loads(request.body)
        new_color = data.get('color')
        if new_color:
            # Видалення існуючого фото
            profile_photo = ProfilePhoto.objects.filter(user=request.user).first()
            if profile_photo and profile_photo.photo:
                profile_photo.photo.delete()  # Видаляє файл з файлової системи
                profile_photo.delete()  # Видаляє запис з бази даних

            # Оновлення кольору профілю
            profile_color, created = ProfileColor.objects.get_or_create(user=request.user)
            profile_color.color = new_color
            profile_color.save()

            return JsonResponse({'success': True, 'message': 'Color updated successfully and photo removed.'})
        return JsonResponse({'success': False, 'message': 'Color update failed.'})





class AnUserProfileView(DetailView):
    model = User
    template_name = 'portal/users/an_user_profile.html'
    context_object_name = 'user_profile'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Отримуємо тип профілю (якщо використовується модель `ProfileType`)
        context['profile_type'] = ProfileType.objects.filter(user=self.object).first()
        return context

    
class UserRegistrationView(View):
    template_name = 'portal/registration/register_user.html'

    def get(self, request):
        # Перевірка, чи користувач має право доступу
        if not self._has_permission(request.user):
            return HttpResponseForbidden("Ви не маєте доступу до цієї сторінки.")
        
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if not self._has_permission(request.user):
            return HttpResponseForbidden("Ви не маєте доступу до цієї сторінки.")
        
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            try:
                validate_password(password)
            except ValidationError as e:
                # Якщо пароль не відповідає правилам, повертаємо форму з помилками
                return render(request, self.template_name, {
                    'form': form,
                    'error_messages': e.messages,
                })

            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Додати роль користувачу
            role = form.cleaned_data.get('role')
            if role:
                UserRole.objects.create(user=user, role=role)

            # Додати тип профілю
            user_type = form.cleaned_data['user_type']
            ProfileType.objects.create(user=user, user_type=user_type)

            ProfileColor.objects.create(user=user)

            return redirect('user_list')  # Повернення до списку користувачів

        return render(request, self.template_name, {'form': form})

    def _has_permission(self, user):
        # Доступ мають тільки власник або адміністратори
        return (
            user.is_superuser or
            UserRole.objects.filter(user=user, role__name="Admin").exists()
        )
        
class UserDataListView(View):
    template_name = 'portal/users/user_data_list.html'

    def get(self, request):
        # Перевірка прав доступу
        if not self._has_permission(request.user):
            return HttpResponseForbidden("Ви не маєте доступу до цієї сторінки.")
        
        users = User.objects.all()
        return render(request, self.template_name, {'users': users})

    def _has_permission(self, user):
        # Тільки власник або адміністратори мають доступ
        return (
            user.is_superuser or 
            UserRole.objects.filter(user=user, role__name="Admin").exists()
        )


class UserEditView(View):
    template_name = 'portal/users/user_edit.html'

    def get(self, request, pk):
        # Перевірка прав доступу
        if not self._has_permission(request.user):
            return HttpResponseForbidden("Ви не маєте доступу до цієї сторінки.")
        
        user = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {'user': user})

    def post(self, request, pk):
        if not self._has_permission(request.user):
            return HttpResponseForbidden("Ви не маєте доступу до цієї сторінки.")
        
        user = get_object_or_404(User, pk=pk)
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        user.username = username
        user.email = email
        if password:
            try:
                # Перевірка пароля за правилами Django
                validate_password(password, user=user)
                user.set_password(password)
            except ValidationError as e:
                # Повернення помилки, якщо пароль не відповідає правилам
                return render(request, self.template_name, {
                    'user': user,
                    'error_messages': e.messages,
                })

        return redirect('user_list')

    def _has_permission(self, user):
        return (
            user.is_superuser or 
            UserRole.objects.filter(user=user, role__name="Admin").exists()
        )
    
class EventListView(ListView):
    model = Event
    template_name = 'portal/events_page.html'
    context_object_name = 'events'

    def get_queryset(self):
        search_query = self.request.GET.get('search', '').lower()
        if search_query:
            words = search_query.split()
            query = Q()
            for word in words:
                query |= Q(title__icontains=word) | Q(content__icontains=word)
            return Event.objects.filter(query).distinct()
        return Event.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context