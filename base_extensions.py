from time import time
from sqlalchemy import distinct, func

from code import AuthError, BaseError
from shop_enum import PayChannel
from config import ORDER_TIMEOUT_DURATION, FREE_PACKAGE_NAME
from shop_utils import string_to_ts, ts_to_string
from models import conn_db, ShopUser, ShopOrder, ALiPayOrder, WxPayOrder, FreeMemberOrder


def get_user_id(username):
    session = conn_db()
    user_obj = session.query(ShopUser).filter(
        ShopUser.phonenum == username,
    ).first()
    if user_obj is None:
        session.close()
        raise AuthError("1002")

    user_id = user_obj.id
    session.close()
    return user_id


def get_order_info(order_obj_list, owner=None, uid=None):
    data = {}
    current_time = time()
    session = conn_db()
    for order_obj in order_obj_list:
        if owner is None:
            user_obj = session.query(ShopUser).filter(
                ShopUser.id == order_obj.user_id
            ).first()
            if user_obj is not None:
                owner = user_obj.phonenum

        if order_obj.trade_state == "WaitPayment":
            create_time = string_to_ts(str(order_obj.create_time))
            if current_time - create_time > ORDER_TIMEOUT_DURATION:
                order_obj.trade_state = "TRADE_CLOSED"
                order_obj.close_time = ts_to_string(time())
                order_obj.end_time = ts_to_string(time())
                session.commit()

        tparty_order_id = order_obj.tparty_order_id
        channel = order_obj.channel

        if channel == PayChannel.ALIPAY.value:
            tparty_order_obj = session.query(ALiPayOrder).filter(
                ALiPayOrder.id == tparty_order_id
            ).first()
            if tparty_order_obj is not None:
                product_name = tparty_order_obj.product_name
                out_trade_no = tparty_order_obj.out_trade_no
                trade_no = tparty_order_obj.trade_no
                tparty_order_no = trade_no if trade_no is not None else out_trade_no

        elif channel == PayChannel.WXPAY.value:
            tparty_order_obj = session.query(WxPayOrder).filter(
                WxPayOrder.id == tparty_order_id
            ).first()
            product_name = tparty_order_obj.product_name
            tparty_order_no = tparty_order_obj.out_trade_no

        elif channel == PayChannel.Free.value:
            free_obj = session.query(FreeMemberOrder).filter(
                FreeMemberOrder.uid == uid
            ).first()
            if free_obj is not None:
                if free_obj.id == tparty_order_id:
                    product_name = FREE_PACKAGE_NAME
                else:
                    product_name = "Shop官方群申请领取会员"
            else:
                product_name = "Shop官方群申请领取会员"

            tparty_order_no = None

        else:
            session.close()
            raise BaseError("1002")

        amount = float(order_obj.amount) if order_obj.amount is not None else 0
        pay_amount = float(order_obj.pay_amount) if order_obj.pay_amount is not None else 0
        discounted_amount = amount - pay_amount

        data[order_obj.order_id] = {
            # "order_id": ,
            "owner":owner,
            "product_name": product_name,
            "out_trade_no": tparty_order_no,
            "channel": channel,
            "amount": '%.2f' % amount,
            "pay_amount": '%.2f' % pay_amount,
            "discounted_amount": '%.2f' % discounted_amount,
            "create_time": str(order_obj.create_time),
            "end_time": str(order_obj.end_time),
            "close_time": str(order_obj.close_time),
            "trade_state": order_obj.trade_state,
            "is_recharge": order_obj.is_recharge,
        }

    return data


def slice_order_data(start, end, username=None):
    session = conn_db()

    if username is None:
        uid = None
        order_obj_list = session.query(ShopOrder).filter(
            ShopOrder.is_deleted == 0,
        )[start:end]

    else:
        uid = get_user_id(username)
        order_obj_list = session.query(ShopOrder).filter(
            ShopOrder.user_id == uid,
            ShopOrder.is_deleted == 0,
        )[start:end]

    data = get_order_info(order_obj_list, username, uid)

    session.close()
    return data


def paging_order_list(username=None):
    session = conn_db()
    if username is None:
        total = session.query(func.count(distinct(ShopOrder.id))).filter(
            ShopOrder.is_deleted == 0,
        ).scalar()

    else:
        uid = get_user_id(username)
        print(f"Before: {time()}")
        total = session.query(func.count(distinct(ShopOrder.id))).filter(
            ShopOrder.user_id == uid,
            ShopOrder.is_deleted == 0,
        ).scalar()

    print(f"After: {time()} {total}")
    session.close()
    return total
