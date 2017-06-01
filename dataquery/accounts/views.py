# coding: utf-8
import json

from django.views.generic import View
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.template.loader import render_to_string

from .forms import CreateUserForm, DepartmentCreateForm, PasswordChangeForm, UserUpdateForm, PasswordResetForm
from .models import Department
from lib.mixin import DispatchAdminMixin, LoginRequiredMixin
from lib.util import send_mail
from sqlexecute.models import DbInfo, DbPermission, TablePermission


class UserListView(DispatchAdminMixin, ListView):
    template_name = "accounts/user_list.html"
    model = User
    context_object_name = "auth_users"
    paginate_by = "30"

    def get_queryset(self):
        username = self.request.GET.get('username')
        if username:
            return User.objects.filter(username__contains=username)
        else:
            return User.objects.all()


class UserCreateView(DispatchAdminMixin, CreateView):
    model = User
    template_name = "accounts/user_create.html"
    form_class = CreateUserForm
    success_url = reverse_lazy('user_list')


class UserUpdateView(DispatchAdminMixin, UpdateView):
    model = User
    template_name = "accounts/user_update.html"
    form_class = UserUpdateForm
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        """ """
        self.object = form.save()

        r = {'success': True, 'msg': u"操作成功"}
        return HttpResponse(json.dumps(r), content_type="application/json")


class UserDeleteView(DispatchAdminMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        user_ = get_object_or_404(User, pk=pk)
        user_.is_active = not user_.is_active
        user_.save()
        r = {'success': True, 'msg': u"操作成功"}
        return HttpResponse(json.dumps(r), content_type="application/json")


class UserChangePasswordView(LoginRequiredMixin, FormView):
    model = User
    template_name = "accounts/user_change_password.html"
    form_class = PasswordChangeForm
    success_url = reverse_lazy('home')

    def get_form_kwargs(self):
        kwargs = super(UserChangePasswordView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class UserPasswordResetView(FormView):
    template_name = "accounts/user_password_reset.html"
    form_class = PasswordResetForm

    def form_invalid(self, form):
        return HttpResponse(json.dumps({'success': False, 'msg': u"用户名不正确"}), content_type="application/json")

    def form_valid(self, form):
        username = form.cleaned_data['username']
        # 发送邮件
        user = User.objects.filter(username=username).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            url = "{}://{}{}".format(
                self.request.scheme, self.request.META['HTTP_HOST'],
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}),)
            email = "{}@mljr.com".format(user.username)

            html_content = render_to_string('reset_password_email.html', {'url': url})
            send_mail(settings.SEND_MAIL['url'], email, u'数据查询申请执行', html_content)
            return HttpResponse(json.dumps({'success': True, 'msg': u"操作成功"}), content_type="application/json")
        else:
            return HttpResponse(json.dumps({'success': False, 'msg': u"用户名不正确"}), content_type="application/json")


class UserPasswordResetDoneView(View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, "accounts/user_pwd_reset_done.html", context)


class DepartmentListView(DispatchAdminMixin, ListView):
    template_name = "accounts/department_list.html"
    model = Department
    context_object_name = "departments"
    paginate_by = "30"

    def get_queryset(self):
        return Department.objects.filter(status=True)


class DepartmentCreateView(DispatchAdminMixin, CreateView):
    model = Department
    template_name = "accounts/department_create.html"
    form_class = DepartmentCreateForm
    success_url = reverse_lazy('department_list')


class DepartmentUpdateView(DispatchAdminMixin, UpdateView):
    model = Department
    template_name = "accounts/department_update.html"
    form_class = DepartmentCreateForm
    success_url = reverse_lazy('department_list')

    def form_valid(self, form):
        """ """
        self.object = form.save()

        r = {'success': True, 'msg': u"操作成功"}
        return HttpResponse(json.dumps(r), content_type="application/json")


class DepartmentDeleteView(DispatchAdminMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        # 有用户不能删除
        pk = kwargs.get('pk')
        d = get_object_or_404(Department, pk=pk)
        d.status = False
        d.save()
        r = {'success': True, 'msg': u"删除成功"}
        return HttpResponse(json.dumps(r), content_type="application/json")


class PermissionAddView(DispatchAdminMixin, View):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        u = get_object_or_404(User, pk=kwargs.get('pk'))
        dbs = DbInfo.objects.get_all_db()

        tables = DbPermission.objects.get_user_perm(u)

        context = {'dbs': dbs, 'u': u, 'tables': tables}
        return render(request, "accounts/permission_add.html", context)

    def post(self, request, *args, **kwargs):
        u = get_object_or_404(User, pk=kwargs.get('pk'))
        dbid = request.POST.get('db')
        have_all = bool(request.POST.get('have_all', False))
        have_secret_columns = bool(request.POST.get('have_secret_columns', False))
        new_tables = request.POST.getlist('tables')
        # 判断已有的去重 tables判断是否合法
        db = get_object_or_404(DbInfo, pk=dbid)
        dbp = DbPermission.objects.filter(db=db, user=u, status=True).first()
        if not dbp:
            dbp = DbPermission(db=db, user=u, have_all=have_all, have_secret_columns=have_secret_columns)
            dbp.save()
        else:
            if have_all:
                dbp.have_all = True
            if have_secret_columns:
                dbp.have_secret_columns = True
            if have_all or have_secret_columns:
                dbp.save()

        tables = TablePermission.objects.filter(db_perm=dbp, status=True)
        new_tables = set(new_tables) - set([t.table_name for t in tables])
        l = []
        for table in new_tables:
            l.append(TablePermission(db_perm=dbp, table_name=table))
        if l:
            TablePermission.objects.bulk_create(l)
        # 修改用户session
        sessions = Session.objects.filter(expire_date__gt=timezone.now())
        for s in sessions:
            data = SessionStore().decode(s.session_data)
            if data.get('_auth_user_id') == str(u.pk):
                permission = DbPermission.objects.get_user_perm(u)
                user_session = SessionStore(session_key=s.session_key)
                user_session['permission'] = {p.db.pk: permission[p] for p in permission}
                user_session['permission_db'] = {p.db.pk: {'name': p.db.db_name, 'have_secret_columns': p.have_secret_columns} for p in permission}
                user_session.save()

        r = {'success': True, 'msg': u"添加成功"}
        return HttpResponse(json.dumps(r), content_type="application/json")


class PermissionDelView(DispatchAdminMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        u = get_object_or_404(User, pk=kwargs.get('pk'))
        dbpid = request.GET.get('dbpid')
        table_name = request.GET.get('table_name')
        have_secret_columns = request.GET.get('have_secret_columns')
        dbp = DbPermission.objects.filter(pk=dbpid, user=u, status=True).first()
        if dbp and have_secret_columns:
            dbp.have_secret_columns = False
            dbp.save()
        elif dbp and not table_name:
            if dbp:
                dbp.status = False
                dbp.save()

            TablePermission.objects.filter(db_perm=dbp, status=True).update(status=False)

        elif dbp and table_name == '__have_all__':
            dbp.have_all = False
            dbp.save()
        elif dbp and table_name:
            TablePermission.objects.filter(db_perm=dbp, table_name=table_name, status=True).update(status=False)
        # 修改用户session
        sessions = Session.objects.filter(expire_date__gt=timezone.now())
        for s in sessions:
            data = SessionStore().decode(s.session_data)
            if data.get('_auth_user_id') == str(u.pk):
                permission = DbPermission.objects.get_user_perm(u)
                user_session = SessionStore(session_key=s.session_key)
                user_session['permission'] = {p.db.pk: permission[p] for p in permission}
                user_session['permission_db'] = {p.db.pk: {'name': p.db.db_name, 'have_secret_columns': p.have_secret_columns} for p in permission}
                user_session.save()

        r = {'success': True, 'msg': u"删除成功"}
        return HttpResponse(json.dumps(r), content_type="application/json")
