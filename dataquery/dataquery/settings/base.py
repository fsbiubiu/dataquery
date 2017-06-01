# coding: utf-8
from os.path import join, abspath

from settings import *


root = lambda *x: join(abspath(BASE_DIR), *x)

TIME_ZONE = 'Asia/Shanghai'

LANGUAGE_CODE = 'zh-hans'

LOGIN_REDIRECT_URL = '/'

STATICFILES_DIRS = (
    root('static'),
)

TEMPLATES[0]['DIRS'].append(root('templates'))
# TEMPLATES[0]['OPTIONS']['context_processors'].append("dataquery.context_processors.settings_var")


INSTALLED_APPS += (
    'django.contrib.humanize',

    'accounts',
    'sqlexecute',
    'schema',
)
