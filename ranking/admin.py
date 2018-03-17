from django.contrib import admin
import ranking.models
# Register your models here.

admin.site.register(ranking.models.Player)
admin.site.register(ranking.models.Match)