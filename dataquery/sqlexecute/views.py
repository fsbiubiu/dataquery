# coding: utf-8
import uuid
import ast
import json
import traceback
import logging

import redis
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic.edit import (
    CreateView,
    FormView,
    UpdateView,
    DeleteView,
)
from django.views.generic import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.conf import settings

from lib.mixin import LoginRequiredMixin, DispatchAdminMixin
from lib.util import send_mail
from lib.db import sql_connect, get_tables, encode_data, return_csv, get_columns, return_excel
from .models import (
    DbInfo,
    DbLog,
    DbPermission,
    TablePermission,
    ExecuteSQL,
    ExecLog,
)
from .forms import (
    AddDBForm,
    QueryForm,
    DBSearchForm,
    CensorQueryForm,
)

logger = logging.getLogger('django')


class AddFormMixin(object):
    def get_context_data(self, **kwargs):
        context = super(AddFormMixin, self).get_context_data(**kwargs)
        context['form'] = self.form_class(self.request.GET)
        return context


class ListSearchMixin(object):
    search_keywords = []

    def get_queryset(self):
        get_dict = self.request.GET
        q = {'status': True}
        for keyword in self.search_keywords:
            value = get_dict.get(keyword, None)
            if value:
                q[keyword] = value

        if q:
            result = self.model.objects.filter(**q)
        else:
            result = self.model.objects.filter(**q)

        return result

    def get_context_data(self, **kwargs):
        context = super(ListSearchMixin, self).get_context_data(**kwargs)
        queries_without_page = self.request.GET.copy()
        if 'page' in queries_without_page:
            del queries_without_page['page']
        context['queries'] = queries_without_page

        return context


class DBCreateView(DispatchAdminMixin, CreateView):
    model = DbInfo
    form_class = AddDBForm
    template_name = "sqlexecute/db_create.html"
    success_url = reverse_lazy('db_list')

    def form_valid(self, form):
        """
        """
        self.object = form.save()

        dblog = DbLog(user=self.request.user, action="创建", db=self.object)
        dblog.save()
        return HttpResponseRedirect(self.get_success_url())


class DBListView(ListSearchMixin, AddFormMixin, DispatchAdminMixin, ListView):
    model = DbInfo
    form_class = DBSearchForm
    template_name = "sqlexecute/db_list.html"
    paginate_by = '30'
    context_object_name = 'dbs'
    search_keywords = ['ip', 'db_name']


class DBUpdateView(DispatchAdminMixin, UpdateView):
    model = DbInfo
    form_class = AddDBForm
    template_name = "sqlexecute/db_create.html"
    success_url = reverse_lazy('db_list')

    def form_valid(self, form):
        """
        判断密码框为空时，不更新密码，
        导致不能更新成空密码
        """
        if not form.instance.password:
            form.instance.password = self.get_object().password

        self.object = form.save()

        dblog = DbLog(user=self.request.user, action="更新", db=self.object)
        dblog.save()
        return HttpResponseRedirect(self.get_success_url())


class DBDeleteView(DispatchAdminMixin, DeleteView):
    model = DbInfo
    success_url = reverse_lazy('db_list')
    http_method_names = ['post', ]

    def post(self, request, *args, **kwargs):
        b = get_object_or_404(DbInfo, pk=kwargs.get('pk'))
        b.status = False
        b.save()
        dblog = DbLog(user=self.request.user, action="删除", db=b)
        dblog.save()

        r = {'success': True, 'msg': ''}
        return HttpResponse(json.dumps(r), content_type="application/json")


class QueryFormView(LoginRequiredMixin, FormView):
    template_name = "sqlexecute/query_sql.html"
    form_class = QueryForm

    def get_form_kwargs(self):
        kwargs = super(QueryFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(QueryFormView, self).get_context_data(**kwargs)
        # 设置session
        if not self.request.session.get('permission', '') and not self.request.user.is_superuser:
            permission = DbPermission.objects.get_user_perm(self.request.user)
            self.request.session['permission'] = {p.db.pk: permission[p] for p in permission}
            self.request.session['permission_db'] = {p.db.pk: {'name': p.db.db_name, 'have_secret_columns': p.have_secret_columns} for p in permission}
        context['page_range'] = range(1, 11)
        return context

    def form_invalid(self, form):
        """ 如果表单错误,返回json """
        errors = []
        for l in form.errors.values():
            errors += l
        return HttpResponse(json.dumps({'error': ' '.join(errors)}), content_type="application/json")

    def form_valid(self, form):
        """ 判断执行人是否有操作该数据库的权限 """
        dbid = form.cleaned_data['db']
        sql = form.cleaned_data['sql']
        explain = self.request.POST.get('explain')
        try:
            page = int(self.request.POST.get('page', 1))
        except:
            page = 1
        if page > 10 or page < 1:
            page = 1

        db = get_object_or_404(DbInfo, pk=dbid)
        # 判断数据库权限
        is_superuser = self.request.user.is_superuser
        permission = self.request.session.get('permission', {})
        permission_db = self.request.session.get('permission_db', {})
        if not (is_superuser or dbid in permission):
            # 改成提示
            # raise PermissionDenied
            return HttpResponseRedirect('/')

        # 查询
        exe = ExecuteSQL(db, sql, explain, is_superuser, permission_db, permission, page=page)
        r = []
        for sql_ in exe.sql_split():
            exec_data = exe.execute(sql_)
            if exec_data:
                r.append(exec_data)
        exe.close_session()

        return HttpResponse(json.dumps(r and r[-1]), content_type="application/json")
        # page_range = range(1, 11)
        # return self.render_to_response(self.get_context_data(r=r, form=form, page=page, page_range=page_range))


class MyQueryListView(LoginRequiredMixin, ListView):
    model = ExecLog
    template_name = "sqlexecute/my_query_list.html"
    paginate_by = '30'
    context_object_name = 'execlogs'

    def get_queryset(self):
        return ExecLog.objects.filter(user=self.request.user).exclude(status=5)


class CensorQueryListView(DispatchAdminMixin, ListView):
    model = ExecLog
    template_name = "sqlexecute/censor_query_list.html"
    paginate_by = '30'
    context_object_name = 'execlogs'

    def get_queryset(self):
        username = self.request.GET.get('username')
        try:
            status = int(self.request.GET.get('status'))
        except:
            status = 0
        l = ExecLog.objects.exclude(status=5)
        if username:
            l = l.filter(Q(user__username__contains=username) | Q(user__first_name__contains=username))
        if status:
            l = l.filter(status=status)

        return l


class CensorDeleteView(LoginRequiredMixin, View):
    """ 删除提交的审核"""
    http_method_names = ['post', ]

    def post(self, request, *args, **kwargs):
        execlog = get_object_or_404(ExecLog, pk=kwargs.get('pk'))
        # if execlog.user != request.user and not request.user.is_superuser:
        if not request.user.is_superuser:
            r = {'success': False, 'msg': '没有权限删除'}
            return HttpResponse(json.dumps(r), content_type="application/json")

        if execlog.status != 5:
            execlog.status = 5
            execlog.save()

        r = {'success': True, 'msg': ''}
        return HttpResponse(json.dumps(r), content_type="application/json")


class CensorUpdateView(DispatchAdminMixin, View):
    model = ExecLog
    success_url = reverse_lazy('censor_log_list')
    http_method_names = ['post', ]

    def post(self, request, *args, **kwargs):
        self.object = get_object_or_404(ExecLog, pk=kwargs.get('pk'))
        if self.object.status == 2:
            is_pass = request.GET.get('is_pass', None)
            status = 4 if is_pass else 3
            self.object.censor_update(censor=request.user, status=status)

        r = {'success': True, 'msg': ''}
        return HttpResponse(json.dumps(r), content_type="application/json")


class CensorQueryFormView(LoginRequiredMixin, CreateView):
    template_name = "sqlexecute/censor_query.html"
    form_class = CensorQueryForm
    success_url = reverse_lazy('my_censor_log_list')

    def get_form_kwargs(self):
        kwargs = super(CensorQueryFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(CensorQueryFormView, self).get_context_data(**kwargs)
        # 设置session
        if not self.request.session.get('permission', '') and not self.request.user.is_superuser:
            permission = DbPermission.objects.get_user_perm(self.request.user)
            self.request.session['permission'] = {p.db.pk: permission[p] for p in permission}
            self.request.session['permission_db'] = {p.db.pk: {'name': p.db.db_name, 'have_secret_columns': p.have_secret_columns} for p in permission}
        return context

    def form_valid(self, form):
        """ 判断执行人是否有操作该数据库的权限 """
        # 判断数据库权限
        is_superuser = self.request.user.is_superuser
        permission = self.request.session.get('permission', {})
        if not (is_superuser or str(form.instance.db.pk) in permission):
            return HttpResponseRedirect('/')

        jobid = uuid.uuid1().hex
        form.instance.user = self.request.user
        form.instance.status = 6
        form.instance.jobid = jobid
        self.object = form.save()

        # 执行，导出结果
        is_superuser = self.request.user.is_superuser
        permission_db = self.request.session.get('permission_db', {})
        data = {'type': 'query', 'is_superuser': is_superuser, 'permission_db': permission_db,
                'permission': permission, 'jobid': jobid, 'id': self.object.pk}
        r = redis.StrictRedis(host=settings.REDIS_SETTINGS['host'], port=settings.REDIS_SETTINGS['port'], db=0)
        r.rpush('dataquery_dump_sql', data)
        # return HttpResponse(json.dumps({'success': True, "jobid": jobid}), content_type="application/json")
        # return return_csv(r)
        return HttpResponseRedirect(self.get_success_url())


class GetJobView(LoginRequiredMixin, View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        """ 轮训job，直到产生结果，并返回
        如果取消，就取消job
        """
        jobid = request.GET.get('jobid', 0)
        id_ = int(request.GET.get('id', 0))
        download = request.GET.get('download', None)
        is_excel = request.GET.get('is_excel', None)
        cancel = request.GET.get('cancel', None)
        r = redis.StrictRedis(host=settings.REDIS_SETTINGS['host'], port=settings.REDIS_SETTINGS['port'], db=0)
        if cancel:
            r.rpush('dataquery_dump_sql', {'type': 'cancel', 'jobid': jobid})
            return HttpResponse(json.dumps({'success': False, 'msg': '已取消导出操作'}), content_type="application/json")
        if download:
            log = ExecLog.objects.filter(jobid=jobid, pk=id_)
            result = r.get("job:"+jobid)
            if not log:
                return HttpResponseRedirect(reverse_lazy('query_censor'))
            if not result:
                log = log[0]
                log.status = 8
                log.save()
                return HttpResponseRedirect(reverse_lazy('query_censor'))

            log = log[0]
            log.status = 8
            log.save()
            r.delete("job:"+jobid)
            result = json.loads(result)
            if is_excel:
                return return_excel(result['data'])
            else:
                return return_csv(result['data'])

        if r.exists("job:"+jobid):
            result = json.loads(r.get("job:"+jobid))
            if result['success']:
                return HttpResponse(json.dumps({'success': True}), content_type="application/json")
            else:
                return HttpResponse(json.dumps(result), content_type="application/json")
        return HttpResponse(json.dumps({'success': False, 'msg': ''}), content_type="application/json")


class ResultView(LoginRequiredMixin, DetailView):
    """ 执行结果"""
    model = ExecLog
    template_name = "sqlexecute/result.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # 设置session
        if not self.request.session.get('permission', '') and not request.user.is_superuser:
            permission = DbPermission.objects.get_user_perm(self.request.user)
            self.request.session['permission'] = {p.db.pk: permission[p] for p in permission}
            self.request.session['permission_db'] = {p.db.pk: {'name': p.db.db_name, 'have_secret_columns': p.have_secret_columns} for p in permission}

        if (self.object.user == request.user) and (self.object.status in [1, 4]) and (not self.object.is_exec):
            # 查询
            is_superuser = self.request.user.is_superuser
            permission = self.request.session.get('permission', {})
            permission_db = self.request.session.get('permission_db', {})
            jobid = uuid.uuid1().hex
            self.object.jobid = jobid
            self.object.status = 7
            self.object.save()

            data = {'type': 'query', 'is_superuser': is_superuser, 'permission_db': permission_db,
                    'permission': permission, 'jobid': jobid, 'id': self.object.pk}
            r = redis.StrictRedis(host=settings.REDIS_SETTINGS['host'], port=settings.REDIS_SETTINGS['port'], db=0)
            r.rpush('dataquery_dump_sql', data)
            return HttpResponse(json.dumps({'success': True, 'jobid': jobid}), content_type="application/json")

            # if download:
            #     return return_csv(r)
            # return self.render_to_response(self.get_context_data(r=r))
        else:
            return HttpResponseRedirect(reverse_lazy('my_censor_log_list'))


class KeywordsView(LoginRequiredMixin, View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        """ 区分db查询
        """
        try:
            dbid = int(request.GET.get('dbid', 0))
        except:
            dbid = 0
        if not dbid:
            return HttpResponse(json.dumps({}), content_type="application/json")

        db = get_object_or_404(DbInfo, pk=dbid)
        r = redis.StrictRedis(host=settings.REDIS_SETTINGS['host'], port=settings.REDIS_SETTINGS['port'], db=0)
        db_keywords = r.hgetall('db_keyword_{}'.format(dbid))
        if db_keywords:
            _db_keywords = {}
            for k, v in db_keywords.items():
                _db_keywords[k] = ast.literal_eval(v)
            return HttpResponse(json.dumps(_db_keywords), content_type="application/json")

        session = sql_connect(db.get_db_connect_str(), encoding=db.get_encode_display())
        db_keywords = {}
        error = False
        try:
            data = session.execute('select TABLE_NAME, COLUMN_NAME from information_schema.COLUMNS WHERE `TABLE_SCHEMA`= :db_name', {'db_name': db.db_name})
            data = data.fetchall()
            data = encode_data(data, db.encode)
            for c in data:
                if c[0].islower() and c[1].islower():
                    if c[1] not in db_keywords:
                        db_keywords[c[1]] = []
                    if c[0] not in db_keywords:
                        db_keywords[c[0]] = [c[1]]
                    else:
                        db_keywords[c[0]].append(c[1])
        except:
            error = True
            logger.error(traceback.format_exc())

        try:
            session.commit()
        except:
            error = True
            logger.error(traceback.format_exc())
        finally:
            session.close()

        # print(db_keywords)
        if not error:
            r.hmset('db_keyword_{}'.format(dbid), db_keywords)
            # 60 * 60 * 24 = 86400
            r.expire('db_keyword_{}'.format(dbid), 86400)
        return HttpResponse(json.dumps(db_keywords), content_type="application/json")


class TablesListView(LoginRequiredMixin, View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        """ 返回一个DB的所有表名
        perm: 返回有权限的表名列表
        """
        try:
            dbid = int(request.GET.get('dbid', 0))
        except:
            dbid = 0
        if not dbid:
            return HttpResponse(json.dumps({}), content_type="application/json")

        perm = request.GET.get('perm')

        db = get_object_or_404(DbInfo, pk=dbid)

        if perm:
            tables = TablePermission.objects.get_user_tables(request.user, db)
            if tables != u'__have_all__':
                r = {'success': True, 'data': tables}
                return HttpResponse(json.dumps(r), content_type="application/json")

        session = sql_connect(db.get_db_connect_str(), encoding=db.get_encode_display())

        try:
            tables = get_tables(session, db.db_name, db.encode)
        except:
            logger.error(traceback.format_exc())
            return HttpResponse(json.dumps({'success': False, 'msg': u"获取失败"}), content_type="application/json")
        finally:
            session.close()

        r = {'success': True, 'data': tables}
        return HttpResponse(json.dumps(r), content_type="application/json")


class ColumsListView(LoginRequiredMixin, View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        """ 返回一个表所有字段名
        """
        try:
            dbid = int(request.GET.get('dbid', 0))
        except:
            dbid = 0
        if not dbid:
            return HttpResponse(json.dumps({}), content_type="application/json")

        table_name = request.GET.get('table_name')
        # 判断db是否删除
        db = get_object_or_404(DbInfo, pk=dbid)

        session = sql_connect(db.get_db_connect_str(), encoding=db.get_encode_display())
        try:
            columns = get_columns(session, db.db_name, table_name, db.encode)
        except:
            logger.error(traceback.format_exc())
            return HttpResponse(json.dumps({'success': False, 'msg': u"获取失败"}), content_type="application/json")
        finally:
            session.close()

        r = {'success': True, 'data': columns}
        return HttpResponse(json.dumps(r), content_type="application/json")
