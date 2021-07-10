import asyncio
import random
import uuid
import json
import hmac
import hashlib
import re
from time import time, strftime, localtime
import aio_msgpack_rpc
import msgpack_numpy as m

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import BaseHandler
from models import ShopUser, ShopVerifyCode, conn_db
from order_extensions import check_is_related, remove_token
from code import AuthError, TokenError
from alimsg import send_sms_format
from config import SECRET, VERIFYCODE_TIMEOUT
from shop_utils import auth_login_redirect, create_token
from order_extensions import handsel_member

m.patch()


async def handle_video(step, file_path):
    host = 'localhost'
    port = 3000

    client = aio_msgpack_rpc.Client(*await asyncio.open_connection(host, port))
    if step == 1:
        result = await client.call('capture_video', file_path)
    else:
        result = await client.call('check_process', file_path)
    print(result)
    return result


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html", user='18310703270')
        return


class LogoutHandler(BaseHandler):
    def get(self):
        try:
            token = self.get_secure_cookie("token")
            if token is None:
                self.render("login.html")
                return

            if isinstance(token, bytes):
                token = token.decode()

            remove_token(token)
            self.clear_cookie("token")
            self.render("login.html")

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            message = {'msg': "Logout failed", 'error_code': '1010'}

            self.write(message)

    def post(self):
        try:
            token = self.get_argument("Authorization", None)

            if token is None or len(token) == 0:
                raise TokenError("5000")

            remove_token(token)
            self.clear_cookie("token")
            message = {'msg': "Logout successful. ", 'error_code': '1000'}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Logout failed", 'error_code': '1010'}

        self.write(message)


class LoginHandler(BaseHandler):
    def get(self):
        self.render('login.html')

    def post(self):
        try:
            session = conn_db()
            username = self.get_argument("phonenum", "")
            password = self.get_argument("password", "")
            is_browser = self.get_argument("is_browser", None)

            if username is None or len(username) == 0:
                raise AuthError("1003")

            if len(re.findall("1[3|4|5|6|7|8|9][0-9]{9}", username)) == 0:
                raise AuthError("1009")

            if password is None or len(password) == 0:
                raise AuthError("1003")

            pwd_verify = re.match(r'[A-Za-z0-9@#$%^&+=]{8,16}$', password)
            if pwd_verify is None:
                raise AuthError("1005")

            user_exists = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
            if user_exists is None:
                raise AuthError("1002")

            password = hmac.new(SECRET, password.encode(), hashlib.md5).hexdigest()

            user_status = session.query(ShopUser).filter(
                ShopUser.phonenum == username,
                ShopUser.password == password
            ).first()

            if user_status is None:
                session.close()
                raise AuthError("1004")

            remote_ip = self.get_client_ip()
            token = create_token(username, remote_ip)

            user_status.last_remote_ip = remote_ip
            user_status.is_expired = 0

            if user_status.access_times is None:
                user_status.access_times = 0

            user_status.access_times += 1

            session.add(user_status)
            session.commit()
            print("login token >>>>", token, username)
            # Shop_send_sms_format(username) # 消耗短信使用
            message = {
                'msg': {'token': token, 'username': username},
                'error_code': '1000'
            }

            session.close()
            self.clear_cookie("token")
            self.clear_cookie("username")
            self.set_secure_cookie("token", token, 3600)
            self.set_secure_cookie("a", "123456tcookie")
            self.set_cookie("username", username)

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("!!!!!!!!!!!! ", e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)


class RegisterHandler(BaseHandler):
    def get(self):
        self.render('register.html')

    def post(self):
        try:
            username = self.get_argument('email', None)
            password1 = self.get_argument('password1', None)
            password2 = self.get_argument('password2', None)
            # verifycode = self.get_argument('verifycode', None)

            if username is None or len(username) == 0:
                raise AuthError("1003")

            # if len(re.findall("1[3|4|5|6|7|8|9][0-9]{9}", username)) == 0:
            #     raise AuthError("1009")

            if len(re.findall("[^@]+@[^@]+\.[^@]+"), username) == 0:
                raise AuthError("1009")

            if password1 is None or len(password1) == 0:
                raise AuthError("1003")

            if password1 != password2:
                raise AuthError("1003")

            session = conn_db()
            user_exists = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
            if user_exists is not None:
                raise AuthError("1001")

            pwd_verify = re.match(r'[A-Za-z0-9@#$%^&+=]{8,16}$', password1)

            if pwd_verify is None:
                raise AuthError("1005")

            # For verification code
            # code_exists = session.query(ShopVerifyCode).filter(
            #     ShopVerifyCode.phonenum == username,
            #     ShopVerifyCode.code == verifycode
            # ).first()

            # if code_exists is None:
            #     raise AuthError("1006")

            # interval_status = (1 if time() - code_exists.store_time < VERIFYCODE_TIMEOUT else 0)
            #
            # if not interval_status:
            #     raise AuthError("1006")

            password = hmac.new(SECRET, password1.encode(), hashlib.md5).hexdigest()
            user = ShopUser(phonenum=username, password=password, access_times=0)
            session.add(user)
            session.commit()

            handsel_member(username)

            message = {
                'msg': 'register successful',
                'error_code': '1000'
            }

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print("!!!!!!!!!!!!!!!!!!!1", e)
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class VerifyCodeHandler(BaseHandler):
    def request_verifycode(self, phonenum):
        code = random.randint(100000, 999999)
        print("code", code)
        business_id = uuid.uuid1()
        smsResponse = send_sms_format(business_id, phonenum, code)
        res_dic = json.loads(smsResponse.decode())
        if res_dic.get("Code") != "OK":
            raise AuthError("1007")

        try:
            session = conn_db()
            verifycode = ShopVerifyCode(phonenum=phonenum, code=str(code), store_time=int(time()))
            session.add(verifycode)
            session.commit()
            session.close()
        except Exception as e:
            raise AuthError("1007")

    def post(self):
        try:
            phonenum = self.get_argument("phonenum", None)
            if phonenum is None or len(phonenum) == 0:
                raise AuthError("1008")  # 获取手机号失败

            if len(re.findall("1[3|4|5|6|7|8|9][0-9]{9}", phonenum)) == 0:
                raise AuthError("1009")

            self.request_verifycode(phonenum)

            message = {
                    'msg': 'The verify code has been sent.',
                    'error_code': '1000'
                }

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknow Error", 'error_code': '1010'}

        self.write(message)


class RestPasswordView(BaseHandler):
    def get(self):
        self.render('resetpwd.html', user=self.current_user)

    def post(self):
        try:
            username = self.get_argument('phonenum', '')
            password = self.get_argument('password', '')
            password2 = self.get_argument('password2', '')
            verifycode = self.get_argument('verifycode', '')
            session = conn_db()
            print(username, password, password2)

            if username is None or len(username) == 0:
                raise AuthError("1003")

            if password is None or len(password) == 0:
                raise AuthError("1003")

            if password != password2:
                raise AuthError("1003")

            pwd_verify = re.match(r'[A-Za-z0-9@#$%^&+=]{8,16}$', password)
            if pwd_verify is None:
                raise AuthError("1005")

            check_user = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
            if check_user is None:
                raise AuthError("1002")

            code_exists = session.query(ShopVerifyCode).filter(ShopVerifyCode.phonenum == username,
                                                                  ShopVerifyCode.code == verifycode).first()
            if code_exists is None:
                raise AuthError("1006")

            interval_status = (1 if time() - code_exists.store_time < VERIFYCODE_TIMEOUT else 0)
            if not interval_status:
                raise AuthError("1006")

            user_obj = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
            password = hmac.new(SECRET, password.encode(), hashlib.md5).hexdigest()
            user_obj.password = password
            session.commit()
            session.close()
            message = {
                'msg': 'reset password successful',
                'error_code': '1000',
            }

        except AuthError as e:
            message = {'msg':  e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        self.write(message)




