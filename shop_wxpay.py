# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import datetime
import xmltodict
import dicttoxml
import requests
import random
import string
from time import time
from dateutil.relativedelta import relativedelta

from code import PayError
from shop_enum import RechargeStatus
from order_extensions import update_order_status, update_transaction_status, update_user_info
# from extensions import store_pay_status, store_pay_success
from config import PACKAGE_LIST

url_wx_base = 'https://api.mch.weixin.qq.com/pay/'

url_unifiedorder = url_wx_base + 'unifiedorder'
url_orderquery = url_wx_base + 'orderquery'

userconf = {
    'appid': u'wx123',
    'mch_id': u'12344',
    'apikey': '5678',
    'callback': '1266',
}


def random_str(length):
    return ''.join(random.sample(string.ascii_letters + string.digits, length))


def create_sign(params):
    sendstr = create_send_str(params)
    sendstr = append_apikey(sendstr, userconf['apikey'])

    return create_sign_from_str(sendstr)


def check_response_sign(rdict):
    sign = rdict.pop('sign')
    sign_local = create_sign(rdict)

    return sign is not None and sign == sign_local


def check_response(response):
    content = response.content

    try:
        root = xmltodict.parse(content)
        data = root['xml']
    except:
        return {'errors': 'response parse error'}

    if check_response_sign(data) is False:
        return {'errors': 'response sign error'}

    if data['return_code'] != 'SUCCESS' or data['result_code'] != 'SUCCESS':
        data['errors'] = '%s: %s' % (data.get('err_code'),
                                     data.get('err_code_des'))
    return data


def request_wx_api(url, data):
    print('----------------')
    print('requst wx pay api: %s' % url)

    sign = create_sign(data)
    data['sign'] = sign

    xml = dicttoxml.dicttoxml(data, custom_root='xml', attr_type=False)
    try:
        raise Exception  # For test
        response = requests.post(url, data=xml)
    except Exception as e:
        print("!!!!!!!!Generate fake data: ", e)
        redict = {}

        if url == url_unifiedorder:
            redict['code_url'] = "weixin://wxpay/bizpayurl/up?pr=NwY5Mz9&groupid=00"
            redict['prepay_id'] = "wx201410272009395522657a690389285100"

        elif url == url_orderquery:
            redict['trade_state'] = "SUCCESS"
            redict['time_end'] = "20201230133525"
            redict['transaction_id'] = "1009660380201506130728806387"
        return redict
    else:
        # rdict removed root element 'xml'
        rdict = check_response(response)
        return rdict


def request_unifiedorder(goods_name, trade_id, userip, amount, discount):
    fee = float(amount) * float(discount)/100 if float(amount) > 0 else 1

    data = {
        'appid':  userconf['appid'],
        'attach': u'支付测试',
        'body': goods_name,
        'mch_id': userconf['mch_id'],
        'device_info': u'WEB',
        'nonce_str': random_str(22),
        'out_trade_no': trade_id,
        'total_fee': int(fee),
        'spbill_create_ip': userip,
        'notify_url': userconf['callback'],
        'trade_type': u'NATIVE',
        # 'product_id': recharge.package.pk,     # member id
    }

    result = request_wx_api(url_unifiedorder, data)
    return result


def request_orderquery(trade_id):
    data = {
        'appid': userconf['appid'],
        'mch_id': userconf['mch_id'],
        'out_trade_no': trade_id,
        'nonce_str': random_str(22)
    }

    result = request_wx_api(url_orderquery, data)
    return result


# --- private

def create_send_str(params):
    sortkey = sorted(params.keys())
    send_list = map(lambda v: '%s=%s' % (v, params[v]), sortkey)

    return '&'.join(send_list)


def append_apikey(sendstr, apikey):
    sendstr += '&key=%s' % apikey
    return sendstr


def create_sign_from_str(sendstr):
    print(hashlib.md5(sendstr.encode('utf-8')))
    sign = hashlib.md5(sendstr.encode('utf-8')).hexdigest().upper()
    return sign


def update_recharge_wx_info(username, trade_id, data):
    trade_state = data.get('trade_state')
    d = data.get('time_end')    # 支付完成时间

    # Todo: 开通后测试这里成功和不成功的时候是否能获取到end_time

    if d is None or trade_state is None:
        raise False

    end_time = d[0:4] + '-' + d[4:6] + '-' + \
                d[6:8] + ' ' + d[8:10] + ':' + d[10:12] + ':' + d[12:14]
    end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp()

    if trade_state != "SUCCESS":
        transaction_id = None
        is_completed = False
        close_time = ""
    else:
        transaction_id = data.get('transaction_id')
        is_completed = True
        close_time = time()
        update_user_info(username, trade_id)

    update_transaction_status(username, trade_id, trade_state, end_time, transaction_id, close_time, is_completed)
    update_order_status(username, trade_id, trade_state, end_time, close_time, is_completed)
