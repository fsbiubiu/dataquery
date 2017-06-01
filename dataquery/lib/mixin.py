# coding: utf-8
from functools import wraps

from django.utils.decorators import available_attrs
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, user_passes_test


LOGIN_URL = reverse_lazy('login')


def admin_login_required(function=None, login_url=LOGIN_URL):
    """ 管理员登陆验证 """
    actual_decorator = user_passes_test(lambda u: u.is_superuser, login_url=login_url)
    if function:
        return actual_decorator(function)
    return actual_decorator


class LoginRequiredMixin(object):
    """
    登陆判断
    """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # permission = getattr(self, "permission", None)
        # # print(self.request.session.get('_user'))
        # if permission and self.request.session.get('_user').get('dept') not in permission:
        #     raise PermissionDenied

        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class DispatchAdminMixin(object):
    """ admin登陆验证 """
    @method_decorator(admin_login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(DispatchAdminMixin, self).dispatch(request, *args, **kwargs)
