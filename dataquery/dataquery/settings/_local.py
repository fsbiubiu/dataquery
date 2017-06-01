# coding: utf-8

from base import *


DEBUG = False

ALLOWED_HOSTS = ['*']


# 報警发送邮件
SEND_MAIL = {
    "url": "http://10.8.45.202:8086/api/notify?access_token=MOa3YqudLK&type=1&async=1",
    "tos": "hui.dong@mljr.com",
}


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'data_query',
        'USER': 'user_dataQuery',
        'PASSWORD': '5ekANbXSZnQA9zDtaZTE',
        'HOST': '10.8.45.202',
        'PORT': '3380',
        'CONN_MAX_AGE': 150,
    }
}

REDIS_SETTINGS = {
    "host": "127.0.0.1",
    "port": 6379,
}
