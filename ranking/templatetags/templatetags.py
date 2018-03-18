import re

from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, pattern_or_urlname):
    try:
        pattern = '^' + reverse(pattern_or_urlname) + '$'
    except NoReverseMatch:
        pattern = pattern_or_urlname
    path = context['request'].path
    if re.match(pattern, path):
        return 'active'
    return ''

@register.filter
def sign(value):
    value = round(value)
    if value > 0:
        return '<span class="text-success">+{}</span>'.format(value)
    return '<span class="text-danger">{}</span>'.format(value)
