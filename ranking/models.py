from django.contrib.auth.hashers import (
    check_password, make_password,
)
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q


class PlayerQuerySet(models.QuerySet):
    @staticmethod
    def _update_kwargs(kwargs):
        if 'name' in kwargs:
            kwargs['slug'] = slugify(kwargs['name'])
            del kwargs['name']

    def filter(self, *args, **kwargs):
        self._update_kwargs(kwargs)
        return super().filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        self._update_kwargs(kwargs)
        return super().get(*args, **kwargs)


class Player(models.Model):
    class Meta:
        default_manager_name = 'objects'
    objects = PlayerQuerySet.as_manager()
    elo = models.FloatField(default=1000)
    name = models.CharField(max_length=30, unique=True,
                            validators=[
                                RegexValidator(r'^[\w. @+-]+$', 'Der Name enthält ein ungültiges Zeichen', 'invalid')
                            ])
    pw_hash = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    _matches = None

    def set_password(self, plain_password):
        self.pw_hash = make_password(plain_password)

    def is_password(self, plain_password):
        return check_password(plain_password, self.pw_hash)

    def __str__(self):
        return self.name

    def update_elo(self, expected_performance, victory):
        self.elo = self.elo + 32 * (int(victory) - expected_performance)
        self.save()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def matches(self):
        print('GETTING MATCHES')
        if self._matches is None:
            print('HITTING DB')
            self._matches = Match.objects.filter(Q(defendant=self) | Q(challenger=self)).order_by('-date')
        return self._matches

    @property
    def matches_won(self):
        return list(filter(lambda m: m.is_winner(self), self.matches))

    @property
    def matches_lost(self):
        return list(filter(lambda m: not m.is_winner(self), self.matches))

    @property
    def winrate(self):
        try:
            return float(len(self.matches_won)) / len(self.matches) * 100
        except ZeroDivisionError:
            return 0

    @property
    def num_legs_won(self):
        return sum(map(lambda m:m.get_score_for_player(self), self.matches))

    @property
    def num_legs_lost(self):
        return sum(map(lambda m: m.get_score_for_opponent(self), self.matches))

    @property
    def legs_winrate(self):
        try:
            return float(self.num_legs_won) / self.total_legs * 100
        except ZeroDivisionError:
            return 0

    @property
    def total_legs(self):
        return self.num_legs_won + self.num_legs_lost



class Match(models.Model):
    class Meta:
        verbose_name_plural = 'matches'
    challenger = models.ForeignKey(Player, models.DO_NOTHING, related_name='challenger')
    defendant = models.ForeignKey(Player, models.DO_NOTHING, related_name='defendant')
    challenger_score = models.IntegerField(validators=[MinValueValidator(0)])
    defendant_score = models.IntegerField(validators=[MinValueValidator(0)])
    date = models.DateTimeField(default=timezone.now)
    challenger_delta = models.IntegerField()
    defendant_delta = models.IntegerField()

    @property
    def winner(self):
        if self.challenger_score > self.defendant_score:
            return self.challenger
        elif self.challenger_score < self.defendant_score:
            return self.defendant
        return None

    def get_score_for_player(self, player):
        if not self.has_player(player):
            return 0
        if self.challenger == player:
            return self.challenger_score
        if self.defendant == player:
            return self.defendant_score

    def get_score_for_opponent(self, player):
        if not self.has_player(player):
            return 0
        if self.challenger != player:
            return self.challenger_score
        if self.defendant != player:
            return self.defendant_score

    def is_winner(self, player):
        return self.winner == player

    def update_elos(self):
        exp_c = 1 / (1 + 10 ** ((self.defendant.elo - self.challenger.elo) / 400))
        exp_d = 1 - exp_c

        c_elo = self.challenger.elo
        d_elo = self.defendant.elo

        self.challenger.update_elo(exp_c, self.is_winner(self.challenger))
        self.defendant.update_elo(exp_d, self.is_winner(self.defendant))

        self.challenger_delta = self.challenger.elo - c_elo
        self.defendant_delta = self.defendant.elo - d_elo

    def has_player(self, player):
        return self.defendant == player or self.challenger == player

    def __str__(self):
        return 'Match on {}: {} {} : {} {}'.format(self.date, self.challenger, self.challenger_score, self.defendant_score, self.defendant)
