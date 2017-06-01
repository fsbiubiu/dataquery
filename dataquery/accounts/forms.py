# coding: utf-8
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm

from .models import Department, Info


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['placeholder'] = field.label


class CreateUserForm(UserCreationForm):
    department = forms.ChoiceField(label=u"部门", choices=Department.objects.get_all())

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.fields['department'].choices = Department.objects.get_all()

        for name, field in self.fields.items():
            # field.widget.attrs['class'] = 'am-form-field am-radius'
            if name == 'first_name':
                field.widget.attrs['placeholder'] = '昵称'
            else:
                field.widget.attrs['placeholder'] = field.label

    class Meta:
        model = User
        fields = ('username', 'first_name', 'department', 'is_superuser')

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if not first_name:
            raise forms.ValidationError(u'昵称必填项')
        return first_name

    def clean_username(self):
        forbidden_name = ['xxx']
        username = self.cleaned_data['username']
        for name in forbidden_name:
            if name in username:
                raise forms.ValidationError(u'该名字已被注册')
        return username

    def save(self, commit=True):
        user = super(CreateUserForm, self).save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        if commit:
            user.save()
        info = Info(user=user, department_id=self.cleaned_data['department'])
        info.save()
        return user


class UserUpdateForm(forms.ModelForm):
    department = forms.ChoiceField(label=u"部门", choices=Department.objects.get_all())
    password1 = forms.CharField(label=u"密码", max_length=32, required=False, widget=forms.PasswordInput, help_text=u"不填不修改密码")

    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        self.fields['department'].choices = Department.objects.get_all()
        for name, field in self.fields.items():
            field.widget.attrs['placeholder'] = field.label

    class Meta:
        model = User
        fields = ('username', 'first_name', 'department', 'password1')

    def save(self, commit=True):
        user = super(UserUpdateForm, self).save(commit=False)
        pwd = self.cleaned_data['password1']
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


class DepartmentCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DepartmentCreateForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['placeholder'] = field.label

    class Meta:
        model = Department
        fields = ('name', )


class PasswordResetForm(forms.Form):
    username = forms.CharField(label=u"用户名", required=True, max_length=32, widget=forms.TextInput(attrs={'class': 'input-small', 'placeholder': u'用户名'}))
