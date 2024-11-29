from django.views.generic import ListView, View, CreateView, UpdateView
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Announcement, Poll,Vote,Choice,Like,Comment, PhotoPost, Photo, AnnouncementPhoto
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from .forms import CommentForm, PostForm, PhotoPostEditForm, AnnouncementForm, PollForm, ChoiceFormSet, AnnouncementPhotoForm, AnnouncementPhotoEditForm
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse_lazy
from django.db.models import Count
from django.db.models import Q
import re

class MainPageView(LoginRequiredMixin, ListView):
    template_name = 'portal/main_page.html'
    context_object_name = 'items'

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
        if 'delete_photo_id' in self.request.POST:
            photo_id = self.request.POST.get('delete_photo_id')
            AnnouncementPhoto.objects.filter(id=photo_id, announcement=announcement).delete()

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
