# coding: utf-8
from django.conf.urls import url

from .views import (
    DBCreateView,
    DBListView,
    DBUpdateView,
    DBDeleteView,

    QueryFormView,
    CensorQueryFormView,
    CensorQueryListView,
    MyQueryListView,
    CensorUpdateView,
    CensorDeleteView,
    ResultView,
    GetJobView,

    KeywordsView,
    TablesListView,
    ColumsListView,
)
from .columns_permission import (
    ColumnsPermissionListView,
    ColumnsPermissionCreateView,
    CPDeleteView,
)


urlpatterns = [
    # db
    url(r'^db_conf/add_db/$', DBCreateView.as_view(), name='db_add'),
    url(r'^db_conf/db_list/$', DBListView.as_view(), name='db_list'),
    url(r'^db_conf/edit_db/(?P<pk>[-_\w]+)/$', DBUpdateView.as_view(), name='db_edit'),
    url(r'^db_conf/delete_db/(?P<pk>[-_\w]+)/$', DBDeleteView.as_view(), name='db_delete'),

    # columns
    url(r'^columns/list/$', ColumnsPermissionListView.as_view(), name='columns_permission_list'),
    url(r'^columns/create/$', ColumnsPermissionCreateView.as_view(), name='columns_permission_create'),
    url(r'^columns/del/(?P<pk>[-_\w]+)/$', CPDeleteView.as_view(), name='columns_permission_delete'),

    # 不需要审核查询
    url(r'^query/$', QueryFormView.as_view(), name='query'),
    # 需要审核
    url(r'^query/censor/$', CensorQueryFormView.as_view(), name='query_censor'),
    url(r'^query/censor_log/$', MyQueryListView.as_view(), name='my_censor_log_list'),
    url(r'^censor_log_list/$', CensorQueryListView.as_view(), name='censor_log_list'),
    url(r'^query/get_job/$', GetJobView.as_view(), name='get_job'),
    # 审核
    url(r'^censor/(?P<pk>[-_\w]+)/$', CensorUpdateView.as_view(), name='censor'),
    # 删除
    url(r'^censor/delete/(?P<pk>[-_\w]+)/$', CensorDeleteView.as_view(), name='censor_delete'),

    # 执行结果
    url(r'^result/(?P<pk>[-_\w]+)/$', ResultView.as_view(), name='result'),

    # 获取自动提示关键字
    url(r'^keywords/$', KeywordsView.as_view(), name='keywords'),
    url(r'^table_list/$', TablesListView.as_view(), name='table_list'),
    # 返回一个表的所有字段
    url(r'^columns/$', ColumsListView.as_view(), name='columns_list'),

]
