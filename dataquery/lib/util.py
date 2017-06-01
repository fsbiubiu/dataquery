# coding: utf-8
import datetime
import decimal

import requests


def utf8(value):
    if isinstance(value, unicode):
        return value.encode("utf-8")

    elif isinstance(value, (bytes, type(None))):
        return value
    else:
        return value

    if not isinstance(value, unicode):
        print("Expected bytes, unicode, or None; got %r" % type(value))
        return ''


def conv_valid_json(data):
    """ 将一些数据改为合法的 JSON, 比如 日期
    """
    if isinstance(data, dict):
        for key in data:
            data[key] = conv_valid_json(data[key])

    if isinstance(data, (list, tuple)):
        data = [conv_valid_json(x) for x in data]

    if isinstance(data, datetime.datetime):
        data = data.strftime("%Y-%m-%d %H:%M:%S.%f")

    if isinstance(data, datetime.date):
        data = data.strftime("%Y-%m-%d")
    if isinstance(data, datetime.time):
        data = str(data)
    if isinstance(data, datetime.timedelta):
        data = str(data)

    if isinstance(data, decimal.Decimal):
        data = float(data)

    # IOS 端在遇到 null 值时会崩溃, 转换一下
    if data is None:
        data = ""

    return data


def send_mail(url, tos, title, html_content):
    """ 发送邮件"""
    try:
        requests.post(url, data={'subject': title, 'html_content': html_content, 'tos': tos})
    except:
        pass
