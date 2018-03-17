from ranking.models import Player

import logging
logger = logging.getLogger(__name__)

def get_session_player(session):
    try:
        key = session['profile']
    except KeyError:
        return None
    try:
        return Player.objects.get(pk=key)
    except Player.DoesNotExist:
        logger.warning('SESSION: no matching player for key=%s', key)
        return None


def set_session_player(session, player):
    if not player.pk:
        msg = 'SESSION: player not saved yet: name=%s'
        logger.warning(msg, player.name)
        return
    session['profile'] = player.pk


def clear_session_player(session):
    try:
        del session['profile']
    except KeyError:
        pass