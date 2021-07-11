import json
import jwt
import math
import asyncio
from time import time, sleep


from base import BaseHandler
from code import TokenError, AuthError, ShopError, BaseError, DBError, PayError
from config import SECRET_KEY, PRODUCT_PAGE_LIMIT, MYHEART_PAGE_LIMIT, MYITEMS_PAGE_LIMIT, PACKAGE_LIST, PAGE_LIMIT, ZIP_LIMIT
from shop_enum import GoodsType
from shop_utils import auth_login_redirect, member_login_redirect, get_token_user, get_discount_price, get_discount, add_num, subtract_num, \
    async_member_login_redirect, admin_login_redirect, async_auth_login_redirect,  producer_login_redirect
from base_extensions import get_user_id
from order_extensions import check_is_member, get_personal_items    # Todo: 待修改
from shop_extensions import get_resource_total_counts, generate_feature_items, generate_zip_items, get_product_dict, \
    paging_goods_list, slice_product_data, get_myheart_list, add_my_heart, delete_my_heart, count_goods_type,  get_my_heart_num, \
    get_page_info, get_myitems_num, get_myitems_list, check_is_bought, get_total_num, get_user_info, get_goods_name, generate_component_list, \
    get_component_total_counts


def generate_start_end_point(page_num, page_limit, total):
    try:
        current_page = page_num if page_num is not None else 1
        page_limit = page_limit if page_limit is not None else total
        start = (current_page - 1) * page_limit
        end = total if page_limit * current_page > total else page_limit * current_page

        return start, end
    except Exception as e:
        raise ShopError("7008")


class CheckIsMemberHandler(BaseHandler):
    @auth_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            is_member = check_is_member(username)
            message = {'msg': is_member, 'error_code': '1000'}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class UserInfoHandler(BaseHandler):
    """ 用户信息接口 (目前只用来看会员到期日期 )"""
    @auth_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        # username = self.get_argument("username", None)
        data = get_user_info(username)
        self.render("user_info.html", data=data, username=username)

    @auth_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            data = get_user_info(username)
            message = {'msg': data, 'error_code': '1000'}

        except Exception as e:
            message = {'msg': " Unknow error", 'error_code': '1010'}

        self.write(message)


class AboutUsHandler(BaseHandler):
    def get(self):
        self.render("about_us.html")


class FeedbackHandler(BaseHandler):
    def get(self):
        self.render("feedback.html")


class CheckIsBoughtHandler(BaseHandler):
    """ 检查当前商品是否已经购买 """
    @async_auth_login_redirect
    async def post(self):
        try:
            goods_id = self.get_argument("goods_id", None)
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)
            is_bought = check_is_bought(uid, goods_id)

            message = {'msg': is_bought, 'error_code': "1000"}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        print("!!!!!!!!!!!!!1", message)
        self.write(message)


class NotifyPurchasedHandler(BaseHandler):
    """ 提示商品已购买接口 """
    def get(self):
        try:
            info = self.get_argument("info", None)
            back_button = self.get_argument("btn", None)
            goods_id = self.get_argument("goods_id", None)

            if goods_id is not None:
                goods_name = get_goods_name(goods_id)
                data = get_product_dict(goods_name)
                print("!!!!!!", goods_id, goods_name)
                return self.render("notify_purchased.html", error_message=info, btn=back_button, data=data)
            else:
                return self.render("error_page.html", error_message="未知商品 ID")

        except DBError as e:
            return self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print("!!!!", e)
            return self.render("error_page.html", error_message="Unknow Error")


class PayPageHandler(BaseHandler):
    """ 返回付款页面(所有支付方式通用) """
    @auth_login_redirect
    def get(self):
        print("data")
        goods_name = self.get_argument("goods_name", None)
        goods_price = self.get_argument("goods_price", None)
        is_recharge = self.get_argument("is_recharge", None)
        goods_id = self.get_argument("goods_id", None)

        is_recharge = True if is_recharge is not None else False
        data = {
            "goods_name": goods_name,
            "goods_price": goods_price,
            "is_recharge": is_recharge,
            "goods_id": goods_id,
        }
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)

        self.render("pay.html", data=data, is_recharge=is_recharge, username=username)


class PackageListHandler(BaseHandler):
    """ 套餐列表接口 """
    # @auth_login_redirect
    def get(self):
        print(PACKAGE_LIST)
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)

        if cookie_token is not None:
            username = get_token_user(cookie_token, token)
        else:
            username = None


        self.render("package_catalog.html", data=PACKAGE_LIST, username=username, get_discount=get_discount, get_discount_price=get_discount_price)

    def post(self):
        try:
            data = json.dumps(PACKAGE_LIST)
            message = {'msg': data, 'error_code': '1000'}
        except Exception as e:
            message = {'msg': "Unknow error", 'error_code': '1010'}

        self.write(message)


class FeatureListHandler(BaseHandler):
    """ 所有功能列表 """

    @producer_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")

            token = self.get_argument("Authorization", None)

            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)

            page_num = self.get_argument("page", None)

            if isinstance(page_num, str):
                page_num = int(page_num)

            total = get_resource_total_counts(GoodsType.FEATURE)
            total_page = math.ceil(total / ZIP_LIMIT)
            current_page = page_num if page_num is not None else 1
            start = (current_page - 1) * ZIP_LIMIT
            end = total if ZIP_LIMIT * current_page > total else ZIP_LIMIT * current_page
            page_info = {
                "start": start,
                "end": end,
                "limit": ZIP_LIMIT,
                "total_data": total,
                "current_page": current_page,
                "total_page": total_page,
            }

            data_list = generate_feature_items(uid, start, end)
            # data = json.dumps(data_list, ensure_ascii=False)
            # message = {'msg': data, 'error_code': '1000'}
            # print(data_list)
            self.render("feature_items.html", page_info=page_info, data=data_list, username=username, subtract=subtract_num, add=add_num)

        except BaseError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except AuthError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except ShopError as e:
            print("raise error. ", e)

            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow Error")

    @member_login_redirect
    def post(self):
        try:
            token = self.get_argument("Authorization", None)
            if token is None:
                raise TokenError("5000")
            token_dic = jwt.decode(token.encode(), SECRET_KEY)
            username = token_dic.get('phonenum')
            uid = get_user_id(username)

            page_num = self.get_argument("page_num", None)
            page_limit = self.get_argument("page_limit", None)

            if isinstance(page_num, str):
                page_num = int(page_num)

            if isinstance(page_limit, str):
                page_limit = int(page_limit)

            total = get_resource_total_counts(GoodsType.FEATURE)
            print("Data count: ", total)
            start, end = generate_start_end_point(page_num, page_limit, total)
            data_list = generate_feature_items(uid, start, end)
            data = json.dumps(data_list, ensure_ascii=False)
            message = {'msg': data, 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)

            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class ZipListHandler(BaseHandler):
    """ 所有Zip 列表 """

    @producer_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)

            page_num = self.get_argument("page", None)
            # page_limit = self.get_argument("page_limit", None)

            if isinstance(page_num, str):
                page_num = int(page_num)

            # if isinstance(page_limit, str):
            #     page_limit = int(page_limit)

            total = get_resource_total_counts(GoodsType.ZIP)
            total_page = math.ceil(total / ZIP_LIMIT)
            current_page = page_num if page_num is not None else 1
            start = (current_page - 1) * ZIP_LIMIT
            end = total if ZIP_LIMIT * current_page > total else ZIP_LIMIT * current_page
            # start, end = generate_start_end_point(page_num, PAGE_LIMIT, total)

            page_info = {
                "start": start,
                "end": end,
                "limit": ZIP_LIMIT,
                "total_data": total,
                "current_page": current_page,
                "total_page": total_page,
            }

            print("Data count: ", total)
            data_list = generate_zip_items(uid, start, end, is_admin=True)

            self.render("zip_items.html", page_info=page_info, data=data_list, username=username, subtract=subtract_num, add=add_num)

        except BaseError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except AuthError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except ShopError as e:
            print("raise error. ", e)

            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow Error")

    @member_login_redirect
    def post(self):
        try:
            token = self.get_argument("Authorization", None)
            if token is None:
                raise TokenError("5000")
            token_dic = jwt.decode(token.encode(), SECRET_KEY)
            username = token_dic.get('phonenum')
            uid = get_user_id(username)

            print(uid)

            page_num = self.get_argument("page_num", None)
            page_limit = self.get_argument("page_limit", None)

            if isinstance(page_num, str):
                page_num = int(page_num)

            if isinstance(page_limit, str):
                page_limit = int(page_limit)

            total = get_resource_total_counts(GoodsType.ZIP, uid)
            print("Data count: ", total)
            start, end = generate_start_end_point(page_num, page_limit, total)
            data_list = generate_zip_items(uid, start, end)
            data = json.dumps(data_list, ensure_ascii=False)
            print(data)
            message = {'msg': data, 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)

            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class ComponentListHandler(BaseHandler):
    # @async_member_login_redirect
    def get(self):
        """  """
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)

            menu = self.get_argument("menu", None)
            if menu is None:
                raise BaseError("1002")

            page_num = self.get_argument("page_num", None)
            page_limit = self.get_argument("page_limit", None)

            if isinstance(page_num, str):
                page_num = int(page_num)

            if isinstance(page_limit, str):
                page_limit = int(page_limit)

            total = get_component_total_counts(menu)
            start, end = generate_start_end_point(page_num, page_limit, total)
            data = generate_component_list(uid, menu, start, end)
            print(data)

            message = {'msg': data, 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)

            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class CountGoodsHandler(BaseHandler):
    def post(self):
        goods_count_list = count_goods_type()
        self.write(goods_count_list)


class StoreCatalogHandler(BaseHandler):
    """ 所有商品页面 """
    # @async_member_login_redirect
    async def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            print("!!!! ",cookie_token)

            if cookie_token is not None:
                username = get_token_user(cookie_token, token)
                uid = get_user_id(username)
            else:
                username = uid = None


            page = self.get_argument("page", None)
            is_sort = self.get_argument("sort", None)
            filter_list = self.get_argument("filter", None)

            if isinstance(page, str):
                page = int(page)

            current_page = page if page is not None else 1
            is_sort = is_sort if is_sort is not None else "0"
            filter_list = filter_list.split(" ") if filter_list is not None else ["All"]


            t0 = time()
            loop = asyncio.get_event_loop()
            group1 = await asyncio.gather(*[
                loop.run_in_executor(None, count_goods_type, ),  # 统计各类商品数量
                loop.run_in_executor(None, get_page_info, current_page, filter_list, is_sort, uid),  # 获取当前页数据
                # loop.run_in_executor(None, get_myheart_list, uid, True)  # 获取我的喜欢列表
            ])

            goods_count_list, page_info = group1

            print("All Step2: ", time(), time() - t0)

            self.render("store_catalog.html", username=username,  get_discount_price=get_discount_price,
                        page_info=page_info, add=add_num, subtract=subtract_num, goods_count_list=goods_count_list)

        except BaseError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except AuthError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except ShopError as e:
            print("raise error. ", e)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow Error")

    # @member_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            is_sort = self.get_argument("sort", None)
            filter_list = self.get_argument("filter", None)
            page_num = self.get_argument("page_num", None)
            page_limit = self.get_argument("page_limit", None)

            uid = get_user_id(username)

            if isinstance(page_num, str):
                page_num = int(page_num)

            if isinstance(page_limit, str):
                page_limit = int(page_limit)

            filter_list = filter_list.split(" ") if filter_list is not None else []
            is_filter = False if len(filter_list) == 0 else True
            is_sort = is_sort if is_sort is not None else "0"
            page_limit = PRODUCT_PAGE_LIMIT if page_limit is None else page_limit

            if is_filter:
                total = paging_goods_list(filter_list)
            else:
                total = get_total_num()

            start, end = generate_start_end_point(page_num, page_limit, total)

            goods_list = slice_product_data(start, end, is_sort, filter_list, uid, is_filter)

            message = {'msg': goods_list, 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class SingleProductHandler(BaseHandler):
    """ 商品详情页面 """
    @member_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)
            goods_name = self.get_argument("goods_name", None)
            goods_id = self.get_argument("goods_id", None)
            goods_price = self.get_argument("goods_price", None)
            base_data = {
                "goods_name": goods_name,
                "goods_id": goods_id,
                "goods_price": goods_price,
            }

            product_list = get_product_dict(goods_name, uid)
            data = product_list[0]
            # print(data)

            self.render("single_product.html", data=data, base_data=base_data, username=username, get_discount_price=get_discount_price)

        except BaseError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except AuthError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except ShopError as e:
            print("raise error. ", e)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow Error")

    def post(self):
        try:
            goods_name = self.get_argument("goods_name", None)
            print(goods_name)
            product_list = get_product_dict(goods_name)
            # data = product_list[0]
            # print(product_list)
            message = {'msg': product_list, 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class AddMyHeartHandler(BaseHandler):
    """ 增加删除物品 """

    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            # token = self.get_argument("Authorization", None)

            if cookie_token is None:
                raise TokenError("5000")

            token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            token_dic = jwt.decode(token.encode(), SECRET_KEY)
            username = token_dic.get('phonenum')
            print(f">> Current User: {username}")

            goods_id = self.get_argument("goods_id")
            add_my_heart(username, goods_id)
            print(">")
            message = {'msg': "successful", 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)

            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        print(message)
        self.write(message)


class DeleteMyHeartHandler(BaseHandler):
    """ 删除收藏物品 """

    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            # token = self.get_argument("Authorization", None)

            if cookie_token is None:
                raise TokenError("5000")

            token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            token_dic = jwt.decode(token.encode(), SECRET_KEY)
            username = token_dic.get('phonenum')
            print(f">> Current User: {username}")

            goods_id = self.get_argument("goods_id")
            delete_my_heart(username, goods_id)
            message = {'msg': "successful", 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)

            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class MyHeartItemsHandler(BaseHandler):
    """ 收藏物品 API"""
    @auth_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            page = self.get_argument("page", None)

            if isinstance(page, str):
                page = int(page)
            uid = get_user_id(username)

            current_page = page if page is not None else 1
            total_data = get_my_heart_num(uid)
            total_page = total_data / MYHEART_PAGE_LIMIT
            total_page = math.ceil(total_page)
            start = (current_page - 1) * MYHEART_PAGE_LIMIT
            end = total_data if MYHEART_PAGE_LIMIT * current_page > total_data else MYHEART_PAGE_LIMIT * current_page

            print("!!!!!!! ", total_data, total_page, start, end)
            data = get_myheart_list(uid, start, end)
            # goods_list = slice_product_data(start, end)

            page_info = {
                "start": start,
                "end": end,
                "limit": MYHEART_PAGE_LIMIT,
                "total_data": total_data,
                "current_page": current_page,
                "total_page": total_page,
            }

            self.render("my_heart.html", username=username, data=data, page_info=page_info, add=add_num, subtract=subtract_num, get_discount_price=get_discount_price )

        except BaseError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except AuthError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except ShopError as e:
            print("raise error. ", e)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow Error")

    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")

            if cookie_token is None:
                data = list()

            else:

                token = cookie_token

                if isinstance(token, bytes):
                    token = token.decode()

                token_dic = jwt.decode(token.encode(), SECRET_KEY)
                username = token_dic.get('phonenum')

                uid = get_user_id(username)
                start = 0
                end = 3

                data = get_myheart_list(uid, start, end)

            message = {'msg': data, 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            print("raise error. ", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)

class MyItemsHandler(BaseHandler):
    """ 获取当前用户所有物品: 购买物品, 自己上传的物品"""
    @auth_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)
            page = self.get_argument("page", None)

            if isinstance(page, str):
                page = int(page)

            current_page = page if page is not None else 1

            total_data = get_myitems_num(uid)
            total_page = total_data / MYITEMS_PAGE_LIMIT
            total_page = math.ceil(total_page)
            start = (current_page - 1) * MYITEMS_PAGE_LIMIT
            end = total_data if MYITEMS_PAGE_LIMIT * current_page > total_data else MYITEMS_PAGE_LIMIT * current_page

            print("!!!!!!! ", total_data, total_page, start, end)
            data = get_myitems_list(uid, start, end)
            # goods_list = slice_product_data(start, end)

            page_info = {
                "start": start,
                "end": end,
                "limit": MYITEMS_PAGE_LIMIT,
                "total_data": total_data,
                "current_page": current_page,
                "total_page": total_page,
            }

            self.render("my_items.html", username=username, data=data, page_info=page_info, add=add_num, subtract=subtract_num, get_discount_price=get_discount_price)

        except BaseError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except AuthError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            self.render("error_page.html", error_message=e.error_msg)

        except ShopError as e:
            print("raise error. ", e)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow Error")





class AllProductsHandler(BaseHandler):
    """ 所有物品接口(待废弃) """
    @auth_login_redirect
    def post(self):
        try:
            token = self.get_argument("Authorization", None)
            token_dic = jwt.decode(token.encode(), SECRET_KEY)
            username = token_dic.get('phonenum')
            # username = "15600803270"
            all_personal_items = get_personal_items(username)
            data = json.dumps(all_personal_items, ensure_ascii=False)

            print(data)
            message = {'msg': data, 'error_code': '1000'}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except PayError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)
