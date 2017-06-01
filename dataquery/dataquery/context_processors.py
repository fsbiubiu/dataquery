# coding:utf-8
from django.conf import settings


def settings_var(request):
    """
    在template里加上settings一些变量
    """
    result = {'PERMISSION_DB_CONFIG': '', 'PERMISSION_CENSOR': ''}

    return result
