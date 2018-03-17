from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView

from ranking.decorators import player_login_required
from ranking.forms import LoginForm, SignupForm, ReportResultForm
from ranking.support import set_session_player, get_session_player, clear_session_player
from ranking.models import Match, Player
from django.db.models import Q


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        print(context)
        context['player'] = get_session_player(request.session)
        context['latest_matches'] = Match.objects.order_by('-date')[:5]
        context['ranking'] = Player.objects.order_by('-elo')
        print(context['latest_matches'])
        return self.render_to_response(context)

    @method_decorator(player_login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class LoginView(FormView):
    form_class = LoginForm
    template_name = 'login.html'

    def get_success_url(self):
        return self.request.GET.get('next', reverse_lazy('home'))

    def form_valid(self, form):
        set_session_player(self.request.session, form.player)
        return HttpResponseRedirect(self.get_success_url())


def logout(request):
    clear_session_player(request.session)
    return HttpResponseRedirect(reverse_lazy('home'))


class SignupView(FormView):
    form_class = SignupForm
    template_name = 'signup.html'

    success_url = reverse_lazy('home')

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        player = form.save(commit=False)
        player.set_password(form.cleaned_data['password1'])
        player.save()
        set_session_player(self.request.session, player)
        return HttpResponseRedirect(self.get_success_url())


class ReportResultView(FormView):
    form_class = ReportResultForm
    template_name = 'report_result.html'

    success_url = reverse_lazy('home')

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        form = form_class(**self.get_form_kwargs())
        form.fields['defendant'].queryset = form.fields['defendant'].queryset.filter(~Q(pk = get_session_player(self.request.session).id))
        return form

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        match = form.save(commit=False)
        match.challenger = get_session_player(self.request.session)

        match.update_elos()
        match.save()

        return HttpResponseRedirect(self.get_success_url())

    @method_decorator(player_login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
