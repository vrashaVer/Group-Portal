from django.shortcuts import render
from django.views.generic import TemplateView

class TestBaseView(TemplateView):

    template_name = 'portal/testbase.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_sidebar'] = True  # Встановлюємо значення True для показу бокової панелі
        return context
