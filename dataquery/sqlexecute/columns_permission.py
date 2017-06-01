# coding: utf-8
import json
import logging

from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, render
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
from .models import (
    DbInfo,
    DbLog,
    DbPermission,
    TablePermission,
    ExecLog,
    ColumnsPermission,
)

logger = logging.getLogger('django')


class ColumnsPermissionListView(DispatchAdminMixin, ListView):
    model = ColumnsPermission
    template_name = "sqlexecute/columns_permission/list.html"
    paginate_by = '30'
    context_object_name = 'cps'

    def get_context_data(self, **kwargs):
        context = super(ColumnsPermissionListView, self).get_context_data(**kwargs)
        context['dbs'] = DbInfo.objects.get_all_db()
        return context

    def get_queryset(self):
        """ 以后优化一下 """
        q = {'status': True}
        dbid = self.request.GET.get('dbid', None)
        if dbid:
            q["db_id"] = dbid

        result = self.model.objects.filter(**q)

        l = {}
        for r in result:
            key = u"{}-{}".format(r.db.name, r.table_name)
            if key not in l:
                l[key] = [r]
            else:
                l[key].append(r)

        return sorted([l[k] for k in l])


class ColumnsPermissionCreateView(DispatchAdminMixin, View):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        dbs = DbInfo.objects.get_all_db()

        context = {'dbs': dbs, }
        return render(request, "sqlexecute/columns_permission/create.html", context)

    def post(self, request, *args, **kwargs):
        db = get_object_or_404(DbInfo, pk=request.POST.get('db'))
        table_name = request.POST.get('table_name')
        new_columns = request.POST.getlist('columns')

        cps = ColumnsPermission.objects.filter(db=db, table_name=table_name, status=True)
        new_columns = set(new_columns) - set([cp.column_name for cp in cps])
        l = []
        for c in new_columns:
            l.append(ColumnsPermission(db=db, table_name=table_name, column_name=c))
        if l:
            ColumnsPermission.objects.bulk_create(l)

        return HttpResponseRedirect(reverse_lazy('columns_permission_list'))


class CPDeleteView(DispatchAdminMixin, View):
    http_method_names = ['post', ]

    def post(self, request, *args, **kwargs):
        table_del = request.GET.get('table_del')
        b = get_object_or_404(ColumnsPermission, pk=kwargs.get('pk'))
        if not table_del:
            b.status = False
            b.save()
        else:
            ColumnsPermission.objects.filter(db=b.db, table_name=b.table_name, status=True).update(status=False)

        r = {'success': True, 'msg': ''}
        return HttpResponse(json.dumps(r), content_type="application/json")
