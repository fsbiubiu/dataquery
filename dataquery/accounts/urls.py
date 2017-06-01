# coding: utf-8
from django.conf.urls import url
from django.contrib.auth.views import login, logout
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth import views

from .forms import LoginForm
from .views import (
    UserCreateView,
    UserUpdateView,
    UserListView,
    UserDeleteView,
    DepartmentListView,
    DepartmentCreateView,
    DepartmentUpdateView,
    DepartmentDeleteView,
    PermissionAddView,
    PermissionDelView,
    UserChangePasswordView,
    UserPasswordResetView,
    UserPasswordResetDoneView,
)


urlpatterns = [
    url(r'^login/$', login, {'authentication_form': LoginForm, 'template_name': 'accounts/login.html'}, name='login'),
    url(r'^logout/$', logout, {'next_page': reverse_lazy('login')}, name='logout'),
    url(r'^changepassword/$', UserChangePasswordView.as_view(), name='user_change_password'),
    url(r'^password_reset/$', UserPasswordResetView.as_view(), name='user_password_reset'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.password_reset_confirm, {'template_name': 'accounts/user_pwd_reset_confirm.html'}, name='password_reset_confirm'),
    url(r'^reset/done/$', UserPasswordResetDoneView.as_view(), name='password_reset_complete'),


    url(r'^list/$', UserListView.as_view(), name='user_list'),
    url(r'^create/$', UserCreateView.as_view(), name='user_create'),
    url(r'^update/(?P<pk>[\d]+)/$', UserUpdateView.as_view(), name='user_update'),
    url(r'^delete/(?P<pk>[\d]+)/$', UserDeleteView.as_view(), name='user_delete'),

    url(r'^department/list/$', DepartmentListView.as_view(), name='department_list'),
    url(r'^department/create/$', DepartmentCreateView.as_view(), name='department_create'),
    url(r'^department/update/(?P<pk>[\d]+)/$', DepartmentUpdateView.as_view(), name='department_update'),
    url(r'^department/delete/(?P<pk>[\d]+)/$', DepartmentDeleteView.as_view(), name='department_delete'),

    url(r'^perm_add/(?P<pk>[\d]+)/$', PermissionAddView.as_view(), name='permission_add'),
    url(r'^perm_del/(?P<pk>[\d]+)/$', PermissionDelView.as_view(), name='permission_del'),
]
