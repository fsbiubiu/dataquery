# coding: utf-8
from django.conf.urls import include, url
# from django.contrib import admin
from .views import HomeView

urlpatterns = [
    # url(r'^admin/', include(admin.site.urls)),

    url(r'^$', HomeView.as_view(), name='home'),

    url(r'^accounts/', include('accounts.urls')),
    url(r'^sql/', include('sqlexecute.urls')),
    url(r'^schema/', include('schema.urls')),

]
