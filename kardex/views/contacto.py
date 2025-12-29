from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView


class ContactoView(LoginRequiredMixin, TemplateView):
    template_name = 'kardex/contacto/contacto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Contacto',
        })
        return context
