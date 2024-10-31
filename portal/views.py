from django.views.generic import ListView, View
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Announcement, Poll,Vote,Choice,Like
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect


class MainPageView(LoginRequiredMixin, ListView):
    template_name = 'portal/main_page.html'
    context_object_name = 'items'

    def get_queryset(self):
        announcements = Announcement.objects.prefetch_related('images').all()
        polls = Poll.objects.all()

        # Комбінуємо оголошення та голосування в один список і сортуємо
        combined = sorted(
            list(announcements) + list(polls),
            key=lambda x: x.created_at,
            reverse=True
        )
        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Отримання голосів користувача
        user_votes = Vote.objects.filter(user=user)
        user_voted_polls = {vote.poll_id for vote in user_votes}
        context['user_voted_polls'] = user_voted_polls

        # Оголошення та лайки для відображення
        announcement_type = ContentType.objects.get_for_model(Announcement)
        user_likes = Like.objects.filter(user=user, content_type=announcement_type)
        liked_announcements = {like.object_id for like in user_likes}
        context['liked_announcements'] = liked_announcements
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

                return JsonResponse({
                    "success": True,
                    "liked": liked,
                    "announcement_id": announcement.id
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
                    "results": results
                })
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    