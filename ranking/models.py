from django.contrib.auth.hashers import (
    check_password, make_password,
)
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.text import slugify
from collections import defaultdict


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


class FullMatchManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by('-date').prefetch_related(
            Prefetch('participations', queryset=MatchParticipation.objects.select_related('player')))


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
    _matches = []
    _participations = []
    _num_legs_won = None
    _num_legs_lost = None
    _total_legs = None
    _bogey = None
    _favorite = None

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
    def matches_won(self):
        return [m for m in self.matches if m.is_winner(self)]

    @property
    def matches_lost(self):
        return [m for m in self.matches if not m.is_winner(self)]

    def winrate(self):
        try:
            return (float(len(self.matches_won)) / len(self.matches)) * 100
        except ZeroDivisionError:
            return 0

    @property
    def matches(self):
        if not self._matches:
            self._matches = Match.objects.filter(participations__player=self)
        return self._matches

    @property
    def num_legs_won(self):
        if self._num_legs_won is None:
            self._calculate_statistics()
        return self._num_legs_won

    @property
    def num_legs_lost(self):
        if self._num_legs_lost is None:
            self._calculate_statistics()
        return self._num_legs_lost

    @property
    def total_legs(self):
        if self._total_legs is None:
            self._calculate_statistics()
        return self._total_legs

    @property
    def legs_winrate(self):
        try:
            return (float(self.num_legs_won) / self.total_legs) * 100
        except ZeroDivisionError:
            return 0

    @property
    def bogey(self):
        if not self._bogey:
            self._calculate_statistics()
        return self._bogey

    @property
    def favorite(self):
        if not self._favorite:
            self._calculate_statistics()
        return self._favorite

    @property
    def participations(self):
        if not self._participations:
            self._participations = MatchParticipation.objects.filter(player=self).select_related().prefetch_related()
        return self._participations

    def _calculate_statistics(self):
        print('CALCULATING STATS')

        self._num_legs_lost = 0
        self._num_legs_won = 0
        self._total_legs = 0
        player_stats = defaultdict(lambda: [0,0])
        for m in self.matches:
            self._total_legs += m.get_num_legs()
            self._num_legs_won += m.get_score_for_player(self)
            self._num_legs_lost += m.get_score_for_opponent(self)

            index = int(not m.is_winner(self))

            player_stats[m.get_opponent(self)][index] += 1

        print(player_stats)
        sorted_stats = sorted(player_stats.items(), key=lambda i: (i[1][1], -i[1][0]))
        if sorted_stats[-1][1][1] > 0:
            self._bogey = self._get_stats_tuple_for_player(sorted_stats[-1])
        if sorted_stats[0][1][0] > 0:
            self._favorite = self._get_stats_tuple_for_player(sorted_stats[0])

        #if len(losses_per_player) > 0:
        #    self._bogey = sorted(losses_per_player.items(), key=lambda t: t[1])[0][0]
        #else:
        #    self._bogey = None

    def _get_stats_tuple_for_player(self, item):
        wins, losses = item[1]
        return (item[0], wins, losses, (float(wins) / (wins + losses)) * 100)

class Match(models.Model):
    class Meta:
        verbose_name_plural = 'matches'
    date = models.DateTimeField(default=timezone.now)
    objects = FullMatchManager()

    def update_elos(self):
        p1, p2 = self.players
        exp_1 = 1 / (1 + 10 ** ((p2.elo - p1.elo) / 400))
        exp_2 = 1 - exp_1

        p1_elo = p1.elo
        p2_elo = p2.elo

        p1.update_elo(exp_1, self.is_winner(p1))
        p2.update_elo(exp_2, self.is_winner(p2))

        pt1, pt2 = self.participations.all()

        pt1.delta = p1.elo - p1_elo
        pt2.delta = p2.elo - p2_elo

        pt1.save()
        pt2.save()


    @property
    def winner(self):
        # if the participations have been prefetched, this doesnt hit the db again
        return sorted(self.participations.all(), key=lambda pt: pt.score, reverse=True)[0].player

    @property
    def players(self):
        return [pt.player for pt in self.participations.all()]

    def is_winner(self, player):
        return self.winner == player

    def get_score_for_player(self, player):
        for pt in self.participations.all():
            if pt.player == player:
                return pt.score
        raise ValueError('Cannot get score: Player {} did not participate in match {}'.format(player, self))

    def get_score_for_opponent(self, player):
        if not player in self.players:
            raise ValueError('Cannot get score: Player {} did not participate in match {}'.format(player, self))

        for pt in self.participations.all():
            if pt.player != player:
                return pt.score

    def get_opponent(self, player):
        if not player in self.players:
            raise ValueError('Cannot get opponent: Player {} did not participate in match {}'.format(player, self))
        for pt in self.participations.all():
            if pt.player != player:
                return pt.player

    def get_num_legs(self):
        return sum(pt.score for pt in self.participations.all())


    # def has_player(self, player):
    #     return self.defendant == player or self.challenger == player
    #
    # def __str__(self):
    #     return 'Match on {}: {} {} : {} {}'.format(self.date, self.challenger, self.challenger_score, self.defendant_score, self.defendant)


class MatchParticipation(models.Model):
    match = models.ForeignKey(Match, models.CASCADE, related_name='participations')
    player = models.ForeignKey(Player, models.CASCADE)
    score = models.IntegerField(validators=[MinValueValidator(0)])
    delta = models.IntegerField()

    def __str__(self):
        return '{} {}'.format(self.player, self.score)

