# coding: utf-8
import sqlparse
from django import forms
# from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import (
    DbInfo,
    ExecLog,
    ExecuteSQL,
)


class AddDBForm(forms.ModelForm):
    class Meta:
        model = DbInfo
        fields = ('name', 'ip', 'port', 'db_name', 'username', 'password', 'encode', )
        widgets = {
            'password': forms.PasswordInput,
        }

    def __init__(self, *args, **kwargs):
        super(AddDBForm, self).__init__(*args, **kwargs)


class QueryForm(forms.Form):

    def __init__(self, request, user, *args, **kwargs):
        super(QueryForm, self).__init__(*args, **kwargs)
        self.request_ = request
        choices = DbInfo.objects.get_db_choices(user=user)
        choices = choices or [(0, '--选择数据库--'), ]
        self.fields['db'] = forms.ChoiceField(label=u"数据库", choices=choices)
        self.fields['sql'] = forms.CharField(label=u"SQL", widget=forms.Textarea, required=False)

        self.fields['sql'].help_text = u"说明：可提交select, show, set语句。查询最多返回500条记录。"
        self.fields['sql'].widget.attrs['class'] = 'full-width'

    def clean_sql(self):
        sql = self.cleaned_data['sql']
        if not sql:
            raise forms.ValidationError(u'这个字段是必须的')

        sql = sql.strip()
        if sql[-1] != ';':
            sql += ';'

        for s in sqlparse.split(sql):
            s = s.strip()
            first_word = s.split(None, 1)[0].lower()
            if first_word not in ['select', 'show', 'set']:
                raise forms.ValidationError(u"只能输入select, show, set语句。")

            if first_word == 'show' and 'explain' in self.request_.POST:
                raise forms.ValidationError(u"show语句不支持explain。")

        return sql


class CensorQueryForm(forms.ModelForm):
    def __init__(self, request, user, *args, **kwargs):
        super(CensorQueryForm, self).__init__(*args, **kwargs)
        self.request_ = request
        choices = DbInfo.objects.get_db_choices(user=user)
        choices = choices or [(0, '--选择数据库--'), ]
        self.fields['db'] = forms.ChoiceField(label=u"数据库", choices=choices)
        self.fields['reason'].widget.attrs['placeholder'] = '查询理由'
        self.fields['reason'].widget.attrs['class'] = 'reason-input'
        self.fields['reason'].widget.attrs['rows'] = '2'
        self.fields['sql'].help_text = u"说明：可提交select语句。查询返回大于十万条记录，需找DBA审核。"

    class Meta:
        model = ExecLog
        fields = ('db', 'reason', 'sql')

    def clean_db(self):
        dbid = self.cleaned_data['db']
        db = get_object_or_404(DbInfo, pk=dbid)
        return db

    def clean_reason(self):
        reason = self.cleaned_data['reason']
        if not reason:
            raise forms.ValidationError(u'查询理由必填')
        return reason

    def clean_sql(self):
        sql = self.cleaned_data['sql'].strip()
        if not sql:
            raise forms.ValidationError(u'这个字段是必须的')
        if sql[-1] != ';':
            sql += ';'

        for s in sqlparse.split(sql):
            s = s.strip()
            first_word = s.split(None, 1)[0].lower()
            if first_word not in ['select', 'show', 'set']:
                raise forms.ValidationError(u"只能输入select, show, set语句。")

        # 判断数据库权限
        is_superuser = self.request_.user.is_superuser
        permission = self.request_.session.get('permission', {})
        permission_db = self.request_.session.get('permission_db', {})
        explain = False
        db = self.cleaned_data['db']

        # 检查表权限
        exe = ExecuteSQL(db, sql, explain, is_superuser, permission_db, permission, limit=False)
        for sql_ in exe.sql_split():
            success, error = exe.check_sql(sql_)
            if not success:
                raise forms.ValidationError(error)
        exe.close_session()

        return sql


class DBSearchForm(forms.Form):
    ip = forms.CharField(max_length=64, required=False, widget=forms.TextInput(attrs={'class': 'input-small', 'placeholder': u'ip'}))
    db_name = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'class': 'input-small', 'placeholder': u'数据库名'}))


class DBConfigSearchForm(forms.Form):
    username = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'class': 'input-small', 'placeholder': u'用户ID'}))
