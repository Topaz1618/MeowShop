# -*- coding: utf-8 -*-
from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
from aliyunsdkcore.client import AcsClient
from config import ACCESS_KEY_ID, ACCESS_KEY_SECRET, REGION

acs_client = AcsClient(ACCESS_KEY_ID, ACCESS_KEY_SECRET, REGION)


def send_sms_format(business_id, phonenum, code):
    params = "{\"number\":\"%d\"}" % code
    sk = u"十二维度"  # u"mycard萌卡"
    code = "SMS_75820182"  # "SMS_75885044"
    return send_sms(business_id, phonenum, sk.encode('utf-8'), code, params)


def send_sms(business_id, phone_number, sign_name, template_code, template_param=None):
    smsRequest = SendSmsRequest.SendSmsRequest()
    smsRequest.set_TemplateCode(template_code)
    if template_param is not None:
        smsRequest.set_TemplateParam(template_param)

    smsRequest.set_OutId(business_id)
    smsRequest.set_SignName(sign_name)
    smsRequest.set_PhoneNumbers(phone_number)
    smsResponse = acs_client.do_action_with_exception(smsRequest)
    return smsResponse


def Shop_send_sms(sign_name, template_code, template_param=None):
    smsRequest = SendSmsRequest.SendSmsRequest()

    smsRequest.set_TemplateCode(template_code)
    if template_param is not None:
        smsRequest.set_TemplateParam(template_param)

    smsRequest.set_SignName(sign_name)
    smsResponse = acs_client.do_action_with_exception(smsRequest)
    return smsResponse


def Shop_send_sms_format(phonenum):
    params = "{\"name\":\"%s\"}" % phonenum
    sk = u"十二维度"  # u"mycard萌卡"
    code = "SMS_204297810"  # know nothing about this: "SMS_75885044" #saibo: SMS_204297810 # ori:SMS_75820182

    for i in range(3):
        Shop_send_sms(sk.encode('utf-8'), code, params)


