# coding: utf-8
import ast
import json
import traceback
import time
from multiprocessing import Process
import logging

import redis

from django.template.loader import render_to_string
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings

from sqlexecute.models import ExecuteSQL, ExecLog
from lib.db import save_excel

logger = logging.getLogger('django')


def close_old_connections():
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()


def exec_dump(jobid, data):
    """ 执行sql"""
    if data.get('type') != 'query':
        return
    # r = redis.StrictRedis(host=settings.REDIS_SETTINGS['host'], port=settings.REDIS_SETTINGS['port'], db=0)

    close_old_connections()
    exelog = ExecLog.objects.get(pk=int(data['id']))
    exe = ExecuteSQL(exelog.db, exelog.sql, False, data['is_superuser'], data['permission_db'], data['permission'], limit=False)
    result_list = []
    result_count = 0
    exec_time = 0
    for sql_ in exe.sql_split():
        exec_result = exe.execute(sql_)
        if exec_result:
            result_count += exec_result.get('count', 0)
            exec_time += exec_result.get('time', 0)
            result_list.append(exec_result)
    exe.close_session()

    if exelog.status == 6 and result_count > 100000:
        # if exelog.status == 6 and result_count > 10:
        save_excel(jobid, result_list)

        exelog.status = 2
        exelog.is_exec = True
        exelog.exec_time = exec_time
        exelog.result_count = result_count
        exelog.exec_datatime = timezone.now()
        exelog.save()
        # r.setex("job:"+jobid, 7200, json.dumps({'success': False, 'msg': u'查询数据过多，请找DBA审核再查询'}))
        return
        # 发送提醒邮件
        # html_content = render_to_string('mail.html', {'request': self.request, 'query_log': self.object, 'url': reverse('censor_log_list')})
        # send_mail(settings.SEND_MAIL['url'], settings.SEND_MAIL['tos'], u'数据查询申请执行', html_content)

    save_excel(jobid, result_list)

    exelog.status = 7
    exelog.is_exec = True
    exelog.exec_time = exec_time
    exelog.result_count = result_count
    exelog.exec_datatime = timezone.now()
    exelog.save()
    # r.setex("job:"+jobid, 7200, json.dumps({'success': True, 'msg': u'查询成功', 'data': result_list}))
    return


class Command(BaseCommand):
    help = u'执行业务可用性检查'

    def handle(self, *args, **options):
        r = redis.StrictRedis(host=settings.REDIS_SETTINGS['host'], port=settings.REDIS_SETTINGS['port'], db=0)
        logger.info("exec_dump_sql Start:{}".format(time.time()))

        jobs = {}
        while 1:
            data = r.rpop('dataquery_dump_sql')
            if not data:
                time.sleep(0.5)
                continue

            data = ast.literal_eval(data)
            jobid = data.get('jobid')
            # query, cancel
            # 取消一个查询
            if data.get('type') == 'cancel':
                logger.info(u"cancel:{}".format(jobid))
                job = jobs.get(jobid)
                if job and job.is_alive():
                    jobs.pop(jobid)
                    job.terminate()

                r.delete(jobid)
                continue

            try:
                p = Process(target=exec_dump, args=[jobid, data])
                p.start()
                jobs[jobid] = p
            except:
                logger.error("dataquery_sqldump exec error")
                logger.error(traceback.format_exc())

        logger.info("exec_dump_sql Done:{}".format(time.time()))
