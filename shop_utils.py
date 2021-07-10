import os
import sys
import io
import jwt
import pdb
import redis
import math
import json
import qrcode
import binascii
import hashlib
import time
from Crypto.PublicKey import RSA
from Crypto.Cipher import DES3, PKCS1_OAEP

from models import ShopUser, conn_db, ShopModelToken, ShopVideo, ShopMember
from config import SECRET_KEY, TOKEN_TIMEOUT, PRODUCT_PAGE_LIMIT, PRODUCT_USER, AUTOMATIC_GIVEAWAY_TIME
from code import TokenError, BaseError
from config import REDIS_HOST, DES_KEY


class ForkedPdb(pdb.Pdb):
    """ ForkedPdb().set_trace() """
    def interaction(self, *args, **kwargs):
        _stdin = sys.stdin
        try:
            sys.stdin = open('/dev/stdin')
            pdb.Pdb.interaction(self, *args, **kwargs)
        finally:
            sys.stdin = _stdin


def common_token_verification(remote_ip, token, is_admin=False, is_producer=False):
    token_dic = jwt.decode(token.encode(), SECRET_KEY)
    token_phonenum = token_dic.get('phonenum')
    token_ip = token_dic.get('remote_ip')

    current_time = time.time()
    if current_time - token_dic['timestamp'] > TOKEN_TIMEOUT:
        raise TokenError("5001")

    if remote_ip != token_ip:
        raise TokenError("5002")

    session = conn_db()
    user_obj = session.query(ShopUser).filter(ShopUser.phonenum == token_phonenum).first()

    if user_obj is None:
        session.close()
        raise TokenError("5003")

    if is_producer:
        if user_obj.is_admin != 1 and user_obj.phonenum not in PRODUCT_USER:
            session.close()
            raise TokenError("5003")

    if is_admin:
        if user_obj.is_admin != 1:
            raise TokenError("5008")

    if user_obj.last_remote_ip != token_ip:
        session.close()
        raise TokenError("5002")

    if user_obj.is_expired == 1:
        session.close()
        raise TokenError("5001")

    print("user_obj.access_times", user_obj.access_times)

    if user_obj.access_times is None:
        user_obj.access_times = 0

    user_obj.last_access_time = ts_to_string(current_time)
    uid = user_obj.id
    register_time = string_to_ts(user_obj.register_time)
    session.commit()
    session.close()

    return uid, register_time


def auth_login_redirect(func):
    def token_verification(remote_ip, token):
        common_token_verification(remote_ip, token)
        return True

    def inner(self, *args, **kwargs):
        token = self.get_argument("Authorization", None)

        if token is not None:
            if len(token) == 0:
                raise TokenError("5000")

        try:
            if not self.request.uri.startswith("/?"):
                uri_token = None
            else:
                uri_token_list = self.request.uri.strip("/?").split("=")
                uri_token = uri_token_list[-1] if len(uri_token_list) > 1 else None
        except:
            raise TokenError("5009")

        cookie_token = self.get_secure_cookie("token")

        try:
            if token is None:
                if uri_token is not None:
                    print("Use uri token")
                    self.clear_cookie("username")
                    self.set_secure_cookie("token", uri_token, 3600)
                    token = uri_token

                elif cookie_token is not None:
                    print("Use cookie token")
                    token = cookie_token

                else:
                    raise TokenError("5000")

            if isinstance(token, bytes):
                token = token.decode()

            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip

            token_verification(remote_ip, token)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)
            return

        except Exception as e:
            print("Auth token exception >>>> ", e)
            self.render("login.html")
            return

        func(self, *args, **kwargs)
    return inner


def producer_login_redirect(func):
    def token_verification(remote_ip, token):
        common_token_verification(remote_ip, token, is_producer=True)
        return True

    def inner(self, *args, **kwargs):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        try:
            if token is None or len(token) == 0:
                if cookie_token is None:
                    raise TokenError("5000")
                else:
                    print("Use cookie token")
                    token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip

            token_verification(remote_ip, token)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)
            return

        except Exception as e:
            print("Admin token exception >>>> ", e)
            self.render("login.html")
            return

        func(self, *args, **kwargs)
    return inner


def admin_login_redirect(func):
    def token_verification(remote_ip, token):
        common_token_verification(remote_ip, token, is_admin=True)
        return True

    def inner(self, *args, **kwargs):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        try:
            if token is None or len(token) == 0:
                if cookie_token is None:
                    raise TokenError("5000")
                else:
                    print("Use cookie token")
                    token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip

            token_verification(remote_ip, token)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)
            return

        except Exception as e:
            print("Admin token exception >>>> ", e)
            self.render("login.html")
            return

        func(self, *args, **kwargs)
    return inner


def async_admin_login_redirect(func):
    def token_verification(remote_ip, token):
        common_token_verification(remote_ip, token, is_admin=True)
        return True

    async def inner(self, *args, **kwargs):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        try:
            if token is None or len(token) == 0:
                if cookie_token is None:
                    raise TokenError("5000")
                else:
                    print("Use cookie token")
                    token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip

            token_verification(remote_ip, token)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)
            return

        except Exception as e:
            print("Admin token exception >>>> ", e)
            self.render("login.html")
            return

        await func(self, *args, **kwargs)
    return inner


def member_login_redirect(func):
    def token_verification(remote_ip, token):
        uid, register_time = common_token_verification(remote_ip, token)
        session = conn_db()
        current_time = time.time()
        member_obj = session.query(ShopMember).filter(ShopMember.uid == uid).first()
        if member_obj is None:
            session.close()
            raise TokenError("5006")

        if member_obj.is_expired == 1:
            session.close()
            raise TokenError("5007")

        # current_time = string_to_ts("2022-1-31 12:12:38")  # for test
        senior_expire_time = string_to_ts(member_obj.senior_expire_time) if member_obj.senior_expire_time is not None else current_time
        give_duration = register_time + AUTOMATIC_GIVEAWAY_TIME

        if member_obj.grade_type == 2:
            if current_time >= senior_expire_time:
                member_obj.grade_type = 0
                member_obj.is_expired = 1
                session.commit()
                session.close()
                raise TokenError("5007")

        session.commit()
        session.close()

        return True

    def inner(self, *args, **kwargs):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        try:
            if token is None or len(token) == 0:
                if cookie_token is None:
                    raise TokenError("5000")
                else:
                    print("Use cookie token")
                    token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip

            token_verification(remote_ip, token)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)
            return

        except Exception as e:
            print("Member token exception >>>> ", e)
            self.render("login.html")
            return

        func(self, *args, **kwargs)
    return inner


def async_member_login_redirect(func):
    def token_verification(remote_ip, token):
        uid, register_time = common_token_verification(remote_ip, token)
        session = conn_db()
        current_time = time.time()
        member_obj = session.query(ShopMember).filter(ShopMember.uid == uid).first()
        if member_obj is None:
            session.close()
            raise TokenError("5006")

        if member_obj.is_expired == 1:
            session.close()
            raise TokenError("5007")

        # current_time = string_to_ts("2022-1-31 12:12:38")  # for test
        senior_expire_time = string_to_ts(member_obj.senior_expire_time) if member_obj.senior_expire_time is not None else current_time
        give_duration = register_time + AUTOMATIC_GIVEAWAY_TIME

        if member_obj.grade_type == 2:
            if current_time >= senior_expire_time:
                member_obj.grade_type = 0
                member_obj.is_expired = 1
                session.commit()
                session.close()
                raise TokenError("5007")

        session.commit()
        session.close()

        return True

    async def inner(self, *args, **kwargs):
        cookie_token = self.get_secure_cookie("token")
        token = self.get_argument("Authorization", None)
        try:
            if token is None or len(token) == 0:
                if cookie_token is None:
                    raise TokenError("5000")
                else:
                    print("Use cookie token")
                    token = cookie_token

            if isinstance(token, bytes):
                token = token.decode()

            x_real_ip = self.request.headers.get("X-Real-IP")
            remote_ip = x_real_ip or self.request.remote_ip

            token_verification(remote_ip, token)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)
            return

        except Exception as e:
            print("Async member token exception >>>> ", e)
            self.render("login.html")
            return

        await func(self, *args, **kwargs)
    return inner


def create_token(user, remote_ip=None):
    print("Remote ip ", remote_ip)
    payload = {
        "timestamp":  time.time(),
        "phonenum": user,
        "remote_ip": remote_ip,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token.decode()


def redis_conn():
    pool = redis.ConnectionPool(host=REDIS_HOST, password="")
    redis_cli = redis.Redis(connection_pool=pool, max_connections=100)
    return redis_cli


def qrcode_path(trade_id, prefix=''):
    path = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(path, 'upload', "qrcodes")
    # folder = 'upload/qrcodes'

    if not os.path.exists(folder):
        os.mkdir(folder)

    return os.path.join(prefix, folder, trade_id)


def create_qrcode(url, trade_id):
    path = qrcode_path("{}.png".format(trade_id))
    img = qrcode.make(url)
    img.save(path)
    return path


def descry_token(encrypted_token):
    with open("private2.pem", 'r') as f:
        key = f.read()
    privite_key = RSA.importKey(key)
    decryptor = PKCS1_OAEP.new(privite_key)
    token = decryptor.decrypt(encrypted_token)
    print("decrypted token >>>", token)
    return token


def store_token_msg(token):
    """ token jwt 解码后内容保存数据库(Ip, username, macheine_id) """
    token_dic = jwt.decode(token, SECRET_KEY)
    print(token_dic)

    username = token_dic["username"]
    remote_ip = token_dic["ip"]
    license = token_dic["license"]
    machine_id = token_dic["machine_id"]
    start_time = token_dic["timestamp"]
    print(type(start_time), start_time)
    end_time = float(start_time) + 3600 * 24 * 30

    session = conn_db()

    license_obj_list = session.query(ShopModelToken).filter(
        ShopModelToken.license == license,
    ).all()
    print(">>>", len(license_obj_list))

    if len(license_obj_list) > 0:
        for license_obj in license_obj_list:
            if license_obj.machine_id != machine_id or license_obj.user != username:
                return False

    token_obj = session.query(ShopModelToken).filter(
        ShopModelToken.user == username,
        ShopModelToken.machine_id == machine_id,
        ShopModelToken.remote_ip == remote_ip,
        ShopModelToken.license == license,
    ).first()

    if token_obj is not None:
        token_obj.start_time = start_time
        token_obj.end_time = str(end_time),

    else:
        token_msg = ShopModelToken(
            user=username,
            machine_id=machine_id,
            remote_ip=remote_ip,
            license=license,
            start_time=start_time,
            end_time=str(end_time),
        )

        session.add(token_msg)
    session.commit()
    session.close()
    return True


def encry_file(token, model_file):
    def _generate_file_key(token):
        m = hashlib.md5()
        m.update(token)
        FileKey = m.digest()
        print("FileKey", FileKey)
        return FileKey

    FileKey =_generate_file_key(token)

    encryted_model_file = os.path.join("./download", model_file)

    with open(model_file, 'rb') as f:
        data = f.read()

    des = DES3.new(FileKey, DES3.MODE_ECB)
    binary_text = data + (8 - (len(data) % 8)) * b'='
    hex_text = des.encrypt(binary_text)  # Hexadecimal representation of binary data

    return hex_text, encryted_model_file


def string_to_ts(str_time):
    try:
        if not isinstance(str_time, str):
            str_time = str(str_time)

        ts = time.mktime(time.strptime(str_time, "%Y-%m-%d %H:%M:%S"))
        return ts
    except ValueError as e:
        print("Catch error: ", e)
        return 0


def ts_to_string(ts):
    if not isinstance(ts, float):
        ts = float(ts)
    time_array = time.localtime(ts)
    str_time = time.strftime("%Y-%m-%d %H:%M:%S", time_array)
    return str_time


def store_upload_record(remote_ip, user, params):
    session = conn_db()
    uid = session.query(ShopUser).filter(ShopUser.phonenum == user).first().id

    video = ShopVideo(
        video_name=params['filename'],
        model_name=params['charactor'],
        uid=uid,
        md5_sum='fake_video_md5',
        audio_name='test.wav',
        audio_allowed=1,
        remote_ip=remote_ip,
    )

    session.add(video)
    session.commit()
    video_id = video.id
    session.close()
    return video_id


def get_code_by_str(text):
    if not isinstance(text, str):
        print("请输入字符串参数.....")
        return None
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image()
    img_data = io.BytesIO()
    img.save(img_data)
    return img_data


def get_token_user(cookie_token, token):
    if token is None or len(token) == 0:
        if cookie_token is None:
            raise TokenError("5000")
        else:
            print("use cookie token")
            token = cookie_token

    if isinstance(token, bytes):
        token = token.decode()

    token_dic = jwt.decode(token.encode(), SECRET_KEY)
    username = token_dic.get('phonenum')
    print(f">> Current User: {username}")
    return username


def generate_order_id():
    struct_time = time.localtime(float("%.7f" % time.time()))
    order_id = str(time.strftime('%Y%m%d%H%M%S', struct_time)) + str(time.time()).replace('.', '')
    return order_id


def add_num(x, y):
    return x + y


def subtract_num(x, y):
    return x - y


def get_discount(x):
    # num = x / 10
    num = x
    res = int(num) if math.modf(num)[0] == 0.0 else round(num, 1)
    return res


def get_discount_price(x, y):
    if not isinstance(x, float):
        x = float(x)

    if not isinstance(y, float):
        y = float(y)

    num = x * (y / 100)
    res = int(num) if math.modf(num)[0] == 0.0 else round(num, 2)

    if math.modf(res)[0] == 0.0:
        res = int(res)

    return res


def get_filter_str(filter_list):
    print("filter_list", filter_list)
    filter_str = str()

    for current_filter in filter_list:
        filter_str += f"{current_filter}+"
    filter_str = filter_str[:-1]

    return filter_str


if __name__ == "__main__":
    test_token = create_token('123456', '192.168.0.6')
    # eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aW1lc3RhbXAiOjE1NjU2ODUwNzQuNjIwNzQyLCJwaG9uZW51bSI6IjEyMzQ1NiIsInJlbW90ZV9pcCI6IjEyNy4wLjAuMSJ9.25KAnrpqwkyfl2IXiXi9RxftHLUM7vCdKKAaNCbq0Ec
    print(test_token)




