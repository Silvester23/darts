from django.http import HttpResponseRedirect
from django.shortcuts import reverse

from django.utils.http import urlencode
from ranking.support import get_session_player


def url_with_query(path, **kwargs):
    return path + '?' + urlencode(kwargs)


def player_login_required(view_func):

    def player_login_wrapper(request, *args, **kwargs):

        if get_session_player(request.session) is not None:
            return view_func(request, *args, **kwargs)
        return HttpResponseRedirect(
            url_with_query(reverse('login'), next=request.path)
        )

    return player_login_wrapper