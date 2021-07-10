import random
import string
import os
import jwt
import math
from time import time, strftime, localtime
from datetime import datetime
from sqlalchemy import distinct, func

from shop_enum import PayChannel, MemberLevel, GoodsType
from shop_logger import asset_logger
from shop_utils import ts_to_string, string_to_ts, get_discount_price
from base_extensions import get_order_info
from shop_extensions import get_product_dict, generate_bought_list
from models import conn_db, ShopUser, ShopGoods, ShopOrder, WxPayTransaction, ShopMember, \
    ShopPersonalItems, ShopZipFiles, ShopFeatures, ShopSecondaryMenu, ShopMainMenu, ALiPayOrder, \
    WxPayOrder, FreeMemberOrder
from config import SECRET_KEY, PACKAGE_LIST, FREE_PACKAGE_NAME, ORDER_TIMEOUT_DURATION
from code import AuthError, PayError, DBError, TokenError, BaseError, ShopError
from base_extensions import get_user_id


# def string_to_ts(str_time):
#     try:
#         ts = time.mktime(time.strptime(str_time, "%Y-%m-%d %H:%M:%S"))
#         return ts
#     except ValueError as e:
#         print("Catch error: ", e)
#         return 0


# def get_discount_price(x, y):
#     if not isinstance(x, float):
#         x = float(x)
#
#     if not isinstance(y, float):
#         y = float(y)
#
#     num = x * (y / 100)
#     res = int(num) if math.modf(num)[0] == 0.0 else round(num, 2)
#
#     if math.modf(res)[0] == 0.0:
#         res = int(res)
#
#     return res


def remove_token(token):
    try:
        token_dic = jwt.decode(token.encode(), SECRET_KEY)
        token_phonenum = token_dic.get('phonenum')
        token_ip = token_dic.get('remote_ip')

    except Exception as e:
        raise TokenError("5004")

    session = conn_db()
    user_obj = session.query(ShopUser).filter(ShopUser.phonenum == token_phonenum).first()

    if user_obj is None:
        raise TokenError("5003")

    if user_obj.last_remote_ip != token_ip:
        raise TokenError("5002")

    if user_obj.is_expired == 0:
        user_obj.is_expired = 1

    session.commit()
    session.close()


def check_is_member(username):
    uid = get_user_id(username)
    session = conn_db()
    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
    ).first()

    if member_obj is None:
        member_grade = 0

    else:
        if member_obj.is_expired:
            member_grade = 0
        else:
            current_time = time()
            senior_expire_time = string_to_ts(member_obj.senior_expire_time) if member_obj.senior_expire_time is not None else 0
            junior_expire_time = string_to_ts(member_obj.junior_expire_time) if member_obj.junior_expire_time is not None else 0

            member_grade = member_obj.grade_type

            if member_obj.grade_type == 2:
                print("!!! 2")
                if current_time >= senior_expire_time:
                    member_obj.grade_type = 1
                    session.commit()
                    member_grade = 1

            if member_obj.grade_type == 1:
                if current_time >= junior_expire_time:
                    member_obj.grade_type = 0
                    member_obj.is_expired = 1
                    session.commit()
                    member_grade = 0

    session.close()
    return member_grade


def check_if_member_expired(ts, expire_time):
    is_expired = False if expire_time > ts else True
    return is_expired


def check_order_status(out_trade_no, channel):
    session = conn_db()

    # from Shop_utils import ForkedPdb; ForkedPdb().set_trace()
    if channel == PayChannel.ALIPAY.value:
        tparty_order_obj = session.query(ALiPayOrder).filter(
            ALiPayOrder.out_trade_no == out_trade_no,
        ).first()

    elif channel == PayChannel.WXPAY.value:
        tparty_order_obj = session.query(WxPayOrder).filter(
            WxPayOrder.out_trade_no == out_trade_no,
        ).first()

    if tparty_order_obj is None:
        session.close()
        raise ShopError("7000")

    tparty_order_id = tparty_order_obj.id
    order_obj = session.query(ShopOrder).filter(
            ShopOrder.tparty_order_id == tparty_order_id,
        ).first()

    if order_obj is None:
        session.close()
        raise ShopError("7001")

    if order_obj.trade_state == "TRADE_SUCCESS":
        session.close()
        return True
    else:
        return False


def get_item_discount(product_name, is_recharge):
    if is_recharge:
        package_info = PACKAGE_LIST.get(product_name)
        total_amount = package_info["Money"]
        discount = package_info["Discount"]
        # pay_amount = get_discount_price(total_amount, discount)
    else:
        data = get_product_dict(product_name)
        for product_info in data:
            total_amount = product_info.get("price")
            discount = product_info.get("discount")

    if not isinstance(total_amount, float):
        total_amount = float(total_amount)

    if not isinstance(discount, float):
        discount = float(discount)

    print("!!!!!!!!! ", total_amount, discount)

    pay_amount = get_discount_price(total_amount, discount)

    return total_amount, pay_amount, discount


def check_recharge_status(trade_id):
    session = conn_db()
    trade_obj = session.query(ShopOrder).filter(
        ShopOrder.trade_id == trade_id,
        ShopOrder.is_closed == 0,
    ).first()

    if trade_obj is None:
        raise DBError("4004")

    trade_state = trade_obj.trade_state
    session.commit()
    session.close()
    return trade_state


def get_goods_id(goods_name):
    session = conn_db()

    goods_obj = session.query(ShopGoods).filter(
        ShopGoods.goods_name == goods_name,
        ShopGoods.is_delete == 0
    ).first()

    if goods_obj is None:
        session.close()
        raise DBError("4004")
    goods_id = goods_obj.id

    session.close()
    return goods_id


def get_out_trade_no(order_id):
    session = conn_db()

    order_obj = session.query(ShopOrder).filter(
        ShopOrder.order_id == order_id,
        ShopOrder.is_deleted == 0
    ).first()

    if order_obj is None:
        session.close()
        raise DBError("4004")

    # Todo: need to add wxpay

    if order_obj.channel == 1:
        tparty_order_obj = session.query(ALiPayOrder).filter(
            ALiPayOrder.id == order_id,
        ).first()

        out_trade_no = tparty_order_obj.out_trade_no
    else:
        raise BaseError("1002")

    session.close()
    return out_trade_no


def create_member_record(user_id, package_name):
    package_info = PACKAGE_LIST.get(package_name)

    timestamp = time()
    purchase_type = package_info["member_grade"]
    purchase_times = package_info["Days"] * 60 * 60 * 24
    session = conn_db()
    member_obj = session.query(ShopMember).filter(ShopMember.uid == user_id).first()

    if member_obj is not None:

        member_obj.grade_type = 2
        member_obj.is_expired = False
        member_obj.recharge_time = ts_to_string(timestamp)

        senior_expire_ts = string_to_ts(member_obj.senior_expire_time) if \
            member_obj.senior_expire_time is not None else 0
        is_senior_expired = check_if_member_expired(timestamp, senior_expire_ts)
        new_senior_expired_time = senior_expire_ts + purchase_times if not \
            is_senior_expired else timestamp + purchase_times
        member_obj.senior_expire_time = ts_to_string(new_senior_expired_time)
        asset_logger.warning(f"\"USER PURCHASE MEMBERSHIP\"  [Uid:{user_id}] [Package name:{package_name}] "
                              f"[New expire time:{ts_to_string(new_senior_expired_time)}]")

    else:
        expire_str = ts_to_string(timestamp + purchase_times)
        if purchase_type == MemberLevel.SENIOR_MEMBER.value:
            new_member_record = ShopMember(
                uid=user_id,
                grade_type=purchase_type,
                senior_expire_time=expire_str,
            )
            asset_logger.warning(f"\"FREE MEMBERSHIP FOR NEW\"  [Uid:{user_id}]  [New expire time:{expire_str}]")
        else:
            print("purchase_type", purchase_type)
            session.close()
            raise BaseError("1002")

        session.add(new_member_record)

    session.commit()
    session.close()


def create_personal_items(uid, product_name, order_id):
    session = conn_db()

    goods_obj = session.query(ShopGoods).filter(
        ShopGoods.goods_name == product_name,
    ).first()

    if goods_obj is None:
        raise DBError("4004")

    goods_id = goods_obj.id

    personal_item_obj = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
        ShopPersonalItems.item_id == goods_id,
    ).first()
    if personal_item_obj is not None:
        raise DBError("4003")

    personal_items_record = ShopPersonalItems(
        uid=uid,
        item_id=goods_id,
        order_id=order_id,
    )
    asset_logger.warning(f"\"USER PURCHASES ITEMS\" [Uid:{uid}] [Product:{product_name}]")
    session.add(personal_items_record)
    session.commit()
    session.close()


def update_user_info(out_trade_no, product_name, channel=PayChannel.ALIPAY.value):
    session = conn_db()
    print("Update user items", out_trade_no, product_name)

    if channel == PayChannel.ALIPAY.value:
        tparty_order_obj = session.query(ALiPayOrder).filter(
            ALiPayOrder.out_trade_no == out_trade_no,
        ).first()

    elif channel == PayChannel.WXPAY.value:
        tparty_order_obj = session.query(WxPayOrder).filter(
            WxPayOrder.out_trade_no == out_trade_no,
        ).first()

    else:
        raise BaseError("1002")

    tparty_order_id = tparty_order_obj.id

    order_obj = session.query(ShopOrder).filter(
        ShopOrder.tparty_order_id == tparty_order_id,
    ).first()

    if order_obj is None:
        raise DBError("4004")

    is_recharge = order_obj.is_recharge
    uid = order_obj.user_id
    order_id = order_obj.id

    if is_recharge:
        create_member_record(uid, product_name)     # 更新会员信息

    else:
        create_personal_items(uid, product_name, order_id)        # 存储个人物品信息


def get_login_ip(phonenum):
    session = conn_db()
    last_remote_ip = session.query(ShopUser).filter(ShopUser.phonenum == phonenum).first().last_remote_ip
    session.close()
    return last_remote_ip




def check_is_related(user_id):
    session = conn_db()
    user_obj = session.query(ShopUser).filter(ShopUser.id == user_id).first()

    data = False
    if user_obj is not None:
        data = user_obj.phonenum

    session.close()

    return data


def generate_personal_items(feature_obj_list, zip_obj_list, data, user_id=None):
    session = conn_db()
    feature_bought_list = zip_bought_list = []
    if user_id is not None:
        feature_bought_list, zip_bought_list = generate_bought_list(user_id)

    for feature_obj in feature_obj_list:
        is_bought = True if feature_obj.id in feature_bought_list else False

        character_obj = session.query(ShopZipFiles).filter(
            ShopZipFiles.id == feature_obj.character_id,
        ).first()

        character = character_obj.zip_name
        if character.endswith(".zip"):
            character = character.split(".zip")[0]

        secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
            ShopSecondaryMenu.id == character_obj.parent_id,
        ).first()

        secondary_menu = secondary_menu_obj.name

        data["FeatureList"][feature_obj.feature_name] = {
            "Authority": feature_obj.is_common,
            "id": feature_obj.id,
            "secondary_menu": secondary_menu,
            "character": character,
            "feature_flag": feature_obj.feature_flag,
            "description": feature_obj.description,
            "create_time": str(feature_obj.create_time),
            "is_bought": is_bought,
        }

    for zip_obj in zip_obj_list:
        is_bought = True if zip_obj.id in zip_bought_list else False

        secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
            ShopSecondaryMenu.id == zip_obj.parent_id,
        ).first()
        secondary_menu = secondary_menu_obj.name

        main_menu_obj = session.query(ShopMainMenu).filter(
            ShopMainMenu.id == secondary_menu_obj.parent_id,
        ).first()

        main_menu = main_menu_obj.name

        data["ZipList"][zip_obj.zip_name] = {
            "id": zip_obj.id,
            "main_menu": main_menu,
            "secondary_menu": secondary_menu,
            # "parent_id": i.parent_id,
            "img_path": f"static/images/shop/{zip_obj.img_path}",
            "Authority": zip_obj.is_common,  # 0: 付费, 1: 免费 2: 会员付费
            "create_time": str(zip_obj.create_time),
            "description": zip_obj.description,
            "is_bought": is_bought,
        }


def get_personal_items(username):
    user_id = get_user_id(username)
    session = conn_db()
    data = {"FeatureList": {}, "ZipList": {}}
    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == user_id,
        ShopMember.is_expired == False,
    ).first()

    # 所有会员免费商品
    if member_obj is not None:
        feature_obj_list = session.query(ShopFeatures).filter(
                ShopFeatures.is_delete == False,
            ).all()

        zip_obj_list = session.query(ShopZipFiles).filter(
            ShopZipFiles.is_delete == False,
        ).all()

        generate_personal_items(feature_obj_list, zip_obj_list, data, user_id)
    return data


def get_purchased_items(username):
    session = conn_db()
    uid = get_user_id(username)
    # feature_bought_list, zip_bought_list = generate_bought_list(uid)
    data = {}

    personal_obj_list = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
    ).all()

    for personal_obj in personal_obj_list:
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.id == personal_obj.item_id,
        ).first()

        if goods_obj.feature_id is not None:
            img_path = "1.jpg"
        else:
            zip_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.id == personal_obj.item_id,
            ).first()
            img_path = zip_obj.img_path

        data[goods_obj.id] = {
            "goods_name": goods_obj.goods_name,
            "price": goods_obj.goods_price,
            "img_path": f"static/images/shop/{img_path}",
        }

    return data


def get_single_order(username, goods_id):
    session = conn_db()
    uid = get_user_id(username)
    personal_item = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
        ShopPersonalItems.item_id == goods_id,
    ).first()

    if personal_item is None:
        raise ShopError("7012")   # 此物品未购买

    order_id = personal_item.order_id

    order_obj_list = session.query(ShopOrder).filter(
        ShopOrder.id == order_id,
        ShopOrder.is_deleted == 0,
    ).all()

    data = get_order_info(order_obj_list, username,  uid)

    session.close()
    print(data)
    return data


def delete_order(order_id):
    session = conn_db()

    order_obj = session.query(ShopOrder).filter(
        ShopOrder.order_id == order_id,
        ShopOrder.is_deleted == False,
    ).first()
    if order_obj is None:
        raise DBError("4004")

    order_obj.is_deleted = True
    session.commit()
    session.close()


def close_order(order_id):
    session = conn_db()

    order_obj = session.query(ShopOrder).filter(
        ShopOrder.order_id == order_id,
        ShopOrder.is_deleted == False,
    ).first()
    if order_obj is None:
        session.close()
        raise DBError("4004")

    current_time = ts_to_string(time())
    order_obj.trade_state = "TRADE_CLOSED"
    order_obj.end_time = current_time
    order_obj.close_time = current_time
    session.commit()

    session.close()


def create_alipay_record(username, order_id, out_trade_no, product_name, money, pay_amount, is_recharge, channel=PayChannel.ALIPAY.value):
    session = conn_db()
    uid = get_user_id(username)

    alipay_record = ALiPayOrder(
        product_name=product_name,      # 如果是recharge
        out_trade_no=out_trade_no,
        trade_status="WaitPayment",     # 这个步骤存储总金额, 支付金额, 优惠金额
    )

    session.add(alipay_record)
    session.commit()

    alipay_id = alipay_record.id

    Shop_record = ShopOrder(      #
        user_id=uid,    # 如果是recharge
        tparty_order_id=alipay_id,
        order_id=order_id,
        amount=money,
        pay_amount=pay_amount,
        channel=channel,
        trade_state="WaitPayment",
        is_recharge=bool(is_recharge),
    )

    session.add(Shop_record)
    session.commit()
    session.close()


def update_alipay_record(out_trade_no, post_dict, from_query=False):
    session = conn_db()
    alipay_order_obj = session.query(ALiPayOrder).filter(
        ALiPayOrder.out_trade_no == out_trade_no,
    ).first()
    if alipay_order_obj is None:
        raise ShopError("7001")

    if alipay_order_obj.trade_status == "TRADE_SUCCESS":
        print(f"!!!! order {out_trade_no} access again")

    if alipay_order_obj.trade_status != "TRADE_SUCCESS":
        if from_query:
            gmt_payment = notify_time = post_dict.get("send_pay_date")
            product_name = alipay_order_obj.product_name

        else:
            gmt_payment = post_dict.get("gmt_payment")
            notify_time = post_dict.get("notify_time")
            product_name = post_dict.get("subject")

        alipay_order_obj.gmt_payment = gmt_payment
        alipay_order_obj.notify_time = notify_time

        alipay_id = alipay_order_obj.id

        Shop_order_obj = session.query(ShopOrder).filter(
            ShopOrder.tparty_order_id == alipay_id,
        ).first()

        if Shop_order_obj is None:
            raise ShopError("7000")

        Shop_order_obj.trade_state = post_dict.get("trade_status")
        Shop_order_obj.end_time = gmt_payment
        Shop_order_obj.close_time = ts_to_string(time())
        session.commit()

        update_user_info(out_trade_no, product_name)

        alipay_order_obj.trade_no = post_dict.get("trade_no")
        alipay_order_obj.total_amount = post_dict.get("total_amount")
        alipay_order_obj.receipt_amount = post_dict.get("receipt_amount")
        alipay_order_obj.buyer_pay_amount = post_dict.get("buyer_pay_amount")
        alipay_order_obj.trade_status = post_dict.get("trade_status")
        session.commit()

        session.close()


def check_receive_authority(uid):
    session = conn_db()

    free_member_obj = session.query(FreeMemberOrder).filter(
        FreeMemberOrder.uid == uid,
    ).first()

    if free_member_obj is not None:
        session.close()
        raise AuthError("1010")

    session.close()


def create_fake_order(uid, order_id, package_name):
    session = conn_db()

    free_member_order = FreeMemberOrder(
        uid=uid,    # 如果是recharge
    )
    session.add(free_member_order)
    session.commit()

    create_member_record(uid, package_name)
    free_order_id = free_member_order.id

    Shop_record = ShopOrder(
        user_id=uid,    # 如果是recharge
        tparty_order_id=free_order_id,
        order_id=order_id,
        amount="0",
        channel=PayChannel.Free.value,
        trade_state="TRADE_SUCCESS",
        is_recharge=True,
        end_time=ts_to_string(time()),
        close_time=ts_to_string(time()),
    )

    session.add(Shop_record)
    session.commit()
    session.close()


def handsel_member(username, package_name=None):
    if package_name is None:
        package_name = FREE_PACKAGE_NAME

    print("!!!!", package_name)

    order_id = str(strftime('%Y%m%d%H%M%S', localtime(time()))) + str(time()).replace('.', '')
    uid = get_user_id(username)
    # check_receive_authority(uid)
    create_fake_order(uid, order_id, package_name)


def get_product_info(goods_id):
    session = conn_db()
    product_obj = session.query(ShopGoods).filter(
        ShopGoods.id == goods_id,
    )
    if product_obj is not None:
        session.close()
        raise DBError("4004")

    res_dic = {}
    res_dic["amount"] = product_obj.goods_price
    res_dic["discount"] = product_obj.discount

    session.close()
    return res_dic


def create_order_record(trade_id, prepay_id, username, amount, code_url, goods_name, is_recharge):
    """ 微信支付部分 """
    session = conn_db()
    user_id = get_user_id(username)

    if not isinstance(is_recharge, bool):
        is_recharge = bool(is_recharge)

    package_name = goods_name if is_recharge else None
    goods_id = None if is_recharge else get_goods_id(goods_name)

    new_order_record = ShopOrder(
        user_id=user_id,
        goods_id=goods_id,
        package_name=package_name,
        trade_id=trade_id,
        channel=PayChannel.WXPAY.value,
        amount=amount,
        prepay_id=prepay_id,
        code_url=code_url,
        is_recharge=is_recharge,
    )

    session.add(new_order_record)
    session.commit()
    session.close()


def check_if_trade_exists(username, trade_id):
    """ 微信支付部分 """

    session = conn_db()

    user_obj = session.query(ShopUser).filter(
        ShopUser.phonenum == username,
    ).first()

    if user_obj is None:
        raise AuthError("1002")

    user_id = user_obj.id

    order_obj = session.query(ShopOrder).filter(
        ShopOrder.user_id == user_id,
        ShopOrder.trade_id == trade_id,
        ShopOrder.is_closed == False,
    ).first()

    if order_obj is None:
        session.close()
        return None

    order_id = order_obj.id
    session.close()
    return order_id


def update_order_status(username, trade_id, trade_state, end_time, close_time, is_completed):
    """ 微信支付部分 """

    session = conn_db()

    user_id = get_user_id(username)

    orade_obj = session.query(ShopOrder).filter(
        ShopOrder.user_id == user_id,
        ShopOrder.trade_id == trade_id,
        ShopOrder.is_completed == False,
        ShopOrder.is_closed == False,
    ).first()

    if orade_obj is None:
        raise DBError("4004")

    print(f"Trade status: {trade_state} End time: {end_time} Close time: {close_time}")
    orade_obj.trade_state = trade_state
    orade_obj.end_time = end_time
    orade_obj.close_time = close_time
    orade_obj.is_completed = is_completed

    session.commit()
    session.close()


def update_transaction_status(username, trade_id, trade_state, end_time, transaction_id, close_time, is_completed):
    """ 微信支付部分 """
    session = conn_db()
    user_id = get_user_id(username)

    trade_obj = session.query(ShopOrder).filter(
        ShopOrder.user_id == user_id,
        ShopOrder.trade_id == trade_id,
        ShopOrder.is_closed == False,
    ).first()

    if trade_obj is None:
        session.close()
        raise DBError("4004")

    trade_id = trade_obj.id
    recharge_status = 1 if trade_state == "SUCCESS" else 0
    transaction_record = WxPayTransaction(
        order_id=trade_id,
        transaction_id=transaction_id,
        recharge_status=recharge_status,
        end_time=end_time,
        close_time=close_time,
        is_completed=is_completed,
    )

    session.add(transaction_record)
    session.commit()
    session.close()






