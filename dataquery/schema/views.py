# coding: utf-8
import logging
import traceback

from django.views.generic import View
from django.shortcuts import get_object_or_404, render

from sqlexecute.models import DbInfo
from lib.db import get_tables, encode_data, sql_connect

logger = logging.getLogger('django')


class SchemaView(View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        dbid = int(request.GET.get('dbid', 0))
        table_name = request.GET.get('table')
        dbs = DbInfo.objects.get_db_choices(user=self.request.user)
        context = {'table_name': table_name, 'dbid': dbid, 'dbs': dbs}

        if not dbs:
            return render(request, "schema/schema.html", context)
        if dbid and dbid not in [d[0] for d in dbs]:
            dbid = dbs[0][0]
        if not dbid:
            dbid = dbs[0][0]
        db = get_object_or_404(DbInfo, pk=dbid)

        session = sql_connect(db.get_db_connect_str(), encoding=db.get_encode_display())

        try:
            # 所有表
            context['tables'] = get_tables(session, db.db_name, db.encode)
            context['tables_count'] = len(context['tables'])

            # 表结构
            if table_name:
                data = session.execute("""SELECT `COLUMN_NAME` AS `Field`, `COLUMN_TYPE` AS `Type`, `COLUMN_KEY` AS `Key`,
                    `COLUMN_DEFAULT` AS `Default`, `COLUMN_COMMENT` AS `Comment`, `EXTRA`,
                    `CHARACTER_SET_NAME` AS `Encoding`, `IS_NULLABLE` AS `Allow_Null`, `COLLATION_NAME` AS `Collation`
                    FROM information_schema.columns
                    WHERE `table_name`= :table_name and `TABLE_SCHEMA`= :db_name;
                    """, {'table_name': table_name, 'db_name': db.db_name})
                context['keys'] = data.keys()
                data = data.fetchall()
                context['columns_count'] = len(data)
                context['data'] = encode_data(data, db.encode)
        except:
            logger.error(traceback.format_exc())
            context['tables'] = []

        return render(request, "schema/schema.html", context)
