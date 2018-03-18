from django.contrib import admin
import ranking.models
# Register your models here.


class PlayerAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(ranking.models.Player, PlayerAdmin)
admin.site.register(ranking.models.Match)