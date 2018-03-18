from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView, ListView, DetailView

from ranking.decorators import player_login_required
from ranking.forms import LoginForm, SignupForm, ReportResultForm
from ranking.models import Match, Player, MatchParticipation
from ranking.support import set_session_player, get_session_player, clear_session_player




class AuthMixin(object):
    player = None
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = self.get_player()
        if player is not None:
            context['player'] = player
        return context

    @method_decorator(player_login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_player(self):
        if self.player is None:
            self.player = get_session_player(self.request.session)
        return self.player


class HomeView(AuthMixin, TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        context['latest_matches'] = Match.objects.all()[:5]
        context['ranking'] = Player.objects.order_by('-elo')
        return self.render_to_response(context)


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


class ReportResultView(AuthMixin, FormView):
    form_class = ReportResultForm
    template_name = 'report_result.html'

    success_url = reverse_lazy('home')

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        form = form_class(**self.get_form_kwargs())
        form.fields['opponent'].queryset = form.fields['opponent'].queryset.filter(~Q(pk = self.get_player().id))
        return form

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        match = Match.objects.create(
            date=timezone.now()
        )
        MatchParticipation.objects.create(
            match=match,
            player=self.get_player(),
            score=form.cleaned_data['player_score'],
            delta=0
        )

        MatchParticipation.objects.create(
            match=match,
            player=form.cleaned_data['opponent'],
            score=form.cleaned_data['opponent_score'],
            delta=0
        )

        match.update_elos()

        return HttpResponseRedirect(self.get_success_url())


class MatchesView(AuthMixin, ListView):
    model = Match
    template_name = 'matches.html'
    ordering = '-date'


class ProfileView(AuthMixin, DetailView):
    model = Player
    slug_field = 'name'
    context_object_name = 'profile'
    template_name = 'profile.html'

    #def get(self, *args, **kwargs):
    #    print(self.get_object().participations.all()[0].match)
    #    return super().get(*args, **kwargs)