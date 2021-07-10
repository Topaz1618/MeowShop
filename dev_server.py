import os.path
import os
import json
import jwt
import math
import asyncio
import ssl
import psutil
from urllib.parse import quote

import tornado.httpserver
import tornado.web
import tornado.options
from tornado.options import define, options

from base import BaseHandler
from config import SECRET_KEY
from code import TokenError, ShopError, BaseError, AuthError
from shop_extensions import get_resource_total_counts, generate_zip_items, generate_feature_items
from backend_extensions import get_user_id
from shop_enum import GoodsType
from shop_logger import logger as Shop_logging

define("port", default=8021, help="run on the given port", type=int)

chunk_size = 1024 * 1024 * 2


def generate_start_end_point(page_num, page_limit, total):
    current_page = page_num if page_num is not None else 1
    page_limit = page_limit if page_limit is not None else total
    total_page = total / page_limit
    total_page = math.ceil(total_page)
    print("total_page", total_page)

    if current_page > total_page:
        print("raise error. ")
        raise ShopError("7002")

    start = (current_page - 1) * page_limit
    end = total if page_limit * current_page > total else page_limit * current_page

    return start, end


class TestHandler(BaseHandler):
    def get(self):
        print(f"内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")
        count = 0
        self.write("123")


class FeatureListHandler(BaseHandler):
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
            data_list = generate_zip_items(uid, start, end)
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


class DownloadVideoHandler(BaseHandler):
    async def get(self, filename):
        try:
            path = os.path.dirname(os.path.abspath(__file__))
            local_file = os.path.join(path, 'download', filename)
            file_exists = os.path.exists(local_file)
            if not file_exists:
                self.write({
                    'msg': 'file does not exist',
                    'error_code': '1008',
                    })
                self.finish()

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header("Content-Disposition", "attachment; filename=%s" % quote(filename))  # 中文支持

            count = 0
            with open(local_file, 'rb', buffering=100000) as f:
                while True:
                    count += 1
                    print(f"download api: {count}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")
                    chunk = f.read(chunk_size)
                    f.flush()
                    if not chunk:
                        break

                    self.write(chunk)
                    await self.flush()

            self.finish()
            Shop_logging.warning(f"Download [{filename}] completed.")

        except Exception as e:
            print(e)
            self.write({'msg': "Unknow Error", 'error_code': '1010'})
            self.finish()


class UploadFileHandler(BaseHandler):
    async def get(self):
        self.render("test_upload.html")

    def save_chunk(self, save_path, loop):
        asyncio.set_event_loop(loop)
        file_metas = self.request.files['file']
        print(file_metas[0].keys())
        for meta in file_metas:
            with open(save_path, 'wb') as up:
                up.write(meta['body'])

    async def post(self):
        filename = self.get_argument("filename", None)
        count = self.get_argument("count", None)
        total_chunk = self.get_argument("total_chunk", None)
        file_uuid = self.get_argument("uuid", None)
        uuid_path = f"{filename.split('.')[0]}_{file_uuid} "
        chunk_path = os.path.join("download", "tmp", uuid_path)
        if not os.path.exists(chunk_path):
            os.mkdir(chunk_path)

        print(f"File upload API  file name: {filename} chunk count: {count}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")

        save_path = os.path.join(chunk_path, "%05d" % int(count))
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self.save_chunk, save_path, loop)
        print("go")

        await self.flush()

        if len(os.listdir(chunk_path)) != int(total_chunk):
            self.write("uploading")
        else:
            self.write('success')


class MergeFileHandler(BaseHandler):
    async def post(self):
        Shop_logging.warning(f" !!!!! Hello! File Merge API!! ")

        filename = self.get_argument("filename", None)
        total_chunk = self.get_argument("total_chunk", None)
        file_uuid = self.get_argument("uuid", None)
        uuid_path = f"{filename.split('.')[0]}_{file_uuid} "
        chunk_path = os.path.join("download", "tmp", uuid_path)
        # chunk_path = os.path.join("download", "tmp", filename.split(".")[0])
        file_path = os.path.join("download", filename)
        if os.path.exists(file_path):
            print(f"File {filename} already exist, ready to delete it. ")
            os.remove(file_path)

        if not os.path.exists(chunk_path):
            self.write("false")
            return

        if len(os.listdir(chunk_path)) != int(total_chunk):
            self.write("false")
            return

        files = sorted(os.listdir(chunk_path))
        with open(file_path, "wb+") as fd:
            for file in files:
                with open(os.path.join(chunk_path, file), "rb") as f:
                    data = f.read()
                    fd.write(data)
                    fd.flush()

                print(f"File merge API file name: {chunk_path}  Current count: {file}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")

        self.write("true")


class TestUploadFileHandler(BaseHandler):
    async def get(self):
        self.render("test_upload.html")

    async def post(self):
        filename = self.get_argument("filename", None)
        save_path = os.path.join("download", filename)
        file_metas = self.request.files['file']
        print(file_metas[0].keys())
        for meta in file_metas:
            with open(save_path, 'wb') as up:
                up.write(meta['body'])

        self.write("done")


if __name__ == "__main__":
    tornado.options.parse_command_line()
    settings = {
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
        "login_url": "/login",
    }

    application = tornado.web.Application([
        # 用户系统
        (r'/video_download/(.*)', DownloadVideoHandler),
        (r'/test', TestHandler),
        (r'/upload_file', UploadFileHandler),  # need to send merge request
        (r'/merge_file', MergeFileHandler),
        (r'/feature_list', FeatureListHandler),
        (r'/zip_list', ZipListHandler),
        (r'/test_upload', TestUploadFileHandler),

    ], debug=True, **settings)

    CA_FILE = "encry_files/WoSign-RSA-root.crt"
    CERT_FILE = "encry_files/4916579_www.zr-ai.com.pem"
    KEY_FILE = "encry_files/4916579_www.zr-ai.com.key"

   
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    context.load_verify_locations(CA_FILE)    # 根证书

    http_server = tornado.httpserver.HTTPServer(
        application,
        ssl_options=context,
        max_buffer_size=10485760000)
    http_server.listen(options.port)

    # tornado.ioloop.IOLoop.current().start()
    asyncio.get_event_loop().run_forever()

