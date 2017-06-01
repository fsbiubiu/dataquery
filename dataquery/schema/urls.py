# coding: utf-8
from django.conf.urls import url

from .views import (
    SchemaView,
)


urlpatterns = [
    # schema
    url(r'^$', SchemaView.as_view(), name='schema'),

]
