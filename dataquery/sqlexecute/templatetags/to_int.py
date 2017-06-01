# coding: utf-8
from django import template


register = template.Library()


@register.filter
def to_int(value):
    """ string to int """
    try:
        return int(value)
    except:
        return 0
