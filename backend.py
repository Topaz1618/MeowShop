import os
import re
import asyncio
import math

from models import ShopVideo, conn_db
from base import BaseHandler
from code import  BaseError, AuthError,  DBError, TokenError, ShopError
from shop_enum import CreateType, GetType, GoodsType
from config import PRODUCT_USER, REGISTER_USER_PAGE_LIMIT, PAGE_LIMIT, access_logfile
from shop_utils import producer_login_redirect,  admin_login_redirect, member_login_redirect, get_token_user, subtract_num, add_num
from shop_logger import asset_logger
from backend_utils import check_create_permissions, check_if_creatable
from base_extensions import get_user_id, paging_order_list, slice_order_data

from shop_extensions import get_page_info, get_product_dict
from backend_extensions import add_package_type, create_zip_file, get_resource_list, check_if_user_exists, create_internal_user,\
    create_feature, create_new_goods, delete_resource, get_secondary_menu, get_all_items, create_video_record, \
    get_video_list, check_is_admin, count_registered_user, count_internal_user,  get_registered_user_info, renewal_membership, \
    update_goods_info, get_internal_user_info, get_single_zip_info, get_single_feature_info, update_zip_info, update_feature_info, \
    delete_multi_resource, modify_user_permission, check_user_exists, get_bind_user_list, update_user_type, modify_record_permission, \
    get_record_right


class StatusHandler(BaseHandler):
    def x(self):

        old_users_list = list()
        access_count_list = dict()
        with open("user.txt", "r") as f:
            while True:
                data = f.readline()
                if not data:
                    break
                user, access_times = data.strip("\n").split(",")
                access_count_list[user] = access_times
                old_users_list.append(user)

        register_amount, usage_amount, today_usage_amount = count_registered_user(old_users_list)
        return register_amount, usage_amount, today_usage_amount, access_count_list

    async def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            if username not in PRODUCT_USER:
                raise TokenError("5008")

            page = self.get_argument("page", None)

            current_page = page if page is not None else 1
            if not isinstance(current_page, int):
                current_page = int(current_page)

            loop = asyncio.get_event_loop()
            res = await asyncio.gather(
                loop.run_in_executor(None, self.x, ),  # 统计各类商品数量
            )
            total_data, usage_amount, today_usage_amount, access_count_list = res[0]
            total_page = total_data / REGISTER_USER_PAGE_LIMIT
            total_page = math.ceil(total_page)
            start = (current_page - 1) * REGISTER_USER_PAGE_LIMIT
            end = total_data if REGISTER_USER_PAGE_LIMIT * current_page > total_data else REGISTER_USER_PAGE_LIMIT * current_page

            data = get_registered_user_info(start, end, access_count_list)

            page_info = {
                "start": start,
                "end": end,
                "total_data": total_data,
                "total_page": total_page,
                "limit": REGISTER_USER_PAGE_LIMIT,
                "current_page": current_page,
                "usage_amount": usage_amount,
                "today_usage_amount": today_usage_amount,
                # "avg_counts": avg_counts,
                # 'log_exists': log_exists,
                # "avg_time": use_time_avg,
            }
            self.render("status.html", username=username, data=data, page_info=page_info, add=add_num, subtract=subtract_num)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknown error")


class RenewalMemberHandler(BaseHandler):
    @member_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            if username not in PRODUCT_USER:
                raise TokenError("5008")

            self.render("renewal_membership.html", username=username)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknown error")

    @member_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            if username not in PRODUCT_USER:
                raise TokenError("5008")

            user = self.get_argument("username", None)
            duration = self.get_argument("duration", None)

            if duration is None:
                raise BaseError("1002")

            print(user, duration)

            data = renewal_membership(user, package_name=duration)
            asset_logger.warning(f"\"RENEWAL MEMBER\" [User:{user}] [Type:{duration}] [New expire time:{data['expire_time']}] [ADMIN:{username}]")

            message = {'msg': data, 'error_code': "1000"}
            print(message)
        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class ModifyUserPerHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            if username not in PRODUCT_USER:
                raise TokenError("5008")

            self.render("modify_user_per.html", username=username)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknown error")

    @producer_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            if username not in PRODUCT_USER:
                raise TokenError("5008")

            user = self.get_argument("username", None)
            permission = self.get_argument("permission", None)

            if permission is None:
                raise BaseError("1002")

            print(user, permission)

            # 修改用户权限

            data = modify_user_permission(user, permission)

            # asset_logger.warning(f"\"RENEWAL MEMBER\" [User:{user}] [Type:{duration}] [New expire time:{data['expire_time']}] [ADMIN:{username}]")

            message = {'msg': data, 'error_code': "1000"}
            print(message)
        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class CheckUserExistsHandler(BaseHandler):
    @producer_login_redirect
    def post(self):
        """ 检查是否存在用户 """
        try:
            username = self.get_argument("username", None)
            authority = self.get_argument("authority", None)

            if username is None:
                raise BaseError("1002")

            if authority is None:
                raise BaseError("1002")

            check_user_exists(username, authority)
            # check_user_authority(username, authority)

            message = {'msg': username, 'error_code': '1000'}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class GetBindUsersHandler(BaseHandler):
    @producer_login_redirect
    def post(self):
        try:
            resource_id = self.get_argument("resource_id", None)
            resource_type = self.get_argument("resource_type", None)
            if resource_id is None:
                raise BaseError("1002")

            if resource_type is None:
                raise BaseError("1002")

            if not isinstance(resource_type, int):
                resource_type = int(resource_type)

            if not isinstance(resource_id, int):
                resource_id = int(resource_id)

            user_list = get_bind_user_list(resource_id, resource_type)
            message = {'msg': user_list, 'error_code': '1000'}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class ModifyZipHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            modify_type = self.get_argument("rtype", None)
            resource_id = self.get_argument("rid", None)

            data = dict()

            if modify_type is not None:
                if not isinstance(modify_type, int):
                    modify_type = int(modify_type)

                if modify_type == 0:
                    data = get_single_zip_info(resource_id)

                if modify_type == 1:
                    data = get_single_feature_info(resource_id)

            basic_info = {
                "rtype": modify_type,
                "resource_id": resource_id,
            }

            self.render("modify_zip.html", basic_info=basic_info, data=data, username=username)
            # self.render("modify_guide.html", basic_info=basic_info, data=data, username=username)

        except BaseError as e:
            print("1005", e)
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            print("DBError", e, e.error_code)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:

            self.render("error_page.html", error_message="Unknown error")

    @producer_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            modify_type = self.get_argument("resource_type", None)
            resource_id = self.get_argument("resource_id", None)
            userlist = self.get_argument("user_list", None)

            resource_name = self.get_argument("resource_name", None)
            new_resource_name = self.get_argument("new_resource_name", None)
            menu_id = self.get_argument("menu_id", None)
            is_common = self.get_argument("is_paid", None)
            is_related_product = self.get_argument("is_related_product", None)
            # goods_id = self.get_argument("current_goods_id", None)
            main_menu_id = self.get_argument("main_menu_id", None)

            is_component = self.get_argument("is_component", None)
            print("all info:", username, modify_type, resource_id, resource_name, menu_id, is_common, is_component, main_menu_id, is_related_product, type(is_related_product), new_resource_name)

            if modify_type is None:
                raise BaseError("1001")

            if resource_id is None:
                raise BaseError("1001")

            if modify_type is None:
                raise BaseError("1001")

            if not isinstance(modify_type, int):
                modify_type = int(modify_type)

            if is_component is not None:
                if not isinstance(is_component, int):
                    is_component = int(is_component)

            if is_common is not None:
                if not isinstance(is_common, int):
                    is_common = int(is_common)

            print("resource type", modify_type)

            if modify_type != 0:
                raise BaseHandler("1002")

            if is_related_product is None:
                raise BaseError("1001")

            update_zip_info(resource_id, resource_name, menu_id, is_common, is_component, is_related_product, main_menu_id,  new_resource_name, userlist)

            message = {'msg': "Update successful", 'error_code': "1000"}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}
        self.write(message)


class ModifyFeatureHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            modify_type = self.get_argument("rtype", None)
            resource_id = self.get_argument("rid", None)

            data = dict()

            if modify_type is not None:
                if not isinstance(modify_type, int):
                    modify_type = int(modify_type)

                if modify_type == 0:
                    data = get_single_zip_info(resource_id)

                if modify_type == 1:
                    data = get_single_feature_info(resource_id)

            basic_info = {
                "rtype": modify_type,
                "resource_id": resource_id,
            }

            self.render("modify_feature.html", basic_info=basic_info, data=data, username=username)
            # self.render("modify_guide.html", basic_info=basic_info, data=data, username=username)

        except BaseError as e:
            print("1005", e)
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            print("DBError", e, e.error_code)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:

            self.render("error_page.html", error_message="Unknown error")

    @producer_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            modify_type = self.get_argument("resource_type", None)
            resource_id = self.get_argument("resource_id", None)
            userlist = self.get_argument("user_list", None)
            resource_name = self.get_argument("resource_name", None)
            menu_id = self.get_argument("menu_id", None)
            is_common = self.get_argument("is_paid", None)
            is_related_product = self.get_argument("is_related_product", None)
            goods_id = self.get_argument("current_goods_id", None)
            main_menu_id = self.get_argument("main_menu_id", None)

            is_component = self.get_argument("is_component", None)
            print("all info:", username, modify_type, resource_id, resource_name, menu_id, is_common, is_component, goods_id, main_menu_id, is_related_product, type(is_related_product))

            if modify_type is None:
                raise BaseError("1001")

            if resource_id is None:
                raise BaseError("1001")

            if modify_type is None:
                raise BaseError("1001")

            if not isinstance(modify_type, int):
                modify_type = int(modify_type)

            if is_component is not None:
                if not isinstance(is_component, int):
                    is_component = int(is_component)

            if is_common is not None:
                if not isinstance(is_common, int):
                    is_common = int(is_common)

            print("resource tytpe", modify_type)
            if modify_type == 0:
                if is_related_product is None:
                    raise BaseError("1001")

                update_zip_info(resource_id, resource_name, menu_id, is_common, is_component, is_related_product, main_menu_id, goods_id, userlist)

            if modify_type == 1:
                update_feature_info(resource_id, resource_name, menu_id, is_common)

            message = {'msg': "Update successful", 'error_code': "1000"}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}
        self.write(message)


class IncreaseUserHandler(BaseHandler):
    @member_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            if username not in PRODUCT_USER:
                raise TokenError("5008")

            self.render("increase_users.html", username=username)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknown error")

    @member_login_redirect
    def post(self):
        try:
            username = self.get_argument("username", None)
            password = self.get_argument("password", None)
            password1 = self.get_argument("password1", None)
            user_type = self.get_argument("user_type", None)
            print(">>>", username, password, password1)
            # 验证用户名， 密码， 密码是否正确， 存储用户， 自动申请会员 200 年， 完成返回1000
            if username is None or len(username) == 0:
                raise AuthError("1003")

            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            admin_user = get_token_user(cookie_token, token)
            if admin_user not in PRODUCT_USER:
                raise TokenError("5008")

            print(">>>>", user_type)

            if len(re.findall("1[3|4|5|6|7|8|9][0-9]{9}", username)) == 0:
                raise AuthError("1009")

            if password is None:
                raise AuthError("1003")

            if password1 != password1:
                raise AuthError("1003")

            check_if_user_exists(username)

            pwd_verify = re.match(r'[A-Za-z0-9@#$%^&+=]{8,16}$', password1)

            if pwd_verify is None:
                raise AuthError("1005")

            create_internal_user(username, password)
            data = renewal_membership(username, package_name="内部测试用户会员")
            update_user_type(username, user_type)
            message = {'msg': data, 'error_code': '1000'}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class ShowInternalUsersHandler(BaseHandler):

    @admin_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)

        page = self.get_argument("page", None)

        current_page = page if page is not None else 1
        if not isinstance(current_page, int):
            current_page = int(current_page)

        total_data = count_internal_user()

        total_page = total_data / REGISTER_USER_PAGE_LIMIT
        total_page = math.ceil(total_page)
        start = (current_page - 1) * REGISTER_USER_PAGE_LIMIT
        end = total_data if REGISTER_USER_PAGE_LIMIT * current_page > total_data else REGISTER_USER_PAGE_LIMIT * current_page

        data = get_internal_user_info(start, end)

        page_info = {
            "start": start,
            "end": end,
            "total_data": total_data,
            "total_page": total_page,
            "limit": REGISTER_USER_PAGE_LIMIT,
            "current_page": current_page,
        }
        self.render("show_internal_users.html", username=username, data=data, page_info=page_info, add=add_num, subtract=subtract_num)


class ModifyResourcesHandler(BaseHandler):
    @admin_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            modify_type = self.get_argument("rtype", None)
            resource_id = self.get_argument("rid", None)

            data = dict()

            if modify_type is not None:
                if not isinstance(modify_type, int):
                    modify_type = int(modify_type)

                if modify_type == 0:
                    data = get_single_zip_info(resource_id)

                if modify_type == 1:
                    data = get_single_feature_info(resource_id)

            basic_info = {
                "rtype": modify_type,
                "resource_id": resource_id,
            }

            # self.render("modify_resource.html", basic_info=basic_info, data=data, username=username)
            self.render("modify_guide.html", basic_info=basic_info, data=data, username=username)

        except BaseError as e:
            print("1005", e)
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            print("DBError", e, e.error_code)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:

            self.render("error_page.html", error_message="Unknown error")

    @producer_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            modify_type = self.get_argument("resource_type", None)
            resource_id = self.get_argument("resource_id", None)
            resource_name = self.get_argument("resource_name", None)
            menu_id = self.get_argument("menu_id", None)
            is_common = self.get_argument("is_paid", None)
            is_related_product = self.get_argument("is_related_product", None)
            goods_id = self.get_argument("current_goods_id", None)
            main_menu_id = self.get_argument("main_menu_id", None)
            userlist = self.get_argument("user_list", None)

            is_component = self.get_argument("is_component", None)
            print("all info:", username, modify_type, resource_id, resource_name, menu_id, is_common, is_component, goods_id, main_menu_id, is_related_product, type(is_related_product))

            if modify_type is None:
                raise BaseError("1001")

            if resource_id is None:
                raise BaseError("1001")

            if modify_type is None:
                raise BaseError("1001")

            if not isinstance(modify_type, int):
                modify_type = int(modify_type)

            if is_component is not None:
                if not isinstance(is_component, int):
                    is_component = int(is_component)

            if is_common is not None:
                if not isinstance(is_common, int):
                    is_common = int(is_common)

            print("resource tytpe", modify_type)
            if modify_type == 0:
                if is_related_product is None:
                    raise BaseError("1001")

                update_zip_info(resource_id, resource_name, menu_id, is_common, is_component, is_related_product, main_menu_id, goods_id, userlist)

            if modify_type == 1:
                update_feature_info(resource_id, resource_name, menu_id, is_common)

            message = {'msg': "Update successful", 'error_code': "1000"}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}
        self.write(message)


class CreateGuideHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        if username not in PRODUCT_USER:
            raise TokenError("5008")
        self.render("create_guide.html", username=username)


class BackendHandler(BaseHandler):
    @member_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            if username not in PRODUCT_USER:
                raise TokenError("5008")

            self.render("backend.html", username=username)

        except BaseError as e:
            print("1005", e)
            self.render("error_page.html", error_message=e.error_msg)

        except TokenError as e:
            print("1005", e)
            self.render("error_page.html", error_message=e.error_msg)

        except DBError as e:
            print("DBError", e, e.error_code)
            self.render("error_page.html", error_message=e.error_msg)

        except Exception as e:

            self.render("error_page.html", error_message="Unknown error")

    @admin_login_redirect
    def post(self):
        try:
            username = self.get_argument("username", None)
            if username is None:
                raise AuthError("1002")

            create_type = self.get_argument("create_type", None)
            if create_type is None:
                raise BaseError("1001")

            if not isinstance(create_type, int):
                create_type = int(create_type)

            is_admin = check_is_admin(username)
            if not is_admin:
                is_allowed = check_create_permissions(username, create_type)
                if not is_allowed:
                    raise BaseError("1005")

            print("Admin", is_admin)

            if create_type == CreateType.CREATE_SECONDARY_MENU.value:
                previous_type = self.get_argument("previous_type", None)
                new_type_name = self.get_argument("new_type_name", None)
                if previous_type is None:
                    raise BaseError("1000")
                print(">>>", previous_type, new_type_name)

                add_package_type(previous_type, new_type_name)
                message = {'msg': "Add package successful. ", 'error_code': '1000'}

            elif create_type == CreateType.GOODS.value:
                goods_name = self.get_argument("goods_name", None)
                goods_type = self.get_argument("goods_type", None)
                zip_id = self.get_argument("zip_id", None)
                feature_id = self.get_argument("feature_id", None)
                goods_price = self.get_argument("goods_price", None)
                discount = self.get_argument("discount", None)
                is_discount = self.get_argument("is_discount", None)
                short_desc = self.get_argument("short_desc", None)
                description = self.get_argument("description", None)
                goods_id = create_new_goods(goods_name, goods_type, zip_id, feature_id, goods_price, discount, short_desc, description, is_discount)
                message = {'msg': goods_id, 'error_code': '1000'}

            else:
                raise BaseError("1002")

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class CreateFeatureHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        # self.render("backend.html")
        self.render("create_feature.html", username=username)

    @producer_login_redirect
    def post(self):
        try:
            username = self.get_argument("username", None)
            if username is None:
                raise AuthError("1002")

            create_type = self.get_argument("create_type", None)
            if create_type is None:
                raise BaseError("1001")

            if not isinstance(create_type, int):
                create_type = int(create_type)

            is_admin = check_is_admin(username)
            if not is_admin:
                is_allowed = check_create_permissions(username, create_type)
                if not is_allowed:
                    raise BaseError("1005")

            print("Admin", is_admin)

            if create_type != CreateType.FEATURE.value:
                raise BaseError("1002")

            character_id = self.get_argument("character_id", None)
            feature_name = self.get_argument("feature_name", None)
            is_common = self.get_argument("is_common", None)
            feature_flag = self.get_argument("feature_flag", None)
            description = self.get_argument("description", None)
            feature_id = create_feature(character_id, feature_name, feature_flag, description, is_common, username)
            message = {'msg': feature_id, 'error_code': '1000'}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class CreateZipHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        # self.render("backend.html")
        self.render("create_zip.html", username=username)

    @producer_login_redirect
    def post(self):
        try:
            username = self.get_argument("username", None)
            if username is None:
                raise AuthError("1002")

            create_type = self.get_argument("create_type", None)
            if create_type is None:
                raise BaseError("1001")

            if not isinstance(create_type, int):
                create_type = int(create_type)

            is_admin = check_is_admin(username)
            if not is_admin:
                is_allowed = check_create_permissions(username, create_type)
                if not is_allowed:
                    raise BaseError("1005")

            print("Admin", is_admin, create_type)

            if create_type != CreateType.ZIP.value:
                raise BaseError("1002")

            parent_id = self.get_argument("parent_id", None)
            if not is_admin:
                check_if_creatable(parent_id)

            is_common = self.get_argument("is_common", None)
            description = self.get_argument("description", None)
            zip_name = self.get_argument('zip_name', None)
            img_name = self.get_argument("img_name", None)
            resource_name = self.get_argument("resource_name", None)
            is_component = self.get_argument("is_component", None)
            userlist = self.get_argument("userlist", None)
            print("!!!!!!!!!!!!!!!!!", userlist)
            print("wtf ", parent_id, resource_name, zip_name, img_name,  is_common, is_component, description, userlist)
            create_zip_file(parent_id, resource_name, zip_name, img_name,  is_common, is_component, description, username, userlist)
            message = {'msg': "Add successful", 'error_code': '1000'}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class CreateVideoHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        # self.render("backend.html")
        self.render("create_video.html", username=username)

    @producer_login_redirect
    def post(self):
        try:
            username = self.get_argument("username", None)
            if username is None:
                raise AuthError("1002")

            create_type = self.get_argument("create_type", None)
            if create_type is None:
                raise BaseError("1001")

            if not isinstance(create_type, int):
                create_type = int(create_type)

            is_admin = check_is_admin(username)
            if not is_admin:
                is_allowed = check_create_permissions(username, create_type)
                if not is_allowed:
                    raise BaseError("1005")

            print("Admin", is_admin)

            if create_type == CreateType.CREATE_SECONDARY_MENU.value:
                previous_type = self.get_argument("previous_type", None)
                new_type_name = self.get_argument("new_type_name", None)
                if previous_type is None:
                    raise BaseError("1000")
                print(">>>", previous_type, new_type_name)

                add_package_type(previous_type, new_type_name)
                message = {'msg': "Add package successful. ", 'error_code': '1000'}

            if create_type != CreateType.VIDEO.value:
                raise BaseError("1002")

            view_title = self.get_argument("view_title", None)
            view_version = self.get_argument("view_version", None)
            view_desc = self.get_argument("view_desc", None)
            file_name = self.get_argument('video_name', None)
            img_name = self.get_argument("img_name", None)
            bind_type = self.get_argument("bind_type", None)            # 0: zip_id 1: featue_id
            bind_id = self.get_argument("bind_id", None)

            create_video_record(file_name, img_name, view_title, view_version, view_desc, bind_type, bind_id)
            message = {'msg': "Create successful", 'error_code': '1000'}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class ManagerMenuHandler(BaseHandler):
    """ 管理菜单 """
    @admin_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        self.render("menu_items.html",  username=username)


class CreateGoodsHanler(BaseHandler):
    """ 创建商品 """
    @admin_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)

        self.render("create_goods.html",  username=username)

    @admin_login_redirect
    def post(self):
        try:
            goods_id = self.get_argument('goods_id', None)
            if goods_id is None:
                raise BaseError("1002")

            is_discount = self.get_argument("is_discount", None)
            if is_discount is None:
                raise BaseError("1002")

            goods_name = self.get_argument('goods_name', None)
            price = self.get_argument('price', None)
            discount = self.get_argument('discount', None)
            short_desc = self.get_argument('short_desc', None)
            product_desc = self.get_argument('product_desc', None)
            print(goods_id, goods_name, price, discount, short_desc, product_desc)
            update_goods_info(goods_id, goods_name, price, discount, short_desc, product_desc, is_discount)
            message = {'msg': 'Update successful. ', 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}
        self.write(message)


class UpdateGoodsHanler(BaseHandler):
    @admin_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        goods_name = self.get_argument("goods_name", None)
        data = None
        if goods_name is not None:
            data = get_product_dict(goods_name)

        self.render("modify_goods.html",  username=username, data=data)

    @admin_login_redirect
    def post(self):
        try:
            goods_id = self.get_argument('goods_id', None)
            if goods_id is None:
                raise BaseError("1002")

            is_discount = self.get_argument("is_discount", None)
            if is_discount is None:
                raise BaseError("1002")

            goods_name = self.get_argument('goods_name', None)
            price = self.get_argument('price', None)
            discount = self.get_argument('discount', None)
            short_desc = self.get_argument('short_desc', None)
            product_desc = self.get_argument('product_desc', None)
            print("!!!!!! ", goods_id, goods_name, price, discount, short_desc, product_desc, is_discount)
            update_goods_info(goods_id, goods_name, price, discount, short_desc, product_desc, is_discount)
            message = {'msg': 'Update successful. ', 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}
        self.write(message)


class ManagerResources(BaseHandler):
    """ 删除资源 """
    @admin_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        data = get_all_items()

        self.render("batch_deletion.html", username=username, data=data)

    @admin_login_redirect
    def post(self):
        try:
            resource_type = self.get_argument("resource_type", None)
            resource_id = self.get_argument("resource_id", None)
            is_multi = self.get_argument("is_multi", None)
            # resource_list = self.get_arguments("resource_list", None)

            print("resource_type", resource_type, resource_id)
            if is_multi is not None:
                data = delete_multi_resource(resource_type, resource_id)
                if len(data) == 0:
                    message = {'msg': 'Delete resource successful. ', 'error_code': '1000'}
                else:
                    message = {'msg': f'Delete failed, current resource {str(data)} has been bound. ', 'error_code': '1000'}
            else:
                delete_resource(resource_type, resource_id)
                message = {'msg': 'Delete resource successful. ', 'error_code': '1000'}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class GetResourceHandler(BaseHandler):
    """ 获取所有资源 """
    @producer_login_redirect
    def post(self):
        try:
            # from Shop_utils import ForkedPdb; ForkedPdb().set_trace()
            resource_type = self.get_argument("resource_type", "")
            print(">>>>", resource_type)

            if len(resource_type) == 0:
                raise BaseError("1001")

            if not isinstance(resource_type, int):
                resource_type = int(resource_type)

            if resource_type == GetType.DEFAULT.value:
                data = get_all_items()

            elif resource_type == GetType.MAIN_MENU.value:
                menu_id = self.get_argument("menu_id", "")
                print("menu id", menu_id)
                if len(menu_id) == 0:
                    raise BaseError("1001")
                data = get_secondary_menu(menu_id)

            elif resource_type == GetType.RESOURCES.value:
                resource_id = self.get_argument("secondary_menu_id", "")
                if len(resource_id) == 0:
                    raise BaseError("1001")
                data = get_resource_list(resource_id)

            else:
                raise BaseError("1002")

            print(data)
            message = {'msg': data, 'error_code': "1000"}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("E:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class SingleResourceHandler(BaseHandler):
    @producer_login_redirect
    def post(self):
        try:
            resource_type = self.get_argument("resource_type", None)
            resource_id = self.get_argument("resource_id", None)
            resource_name = self.get_argument("resource_name", None)

            print("!!!!", resource_type, resource_id, type(resource_id), resource_name)

            if resource_type is None:
                raise BaseError("1001")

            if resource_name is None:
                raise BaseError("1001")

            if resource_id is not None:
                if not isinstance(resource_id, int):
                    if isinstance(resource_id, str) and resource_id == "null":
                        resource_id = None
                    else:
                        resource_id = int(resource_id)

            if not isinstance(resource_type, int):
                resource_type = int(resource_type)

            data = dict()
            if resource_type == 0:
                data = get_single_zip_info(resource_id, resource_name)

            elif resource_type == 1:
                data = get_single_feature_info(resource_id, resource_name)
            print(data)

            user_list = get_bind_user_list(resource_id, resource_type)

            message = {'msg': data, "user_list": user_list, 'error_code': "1000"}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except ShopError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        self.write(message)


class GetAllResourceHandler(BaseHandler):
    @admin_login_redirect
    def get(self):
        zip_list = list()
        feature_list = list()
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)

        self.render("all_resources.html", zip_list=zip_list, feature_list=feature_list, username=username)


class ManagerViewFilesHandler(BaseHandler):
    @admin_login_redirect
    def get(self):
        self.render("manager_view_videos.html")


class DeleteFileHandler(BaseHandler):
    @admin_login_redirect
    def post(self):
        video_id = self.get_argument("id", "")
        session = conn_db()
        video_obj = session.query(ShopVideo).filter(ShopVideo.id == video_id).first()
        video_obj.delete_status = 1
        session.commit()
        session.close()
        self.write({
            'msg': 'upload successful',
            'error_code': '1000'
        })


class GetVideoListHandler(BaseHandler):
    @admin_login_redirect
    def post(self):
        try:
            user = self.get_argument("username", None)
            data = get_video_list(user)
            message = {'msg': data, 'error_code': '1000'}
        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class ShowGoodsItemsHandler(BaseHandler):
    @admin_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            uid = get_user_id(username)

            page = self.get_argument("page", None)
            is_sort = self.get_argument("sort", None)
            filter_list = self.get_argument("filter", None)

            if isinstance(page, str):
                page = int(page)

            current_page = page if page is not None else 1
            is_sort = is_sort if is_sort is not None else "0"
            filter_list = filter_list.split(" ") if filter_list is not None else ["All"]

            page_info = get_page_info(current_page, filter_list, is_sort, uid)

            self.render("goods_items.html", username=username,  page_info=page_info, add=add_num, subtract=subtract_num)

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


class ShowOrdersHandler(BaseHandler):
    @admin_login_redirect
    def get(self):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        username = get_token_user(cookie_token, token)
        page = self.get_argument("page", None)
        if isinstance(page, str):
            page = int(page)

        current_page = page if page is not None else 1

        total = paging_order_list()

        total_page = total / PAGE_LIMIT
        total_page = math.ceil(total_page)

        start = (current_page - 1) * PAGE_LIMIT
        end = total if PAGE_LIMIT * current_page > total else PAGE_LIMIT * current_page

        order_list = slice_order_data(start, end)

        page_info = {
            "start": start,
            "end": end,
            "limit": PAGE_LIMIT,
            "total_data": total,
            "current_page": current_page,
            "total_page": total_page,
        }

        print(f"page_info: {page_info}")

        self.render("view_orders.html", data=order_list, order_length=len(order_list),
                    page_info=page_info, username=username, add=add_num, subtract=subtract_num)


class ModifyRecordPerHandler(BaseHandler):
    @producer_login_redirect
    def get(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            if username not in PRODUCT_USER:
                raise TokenError("5008")

            self.render("modify_record_permission.html", username=username)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknown error")

    @producer_login_redirect
    def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            if username not in PRODUCT_USER:
                raise TokenError("5008")

            user = self.get_argument("username", None)
            permission = self.get_argument("permission", None)

            if permission is None:
                raise BaseError("1002")

            print(user, permission)

            if not isinstance(permission, int):
                permission = int(permission)

            data = modify_record_permission(user, permission)

            # asset_logger.warning(f"\"RENEWAL MEMBER\" [User:{user}] [Type:{duration}] [New expire time:{data['expire_time']}] [ADMIN:{username}]")

            message = {'msg': data, 'error_code': "1000"}
            print(message)
        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class GetRecordPerHandler(BaseHandler):
    @member_login_redirect
    def get(self):
        try:

            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            data = get_record_right(username)

            message = {'msg': data, 'error_code': "1000"}

        except BaseError as e:
            print("1005", e)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except DBError as e:
            print("DBError", e, e.error_code)
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("Error:", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


