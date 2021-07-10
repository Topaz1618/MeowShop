import asyncio
import ssl
from sqlalchemy import distinct, func, or_, and_

import tornado.web
import tornado.options
import tornado.httpserver
from tornado.options import define, options

import os
import math

from base import BaseHandler
from code import TokenError
from config import PRODUCT_USER, PAGE_LIMIT, TEST_USER
from shop_utils import get_token_user, subtract_num, add_num

from models import conn_db, ShopUser, ShopMember

define("port", default=8022, help="run on the given port", type=int)
from urllib.parse import parse_qs


def count_registered_user():
    session = conn_db()
    total = session.query(func.count(distinct(ShopUser.id))).filter(
        *[ShopUser.phonenum != name for name in TEST_USER]
    ).scalar()

    sum_access = session.query(func.sum(distinct(ShopUser.access_times))).filter(
        *[ShopUser.phonenum != name for name in TEST_USER]
    ).scalar()

    avg_counts = int(sum_access / total)

    session.close()
    return total, avg_counts


def get_registered_user_info(start, end):
    session = conn_db()

    user_list_obj = session.query(ShopUser).filter(
        *[ShopUser.phonenum != name for name in TEST_USER]
    )[start:end]

    data = []
    for user_obj in user_list_obj:
        uid = user_obj.id
        member_obj = session.query(ShopMember).filter(
            ShopMember.uid == uid,
        ).first()

        if member_obj is not None:
            access_times = int(user_obj.access_times) if user_obj.access_times is not None else 0
            total_time = access_times * 60
            data.append({
                "user": user_obj.phonenum,
                "access_count": access_times,
                "member_level": member_obj.grade_type,
                "is_expired": member_obj.is_expired,
                "total_time": total_time,

            })

    return data


class StatusHandler(BaseHandler):
    def get(self):
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

            total_data, avg_counts = count_registered_user()

            total_page = total_data / PAGE_LIMIT
            total_page = math.ceil(total_page)
            start = (current_page - 1) * PAGE_LIMIT
            end = total_data if PAGE_LIMIT * current_page > total_data else PAGE_LIMIT * current_page

            data = get_registered_user_info(start, end)
            use_time_avg = avg_counts * 60

            page_info = {
                "start": start,
                "end": end,
                "limit": PAGE_LIMIT,
                "total_data": total_data,
                "current_page": current_page,
                "total_page": total_page,
                "avg_counts": avg_counts,
                "avg_time": use_time_avg,
            }
            self.render("status.html", username=username, data=data, page_info=page_info, add=add_num, subtract=subtract_num)

        except TokenError as e:
            self.render("authority_error.html", error_message=e.error_msg, error_code=e.error_code)

        except Exception as e:
            print(e)
            self.render("error_page.html", error_message="Unknow error")


class UpdateOrderHandler(BaseHandler):
    def get(self):
        body_str = self.request.body.decode('utf-8')
        post_data = parse_qs(body_str)
        post_dict = dict()
        for k, v in post_data.items():
            post_dict[k] = v[0]

        print("Post dict: ", post_dict)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    settings = {
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
        "login_url": "/login",
    }

    application = tornado.web.Application([
        (r'/status', StatusHandler),
        (r'/update_order', UpdateOrderHandler),

    ], debug=True, **settings)

    CA_FILE = "encry_files/WoSign-RSA-root.crt"
    CERT_FILE = "encry_files/4916579_www.zr-ai.com.pem"
    KEY_FILE = "encry_files/4916579_www.zr-ai.com.key"

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    context.load_verify_locations(CA_FILE)    # 根证书

    http_server = tornado.httpserver.HTTPServer(
        application,
        # ssl_options=context,
        max_buffer_size=10485760000)
    http_server.listen(options.port)

    # tornado.ioloop.IOLoop.current().start()
    asyncio.get_event_loop().run_forever()
