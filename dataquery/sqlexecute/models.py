# coding:utf-8
import re
import sys
import time
import traceback
import logging

import sqlparse
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from lib.sqlparser import Parser
from lib.db import encode_data, sql_connect, get_mysql_field_type

# warning编码问题
import MySQLdb
import warnings
warnings.filterwarnings('ignore', category=MySQLdb.Warning)


logger = logging.getLogger('django')


class ExecuteSQL(object):
    def __init__(self, db, sql, is_explain, is_superuser, permission_db, permission, limit=True, limit_num=50, page=1):
        """ 初始化"""
        self.db = db
        self.sql = sql
        self.is_explain = is_explain
        self.limit = limit
        self.limit_num = limit_num
        self.page = page
        self.is_superuser = is_superuser
        self.permission_db = permission_db
        self.permission = permission
        self.have_pagination = False

        self.session = sql_connect(db.get_db_connect_str(), encoding=db.get_encode_display())
        self.must_secret_columns = True
        if self.is_superuser or self.is_explain:
            self.must_secret_columns = False
        if str(self.db.pk) in self.permission_db and self.permission_db[str(self.db.pk)]['have_secret_columns']:
            self.must_secret_columns = False

    def sql_split(self):
        for s in sqlparse.split(self.sql):
            s = s.strip()
            if s[-1] != ';':
                s = s + ';'
            self.have_pagination = False
            if not self.limit:
                yield s
                continue
            # explain 不做限制
            if self.is_explain:
                s = "explain " + s
            elif s[:3].lower() == "set":
                pass
            else:
                # 数据限制显示35条 row_count OFFSET offset
                limit_list = [
                    r'[\s]+limit[\s]+(?P<min>\d+)[\s]*,[\s]*(?P<num>\d+)',
                    r'[\s]+limit[\s]+(?P<num>\d+)',
                    r'[\s]+LIMIT[\s]+(?P<min>\d+)[\s]*,[\s]*(?P<num>\d+)',
                    r'[\s]+LIMIT[\s]+(?P<num>\d+)',
                    r'[\s]+LIMIT[\s]+(?P<num>\d+)[\s]+OFFSET[\s]+(?P<min>\d+)',
                    r'[\s]+LIMIT[\s]+(?P<num>\d+)[\s]+offset[\s]+(?P<min>\d+)',
                    r'[\s]+limit[\s]+(?P<num>\d+)[\s]+OFFSET[\s]+(?P<min>\d+)',
                    r'[\s]+limit[\s]+(?P<num>\d+)[\s]+offset[\s]+(?P<min>\d+)',
                ]

                def func(m):
                    value = m.group('num')
                    self.have_pagination = False
                    try:
                        _min = m.group('min')
                    except:
                        _min = None

                    if int(value) > self.limit_num or int(value) < 0:
                        if _min is not None:
                            return ' LIMIT {}, {} ;'.format(_min, self.limit_num)
                        else:
                            return ' LIMIT {} ;'.format(self.limit_num)

                    if _min:
                        return ' LIMIT {}, {} ;'.format(_min, value)
                    else:
                        return ' LIMIT {} ;'.format(value)

                # for l in limit_list:
                #     pattern = re.compile(l)
                #     s = re.sub(pattern, func, s)

                if s[:6].lower() == "select":
                    self.have_pagination = True
                    for l in limit_list:
                        pattern = re.compile(l+r'[\s]*;[\s]*$')
                        s = re.sub(pattern, func, s)
                        if not self.have_pagination:
                            break

                    if self.have_pagination:
                        s = s[:-1] + " LIMIT {}, {};".format((self.page-1)*self.limit_num, self.limit_num)
            yield s

    def check_permission(self, tables):
        """ 检查是否有表权限"""
        # 判断一个db查询权限
        perms = self.permission.get(str(self.db.pk), [])
        for t in tables:
            if t not in perms:
                return False, t
        return True, ''

    def check_sql(self, sql):
        """ 检查是否拥有数据库表权限 """
        perms = self.permission.get(str(self.db.pk), [])
        if self.is_superuser or self.is_explain or sql[:3].lower() == "set":
            return True, u''

        try:
            self.parser = Parser(sql)
        except:
            logger.error(sql)
            logger.error(traceback.format_exc())
            return False, u"表权限查询失败，请检查是否有语法错误"

        # 拥有整个库权限
        if '__have_all__' in perms:
            return True, u''

        if sql[:6].lower() != "select":
            return True, u''

        try:
            tables = self.parser.tables
            if tables is None:
                logger.error(sql)
                return False, u"表权限查询失败，请检查是否有语法错误."
        except:
            logger.error(sql)
            logger.error(traceback.format_exc())
            return False, u"表权限查询失败，请检查是否有语法错误"

        success, table = self.check_permission(tables)
        if success:
            return True, u''
        else:
            logger.error(sql)
            logger.error(table)
            return False, u"您没有'{}'的查询权限".format(table)

    def get_secret_columns_idx(self, keys):
        # 从字段名找到别名相关的进行替换
        # 可能有找不到对应的表名
        secret_columns = ColumnsPermission.objects.get_columns(db=self.db, tables=self.parser.tables)
        secret_columns_set = set([name for l in secret_columns.values() for name in l])
        # 列名与表名对应关系
        columns_table = self.parser.columns_table
        # *的表名，找到所有表的加密字段
        asterisk_table = columns_table.get('*', [])
        secret_asterisk_column = [name for t in asterisk_table for name in secret_columns.get(t, [])]
        secret_columns_idx = []
        for idx, key in enumerate(keys):
            key_ = self.parser.alias.get(key, key)
            # case 语句，后边字段有别名会None。count(*)
            key = key_ or key
            if '.' in key:
                key = key.split('.')[-1].strip('`')
            # 如果在*table的加密column里，直接当做加密字段，可能有误加密
            # 如果查了两个表的相同名的字段，一个需要加密，一个不需要加密，就会都加密
            if key in secret_asterisk_column:
                secret_columns_idx.append(idx)
                continue
            table_name = columns_table.get(key, [])
            if not table_name or "UNKNOWN" in table_name:
                if key in secret_columns_set:
                    secret_columns_idx.append(idx)
                    continue
                else:
                    continue
            column_name_list = []
            for table_ in table_name:
                column_name_list += secret_columns.get(table_, [])
            if key in column_name_list:
                secret_columns_idx.append(idx)
        return secret_columns_idx

    def filter_blob_field(self, field_types):
        """ 过滤二进制字段"""
        return []
        field_type_dict = get_mysql_field_type()
        r = []
        for idx, t in enumerate(field_types):
            for k, v in field_type_dict.items():
                if v == t:
                    if 'BLOB' in k:
                        r.append(idx)
                    break
        return r

    def execute(self, sql):
        try:
            success, error = self.check_sql(sql)
            if not success:
                return {'error': error}
        except:
            logger.error(traceback.format_exc())
            error = u"SQL检查权限错误"
            return {'error': error}

        try:
            start_time_ = time.time()
            # print(repr(sql))
            data = self.session.execute(sql)
            # 执行时间 毫秒ms
            time_ = (time.time() - start_time_) * 1000

            if sql[:3].lower() == "set":
                return

            keys = data.keys()
            if not keys:
                count = data.rowcount
                return {'is_select': False, 'count': count}
            field_types = [elem[1] for elem in data.cursor.description]

            data = data.fetchall()
            count = len(data)
            if self.limit and count > self.limit_num:
                logger.error(u"条数大于限制")
                logger.error(sql)
                data = data[:self.limit_num]

            # 加密字段
            if self.must_secret_columns and sql[:6].lower() == "select":
                idxs = self.get_secret_columns_idx(keys)
            else:
                idxs = None
            # 二进制字段
            blob_idxs = self.filter_blob_field(field_types)
            data = encode_data(data, self.db.encode, idxs, blob_idxs)

            return {'is_select': True, 'keys': keys, 'data': data, 'count': count, 'time': time_, "have_pagination": self.have_pagination}
        except:
            logger.error(self.db.db_name)
            logger.error(sql)
            logger.error(traceback.format_exc())
            info = sys.exc_info()
            error = u"SQL执行错误：{}".format(info[1])
            error = re.sub(r'\d+\.\d+\.\d+\.\d+', 'localhost', error)
            return {'error': error}

    def close_session(self):
        self.session.close()


class DbInfoManager(models.Manager):
    def get_all_db(self):
        """ 获取所有db列表，用于选择
        """
        l = DbInfo.objects.filter(status=True).values_list('id', 'name').distinct()
        return sorted([(i[0], i[1]) for i in l], key=lambda x: x[1])

    def get_db_choices(self, user=None):
        """ 获取db的列表，用于选择框
        查询操作，需要权限
        """
        if user.is_superuser:
            return [(i.pk, i.name) for i in DbInfo.objects.filter(status=True)]
        l = DbPermission.objects.filter(user=user, status=True)
        if user:
            return [(i.db.pk, i.db.name) for i in l if i.db.status]
        else:
            return []


class DbInfo(models.Model):
    """
    数据库连接信息
    """
    DB_ENCODE_CHOICES = (
        (1, u'utf-8'),
        (2, u'latin1'),
    )
    READ_WRITE_CHOICES = (
        (1, '读'),
        (2, '写'),
    )
    name = models.CharField('别名', max_length=20, unique=True)
    ip = models.CharField('HOST', max_length=64)
    port = models.CharField('端口', max_length=8)
    db_name = models.CharField('数据库名', max_length=32)
    username = models.CharField('用户名', max_length=32)
    password = models.CharField('密码', max_length=128, blank=True, help_text=u"编辑的时候不填不更新密码")
    encode = models.IntegerField('数据库编码', choices=DB_ENCODE_CHOICES, default=1)

    status = models.BooleanField("状态", default=True)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)

    objects = DbInfoManager()

    def __unicode__(self):
        return self.db_name + "@" + self.ip

    def get_db_label(self):
        return self.db_name + "@" + self.ip

    def get_db_connect_str(self):
        """
        得到sqlalchemy的连接字符串
        """
        charset = 'utf8' if self.encode == 1 else 'latin1'
        return "mysql+mysqldb://{}:{}@{}:{}/{}?charset={}".format(self.username, self.password, self.ip, self.port, self.db_name, charset)

    def is_user_have_db_permission(self, user):
        """ 判断用户是否有执行该数据库的权限
        """
        if user.is_superuser:
            return True
        return DbPermission.objects.filter(db=self, user=user, status=True).exists()


class ExecLog(models.Model):
    """ 执行sql的记录 """

    STATUS_CHOICES = (
        (1, u'不需要审核'),
        (2, u'未审核'),
        (3, u'审核未通过'),
        (4, u'审核通过'),
        (5, u'删除'),
        (6, u'正在执行'),
        (7, u'正在执行'),
        (8, u'已下载'),
    )

    db = models.ForeignKey(DbInfo, verbose_name="db",)
    user = models.ForeignKey(User, verbose_name="user",)
    censor = models.ForeignKey(User, related_name='+', null=True, blank=True)
    censor_time = models.DateTimeField("审核时间", null=True)

    jobid = models.CharField('Jobid', max_length=100, blank=True)
    sql = models.TextField("SQL语句", blank=True)
    is_exec = models.BooleanField("是否执行", default=False)
    reason = models.TextField("申请理由", max_length=500, blank=True)
    result_count = models.IntegerField("结果条数", default=0)
    exec_time = models.FloatField("执行消耗时间", default=0)
    exec_datatime = models.DateTimeField("执行时间", null=True)

    status = models.IntegerField("状态", choices=STATUS_CHOICES, default=2)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ['-create_time']

    def censor_update(self, censor, status):
        """ censor 审核人
            status 状态
        """
        self.censor = censor
        self.status = status
        self.censor_time = timezone.now()
        self.save()


class DbPermissionManager(models.Manager):
    def get_user_perm(self, user):
        """ 获取用户的数据库权限
        """
        dbps = DbPermission.objects.filter(user=user, status=True)  # .values_list('id', flat=True)
        r = {}
        for dbp in dbps:
            # 拥有整个库权限
            if dbp.have_all:
                r[dbp] = ['__have_all__']
            else:
                r[dbp] = list(TablePermission.objects.filter(db_perm=dbp, status=True).values_list('table_name', flat=True))
        return r


class DbPermission(models.Model):
    """
    数据库的查询权限
    """
    db = models.ForeignKey(DbInfo, verbose_name="db",)
    user = models.ForeignKey(User, verbose_name="user",)
    have_all = models.BooleanField("拥有整个数据库权限", default=False)
    have_secret_columns = models.BooleanField("拥有查看加密字段权限", default=False)
    status = models.BooleanField("状态", default=True)

    objects = DbPermissionManager()

    def __unicode__(self):
        return u"{}".format(self.pk)


class TablePermissionManager(models.Manager):
    def get_user_tables(self, user, db):
        """ 获取用户的数据库权限
        """
        dbp = DbPermission.objects.filter(db=db, user=user, status=True).first()
        if dbp and dbp.have_all or user.is_superuser:
            return u'__have_all__'
        if not dbp:
            return []
        return list(self.filter(db_perm=dbp, status=True).values_list('table_name', flat=True))


class TablePermission(models.Model):
    """ 表的查询权限
    """
    db_perm = models.ForeignKey(DbPermission, verbose_name="db_perm",)
    table_name = models.CharField('表名', max_length=100)
    status = models.BooleanField("状态", default=True)

    objects = TablePermissionManager()

    def __unicode__(self):
        return self.table_name


class ColumnsPermissionManager(models.Manager):
    def get_columns(self, db, tables):
        """ 获取数据库相关表的加密字段
        """
        l = self.filter(db=db, table_name__in=tables, status=True).only('column_name', 'table_name')
        r = {}
        for i in l:
            if i.table_name not in r:
                r[i.table_name] = [i.column_name]
            else:
                r[i.table_name].append(i.column_name)
        return r


class ColumnsPermission(models.Model):
    """ 字段权限
        没有权限的人 能查询但是查看的时候数据加密
    """
    db = models.ForeignKey(DbInfo, verbose_name="db",)
    table_name = models.CharField('表名', max_length=100)
    column_name = models.CharField('列名', max_length=100)
    status = models.BooleanField("状态", default=True)

    objects = ColumnsPermissionManager()

    class Meta:
        ordering = ['db', 'table_name']

    def __unicode__(self):
        return u"{}-{}-{}".format(self.db, self.table_name, self.column_name)


class DbLog(models.Model):
    """
    操作数据库信息的日志
    """
    user = models.ForeignKey(User, verbose_name="user",)
    db = models.ForeignKey(DbInfo, verbose_name="db",)
    action = models.CharField('操作', max_length=500)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
