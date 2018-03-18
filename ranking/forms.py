import logging

from django.forms import (
    PasswordInput, NumberInput,
    CharField, Form, ValidationError, ModelForm
)
from django.utils.translation import ugettext as _
from django_select2.forms import Select2Widget

from ranking.models import Player, Match

logger = logging.getLogger(__name__)


class SignupForm(ModelForm):
    class Meta:
        model = Player
        fields = ['name']

    password1 = CharField(
        label='Passwort',
        widget=PasswordInput(),
    )

    password2 = CharField(
        label='Passwort wiederholen',
        widget=PasswordInput(),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['password1'] != cleaned_data['password2']:
            raise ValidationError('Die Passwörter sind nicht identisch.')
        return self.cleaned_data


class LoginForm(Form):

    username = CharField(
        label='Name',
    )

    password = CharField(
        widget=PasswordInput(),
        label='Passwort',
    )

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean(self):

        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username is None or password is None:
            # basic field validation will fail anyway: no need to hit the DB
            return

        error_message = 'Ungültiger Name oder ungültiges Passwort'
        try:
            player = Player.objects.get(
               name=username
            )
        except Player.DoesNotExist:
            raise ValidationError(error_message)

        if player.is_password(password):
            logger.info('LOGIN: successful for player name=%s', player.name)
            self.player = player
        else:
            logger.info('LOGIN: failed for player name=%s', player.name)
            raise ValidationError(error_message)


class ReportResultForm(ModelForm):
    class Meta:
        model = Match
        fields = ['defendant', 'defendant_score', 'challenger_score']
        widgets = {
            'defendant': Select2Widget,
            'defendant_score': NumberInput(attrs={'style': 'width:4ch'}),
            'challenger_score': NumberInput(attrs={'style': 'width:4ch'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['defendant_score'] == cleaned_data['challenger_score']:
            raise ValidationError('Unentschieden ist nicht möglich')
        return cleaned_data