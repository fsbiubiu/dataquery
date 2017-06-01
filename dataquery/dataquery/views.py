# coding: utf-8
from django.shortcuts import render
from django.views.generic.base import View

from lib.mixin import LoginRequiredMixin
from sqlexecute.models import DbPermission


class HomeView(LoginRequiredMixin, View):
    template_name = 'home.html'

    def get(self, request):

        permission = DbPermission.objects.get_user_perm(request.user)

        if not request.session.get('permission', '') and not request.user.is_superuser:
            request.session['permission'] = {p.db.pk: permission[p] for p in permission}
            request.session['permission_db'] = {p.db.pk: {'name': p.db.db_name, 'have_secret_columns': p.have_secret_columns} for p in permission}

        return render(request, self.template_name, {'permission': permission})
