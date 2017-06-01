# coding: utf-8
from django import template


register = template.Library()


@register.filter
def format_data(value):
    """
    更改python数据类型和sql数据类型不一致的问题
    """
    if value is None:
        return 'NULL'
    else:
        return value
