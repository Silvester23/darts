# Generated by Django 2.0.3 on 2018-03-18 12:40

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('challenger_score', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('defendant_score', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('challenger_delta', models.IntegerField()),
                ('defendant_delta', models.IntegerField()),
            ],
            options={
                'verbose_name_plural': 'matches',
            },
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('elo', models.FloatField(default=1000)),
                ('name', models.CharField(max_length=30, unique=True, validators=[django.core.validators.RegexValidator('^[\\w. @+-]+$', 'Der Name enthält ein ungültiges Zeichen', 'invalid')])),
                ('pw_hash', models.CharField(max_length=128)),
                ('slug', models.SlugField(unique=True)),
            ],
            options={
                'default_manager_name': 'objects',
            },
        ),
        migrations.AddField(
            model_name='match',
            name='challenger',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='challenger', to='ranking.Player'),
        ),
        migrations.AddField(
            model_name='match',
            name='defendant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='defendant', to='ranking.Player'),
        ),
    ]
