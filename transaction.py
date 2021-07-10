import os
import random
import string
import math
import asyncio
import time
from urllib.parse import parse_qs
import alipay as alipay_sdk


from base import BaseHandler
import shop_wxpay
from shop_alipay import AliPay
from shop_enum import RechargeStatus, PayChannel, PayStatus
from code import BaseError, PayError, AuthError, DBError, TokenError, ShopError
from config import PACKAGE_LIST,  APPID, SAPPID, APP_NOTIFY_URL, RETURN_URL, ALIPAY_PUBLIC_KEY_PATH, \
    APP_PRIVATE_KEY_PATH, ALIPAY_GATEWAY, SALIPAY_GATEWAY, PAGE_LIMIT
from shop_utils import create_qrcode, get_code_by_str,  member_login_redirect, admin_login_redirect, auth_login_redirect, \
    get_token_user, generate_order_id, add_num, subtract_num
from base_extensions import slice_order_data, paging_order_list
from order_extensions import create_order_record, check_if_trade_exists, check_recharge_status, create_alipay_record, \
    update_alipay_record, delete_order, close_order, check_order_status, get_item_discount, \
    get_single_order


# 订单管理
class OrderListHandler(BaseHandler):
    """ 订单列表接口 """

    @auth_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        page = self.get_argument("page", None)
        if isinstance(page, str):
            page = int(page)

        current_page = page if page is not None else 1

        total = paging_order_list(username)

        total_page = total / PAGE_LIMIT
        total_page = math.ceil(total_page)

        start = (current_page - 1) * PAGE_LIMIT
        end = total if PAGE_LIMIT * current_page > total else PAGE_LIMIT * current_page

        order_list = slice_order_data(start, end, username)

        page_info = {
            "start": start,
            "end": end,
            "limit": PAGE_LIMIT,
            "total_data": total,
            "current_page": current_page,
            "total_page": total_page,
        }

        print(f"page_info: {page_info}")

        self.render("order_catalog.html", data=order_list, order_length=len(order_list),
                    page_info=page_info, username=username, add=add_num, subtract=subtract_num)


class SingleOrderHandler(BaseHandler):
    @auth_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        print("username", username)

        goods_id = self.get_argument("goods_id", None)
        if goods_id is None:
            raise BaseError("1002")

        if not isinstance(goods_id, int):
            goods_id = int(goods_id)

        data = get_single_order(username, goods_id)
        self.render("single_order.html", data=data, username=username, add=add_num, subtract=subtract_num)


class QueryOrderHandler(BaseHandler):
    def query_order(self, Shop_alipay_sdk, out_trade_no):
        print("access query order")
        post_dict = Shop_alipay_sdk.api_alipay_trade_query(out_trade_no=out_trade_no)
        print("Res dict", post_dict)
        trade_status = post_dict.get("trade_status")

        if trade_status == "TRADE_SUCCESS":
            update_alipay_record(out_trade_no, post_dict, from_query=True)
            print("Update new status done. ")

    @auth_login_redirect
    async def get(self):
        try:
            out_trade_no = self.get_argument("out_trade_no", None)
            channel = self.get_argument("channel", None)
            if channel is None:
                channel = PayChannel.ALIPAY.value

            if out_trade_no is None:
                self.render("error_page.html", error_message="当前订单号不存在")

            page = self.get_argument("page", None)
            page_num = page if page is not None else 1

            alipay_public_key = open(ALIPAY_PUBLIC_KEY_PATH).read()
            app_private_key = open(APP_PRIVATE_KEY_PATH).read()

            Shop_alipay_sdk = alipay_sdk.AliPay(
                appid=APPID,
                app_notify_url=APP_NOTIFY_URL,
                alipay_public_key_string=alipay_public_key,
                app_private_key_string=app_private_key,
                sign_type="RSA2",
            )

            is_paid = check_order_status(out_trade_no, channel)
            print("Is Paid: ", is_paid)
            if not is_paid:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, self.query_order, Shop_alipay_sdk, out_trade_no)

            print("return. ")

        except BaseError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except DBError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except PayError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except ShopError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            message = {'msg': " Unknown error", 'error_code': '1010'}
            self.write(message)

        self.redirect(f"/order_list?page={page_num}")


class DeleteOrderHandler(BaseHandler):
    @auth_login_redirect
    def get(self):
        try:
            order_id = self.get_argument("order_no", None)
            if order_id is None:
                raise BaseError("1002")

            page = self.get_argument("page", None)
            page_num = page if page is not None else 1
            delete_order(order_id)

        except BaseError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except DBError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except PayError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            print("Error: ", e)
            message = {'msg': " Unknown error", 'error_code': '1010'}
            self.write(message)

        self.redirect(f"/order_list?page={page_num}")


class CloseOrderHandler(BaseHandler):
    @auth_login_redirect
    def get(self):
        try:
            order_id = self.get_argument("order_no", None)
            if order_id is None:
                raise BaseError("1001")

            page = self.get_argument("page", None)
            page_num = page if page is not None else 1
            close_order(order_id)

        except DBError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except PayError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            print("Error: ", e)
            message = {'msg': " Unknown error", 'error_code': '1010'}
            self.write(message)

        self.redirect(f"/order_list?page={page_num}")


# 支付宝支付
class ALiPayHandler(BaseHandler):
    """ 支付宝支付确认订单接口 """
    @auth_login_redirect
    def post(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)

        product_id = self.get_argument("product_id", None)
        product_name = self.get_argument("product_name", None)
        product_price = self.get_argument("product_price", None)
        is_recharge = self.get_argument("is_recharge", None)

        money = float(product_price)  # 保留俩位小数  前端传回的数
        order_id = generate_order_id()

        out_trade_no = ''.join(random.sample(order_id, 28))
        print(">>>", product_name, product_id, product_price, is_recharge, out_trade_no)
        debug = True
        # debug = False

        app_id = APPID if not debug else SAPPID
        total_amount, pay_amount, discount = get_item_discount(product_name, is_recharge)

        print(f"Product: {product_name} total amount: {total_amount} pay amount: {pay_amount} discount: {discount}")

        Shop_alipay = AliPay(
            appid=app_id,
            app_notify_url=APP_NOTIFY_URL,
            return_url=RETURN_URL,
            alipay_public_key_path=ALIPAY_PUBLIC_KEY_PATH,
            app_private_key_path=APP_PRIVATE_KEY_PATH,
            debug=debug,
        )

        query_params = Shop_alipay.direct_pay(
            subject=product_name,  # 商品简单描述 这里一般是从前端传过来的数据
            out_trade_no=out_trade_no,  # 商户订单号  这里一般是从前端传过来的数据
            total_amount=pay_amount,  # 交易金额(单位: 元 保留俩位小数)   这里一般是从前端传过来的数据
        )
        print("Generate access url: ", query_params)
        create_alipay_record(username, order_id, out_trade_no, product_name, total_amount, pay_amount, is_recharge)

        rpay_url = f"{ALIPAY_GATEWAY}?{query_params}"
        spay_url = f"{SALIPAY_GATEWAY}?{query_params}"
        pay_url = rpay_url if not debug else spay_url
        print("Pay url: ", pay_url)
        self.redirect(pay_url)


class PayAgainHandler(BaseHandler):
    """ 支付宝重新支付接口 """
    @auth_login_redirect
    def get(self):
        product_name = self.get_argument("product_name", None)
        trade_no = self.get_argument("trade_no", None)
        is_recharge = self.get_argument("is_recharge", None)

        # out_trade_no = "8011934046612025262374097031"
        # product_name = "女性角色基础套装"
        print("!!!!!!!!!!111", product_name, trade_no, is_recharge)
        if is_recharge is not None:
            is_recharge = False if is_recharge == "False" else True

        debug = True
        # debug = False

        app_id = APPID if not debug else SAPPID
        total_amount, pay_amount, discount = get_item_discount(product_name, is_recharge)

        Shop_alipay = AliPay(
            appid=app_id,
            app_notify_url=APP_NOTIFY_URL,
            return_url=RETURN_URL,
            alipay_public_key_path=ALIPAY_PUBLIC_KEY_PATH,
            app_private_key_path=APP_PRIVATE_KEY_PATH,
            debug=debug,
        )

        query_params = Shop_alipay.direct_pay(
            subject=product_name,  # 商品简单描述 这里一般是从前端传过来的数据
            out_trade_no=trade_no,  # 商户订单号  这里一般是从前端传过来的数据
            total_amount=pay_amount,  # 交易金额(单位: 元 保留俩位小数)   这里一般是从前端传过来的数据
        )

        rpay_url = f"{ALIPAY_GATEWAY}?{query_params}"
        spay_url = f"{SALIPAY_GATEWAY}?{query_params}"
        pay_url = rpay_url if not debug else spay_url
        print("Pay url: ", pay_url)
        self.redirect(pay_url)


class AliUpdateOrderHandler(BaseHandler):
    """ 支付宝支付成功后通知接口 """
    def post(self):
        body_str = self.request.body.decode('utf-8')
        post_data = parse_qs(body_str)
        post_dict = dict()
        for k, v in post_data.items():
            post_dict[k] = v[0]

        print("Post dict: ", post_dict)

        Shop_alipay = AliPay(
            appid=APPID,
            app_notify_url=APP_NOTIFY_URL,
            return_url=RETURN_URL,
            alipay_public_key_path=ALIPAY_PUBLIC_KEY_PATH,
            app_private_key_path=APP_PRIVATE_KEY_PATH,
            # debug=True,
        )

        sign = post_dict.pop('sign', None)
        status = Shop_alipay.verify(post_dict, sign)
        # status = 1
        if status:
            out_trade_no = post_dict.get('out_trade_no')
            print("Order id: ", out_trade_no)
            update_alipay_record(out_trade_no, post_dict)

            msg = PayStatus.SUCCESS.value     # Succesful
        else:
            msg = PayStatus.Fail.value          # Failed

        self.write(msg)


# 微信支付
class CreateTradeHandler(BaseHandler):
    """ 微信支付创建订单接口 """
    def post(self):
        try:
            username = self.get_argument("username", "")
            goods_name = self.get_argument("goods_name", "")
            amount = self.get_argument("amount", "")
            discount = self.get_argument("discount", "")
            is_recharge = self.get_argument("is_recharge", "")
            remote_ip = self.request.remote_ip

            if len(is_recharge) != 0:
                package_info = PACKAGE_LIST.get(goods_name)
                if package_info is None:
                    raise PayError("3001")

                if package_info["Money"] != int(amount):
                    raise PayError("3005")

            # 生成预支付订单
            trade_id = ''.join(random.sample(string.ascii_letters + string.digits, 20))
            response = shop_wxpay.request_unifiedorder(goods_name, trade_id, remote_ip, amount, discount)

            if not response:
                raise PayError("3001")

            response_error = response.get('errors')
            if response_error is not None:
                raise PayError("-2", response_error)

            code_url = response['code_url']
            prepay_id = response['prepay_id']

            # 新增订单记录
            create_order_record(trade_id, prepay_id, username, amount, code_url, goods_name, is_recharge)
            qrcode = create_qrcode(code_url, trade_id)

            message = {"msg": {"code": qrcode, "trade_id": trade_id}, "error_code": "1000"}

        except DBError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except PayError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error: ", e)
            message = {'msg': " Unknown error", 'error_code': '1010'}

        self.write(message)


class WechatPayCallback(BaseHandler):
    """ 微信支付回调接口 """
    def post(self):
        try:
            trade_id = self.get_argument("trade_id", "")
            response = shop_wxpay.request_orderquery(trade_id)

            if response.get('trade_state') == 'NOTPAY':
                raise PayError("-4", "NOTPAY")

            response_error = response.get('errors')
            if response_error is not None:
                raise PayError("-2", response_error)

            # Todo: 测试这里能否能获取到交易状态, 能得话业务逻辑操作放这里(交易记录,订单表, 会员, 个人物品表的更新) 放到这里

            recharge_status = check_recharge_status(trade_id)
            if recharge_status != RechargeStatus.SUCCESS.value:
                raise PayError("3003")

            message = {"msg": "Successful", "error_code": "1000"}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except PayError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': " Unknown error", 'error_code': '1010'}

        self.write(message)


class CheckOrderHandler(BaseHandler):
    """ 微信支付订单状态查询接口　"""
    def post(self):
        try:
            username = self.get_argument("username", "")
            trade_id = self.get_argument("trade_id", "")

            trade_exists = check_if_trade_exists(username, trade_id)
            if trade_exists is None:
                raise DBError("4004")

            response = shop_wxpay.request_orderquery(trade_id)
            response_error = response.get('errors')
            if response_error is not None:
                raise PayError("-2", response_error)

            # Todo: 开通后测试获取交易失败信息, 失败的也记录到数据库
            pay_status = shop_wxpay.update_recharge_wx_info(username, trade_id, response)

            if not pay_status:
                raise PayError("-4", "NOTPAY")

            message = {"msg": "ok", "error_code": "1000"}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except PayError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(">>>>", e)

            message = {'msg': " Unknown error", 'error_code': '1010'}

        self.write(message)


class CodeHandler(BaseHandler):
    """ 微信支付二维码接口 """
    def get(self):
        img_handler = get_code_by_str("http://127.0.0.1:8001/backend")
        print(img_handler.getvalue(), img_handler)
        self.write(img_handler.getvalue())




