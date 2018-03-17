from django.contrib.auth.hashers import (
    check_password, make_password,
)
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Player(models.Model):
    elo = models.FloatField(default=1000)
    name = models.CharField(max_length=30, unique=True,
                            validators=[
                                RegexValidator(r'^[\w. @+-]+$', 'Der Name enthält ein ungültiges Zeichen', 'invalid')
                            ])
    pw_hash = models.CharField(max_length=128)

    def set_password(self, plain_password):
        self.pw_hash = make_password(plain_password)

    def is_password(self, plain_password):
        return check_password(plain_password, self.pw_hash)

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.elo)

    def __str__(self):
        return self.__unicode__()

    def update_elo(self, expected_performance, victory):
        self.elo = self.elo + 32 * (int(victory) - expected_performance)
        self.save()


class Match(models.Model):
    class Meta:
        verbose_name_plural = 'matches'
    challenger = models.ForeignKey(Player, models.DO_NOTHING, related_name='challenger')
    defendant = models.ForeignKey(Player, models.DO_NOTHING, related_name='defendant')
    challenger_score = models.IntegerField(validators=[MinValueValidator(0)])
    defendant_score = models.IntegerField(validators=[MinValueValidator(0)])
    date = models.DateTimeField(default=timezone.now)

    @property
    def winner(self):
        if self.challenger_score > self.defendant_score:
            return self.challenger
        elif self.challenger_score < self.defendant_score:
            return self.defendant
        return None

    def is_winner(self, player):
        return self.winner == player

    def update_elos(self):
        exp_c = 1 / (1 + 10 ** ((self.defendant.elo - self.challenger.elo) / 400))
        exp_d = 1 - exp_c

        self.challenger.update_elo(exp_c, self.is_winner(self.challenger))
        self.defendant.update_elo(exp_d, self.is_winner(self.defendant))

    def __str__(self):
        return 'Match on {}: {} {} : {} {}'.format(self.date, self.challenger, self.challenger_score, self.defendant_score, self.defendant)


