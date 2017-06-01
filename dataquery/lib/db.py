# coding: utf-8
import os.path
import csv
import datetime
from gzip import GzipFile
from io import BytesIO
from decimal import Decimal

import xlsxwriter
import sqlalchemy
import sqlalchemy.orm
from MySQLdb.constants import FIELD_TYPE
from django.http import HttpResponse
from django.conf import settings

from lib.util import utf8


def get_mysql_field_type():
    """ 获取mysql字段和对应的数值
    """
    r = {}
    for k, v in FIELD_TYPE.__dict__.items():
        if not k.startswith('__'):
            r[k] = v
    return r


def sql_connect(db_connect_str, encoding='utf-8'):
    engine = sqlalchemy.create_engine(db_connect_str, connect_args={'connect_timeout': 6},
                                      encoding=utf8(encoding), pool_recycle=150)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    session = Session()
    return session


def encode_data(data, encode, idxs=None, blob_idxs=None):
    """ 编码数据，idxs是加密字段的索引
    """
    r = []
    for row in data:
        l = []
        for idx, s in enumerate(row):
            if idxs and idx in idxs:
                s = "Secret Field"
            elif blob_idxs and idx in blob_idxs:
                s = "BLOB Field"
            elif isinstance(s, long):
                s = str(s)
            elif isinstance(s, unicode):
                pass
                # if encode == 1:
                #     s = s.encode('utf-8')
                # else:
                #     s = s.encode("latin1")
            elif isinstance(s, datetime.datetime):
                s = s.strftime("%Y-%m-%d %H:%M:%S.%f")
            elif isinstance(s, datetime.date):
                s = s.strftime("%Y-%m-%d")
            elif isinstance(s, Decimal):
                s = str(s)
            elif isinstance(s, datetime.time):
                s = str(s)
            elif isinstance(s, datetime.timedelta):
                s = str(s)

            l.append(s)
        r.append(l)
    return r


def get_tables(session, db_name, db_encode):
    """ 获取所有表名"""
    data = session.execute('''
        SELECT `table_name` FROM information_schema.tables WHERE `TABLE_SCHEMA`= :db_name;
        ''', {'db_name': db_name})
    data = data.fetchall()
    data = encode_data(data, db_encode)
    return [c[0] for c in data]


def get_columns(session, db_name, table_name, db_encode):
    """ 获取所有表名"""
    data = session.execute('''
        SELECT `COLUMN_NAME` AS `Field`
        FROM information_schema.columns
        WHERE `table_name`= :table_name and `TABLE_SCHEMA`= :db_name;
    ''', {'db_name': db_name, 'table_name': table_name})
    data = data.fetchall()
    data = encode_data(data, db_encode)
    return [c[0] for c in data]


def return_csv(data):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Encoding'] = 'gzip'
    response['Content-Disposition'] = 'attachment; filename="result.csv"'

    zbuf = BytesIO()
    zfile = GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
    # zfile.write(s)

    # writer = csv.writer(response)
    writer = csv.writer(zfile, quoting=csv.QUOTE_NONNUMERIC)
    for d in data:
        error = d.get('error', None)
        if error:
            writer.writerow(['error', utf8(error)])
        elif d['is_select']:
            writer.writerow(['count', d['count']])
            writer.writerow([utf8(k) for k in d['keys']])
            for row in d['data']:
                l = []
                for s in row:
                    l.append(utf8(s))
                writer.writerow(l)
            writer.writerow([])
        else:
            writer.writerow(['count', d['count']])
    zfile.close()
    response.write(zbuf.getvalue())
    return response


def return_excel(data):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;')
    response['Content-Encoding'] = 'gzip'
    response['Content-Disposition'] = 'attachment; filename="result.xlsx"'

    zbuf = BytesIO()
    zfile = GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
    # zfile.write(s)

    workbook = xlsxwriter.Workbook(zfile, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    row = 1
    col = 0
    for d in data:
        error = d.get('error', None)
        if error:
            worksheet.write_row(row, col, ['error', error])
        elif d['is_select']:
            worksheet.write_row(row, col, ['count', d['count']])
            row += 1
            worksheet.write_row(row, col, [k for k in d['keys']])
            row += 1
            for row_ in d['data']:
                l = []
                for s in row_:
                    l.append(s)
                worksheet.write_row(row, col, l)
                row += 1
            worksheet.write_row(row, col, [])
            row += 1
        else:
            worksheet.write_row(row, col, ['count', d['count']])
            row += 1
    workbook.close()
    zfile.close()
    response.write(zbuf.getvalue())
    return response


def save_excel(jobid, data):
    """ 保存成excel"""
    file_path = os.path.join(settings.BASE_DIR, 'static', 'excel', '{}.xlsx'.format(jobid))
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()
    row = 1
    col = 0
    for d in data:
        error = d.get('error', None)
        if error:
            worksheet.write_row(row, col, ['error', error])
        elif d['is_select']:
            worksheet.write_row(row, col, ['count', d['count']])
            row += 1
            worksheet.write_row(row, col, [k for k in d['keys']])
            row += 1
            for row_ in d['data']:
                l = []
                for s in row_:
                    l.append(s)
                worksheet.write_row(row, col, l)
                row += 1
            worksheet.write_row(row, col, [])
            row += 1
        else:
            worksheet.write_row(row, col, ['count', d['count']])
            row += 1
    workbook.close()
