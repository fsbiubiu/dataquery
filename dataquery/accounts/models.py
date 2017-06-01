# coding: utf-8
from django.db import models
from django.contrib.auth.models import User


class DepartmentManager(models.Manager):
    def get_all(self):
        """ 获取所有列表，用于选择
        """
        return Department.objects.filter(status=True).values_list('id', 'name').distinct()


class Department(models.Model):
    """ 部门
    """
    name = models.CharField('部门名称', max_length=20, unique=True)

    status = models.BooleanField("状态", default=True)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)

    objects = DepartmentManager()


class Info(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, verbose_name="department",)
