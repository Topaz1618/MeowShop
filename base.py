import os
import stat
import asyncio
import jwt
import psutil
import aiofiles
from time import time, sleep
from urllib.parse import quote

from tornado.web import RequestHandler

from backend_extensions import generate_zip_path, get_user_id, record_access_times
from shop_extensions import get_product_dict, get_goods_name
from shop_utils import auth_login_redirect, member_login_redirect, get_token_user, async_member_login_redirect
from shop_logger import logger as Shop_logging
from shop_logger import download_logger
from config import NewVersion, CHUNK_SIZE, SECRET_KEY, ADMIN_USER
from code import BaseError, DBError, PersonalItemError, TokenError, AuthError


class BaseHandler(RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("username")

    def get_client_ip(self):
        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip
        return remote_ip


class IndexHandler(BaseHandler):
    """ 主页面 """
    @auth_login_redirect
    def get(self):
        try:
            uri_token_list = self.request.uri.strip("/?").split("=")
            uri_token = uri_token_list[-1] if len(uri_token_list) > 1 else None
            cookie_token = self.get_secure_cookie("token")

            if cookie_token is None:
                self.set_secure_cookie("token", uri_token)

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)
            return

        except Exception as e:
            print(e)
            self.write({'msg': "Unknown Error", 'error_code': '1010'})
            return

        self.render("main.html")


class PageErrorHandler(BaseHandler):
    """ 错误页面 """
    def get(self):
        self.set_header("Response-Code", "404")
        self.render("404.html")


class GetVerisonHandler(BaseHandler):
    """ 获取版本 """
    def get(self):
        message = {'msg': {"version": str(NewVersion)}, 'error_code': 1000}
        self.write(message)


class DownloadHandler(BaseHandler):
    """ 客户端, 观看视频下载 API (权限限制: 无)  """
    async def get(self, filename):
        try:
            if filename.endswith("zip"):
                if filename != "Shop.zip":
                    raise BaseError("1005")

            path = os.path.dirname(os.path.abspath(__file__))
            local_file = os.path.join(path, 'download', filename)
            file_exists = os.path.exists(local_file)
            if not file_exists:
                raise BaseError("1003")

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header("Content-Disposition", "attachment; filename=%s" % quote(filename))  # 中文支持

            count = 0
            with open(local_file, 'rb', buffering=100000) as f:
                while True:
                    count += 1
                    print(f"download api: {count}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")
                    chunk = f.read(CHUNK_SIZE)

                    f.flush()
                    if not chunk:
                        break

                    self.write(chunk)
                    await self.flush()

            self.finish()
            Shop_logging.warning(f"Download [{filename}] completed.")

        except BaseError as e:
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            print(e)
            self.write({'msg': "Unknown Error", 'error_code': '1010'})
            self.finish()


class DownloadZipHandler(BaseHandler):
    """ Zip 下载接口 (权限限制: 有)  """
    def get_content_size(self, file_path):
        stat_result = os.stat(file_path)
        content_size = stat_result[stat.ST_SIZE]
        return content_size

    # @async_member_login_redirect
    async def get(self):
        try:
            print("!!!!")
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            print("!!!!", cookie_token, token)

            username = get_token_user(cookie_token, token)

            zip_id = self.get_argument("zip_id", None)   # zip id
            goods_id = self.get_argument("goods_id", None)  # goods id
            current_pos = self.get_argument("current_pos", None)   # For 断点续传
            print("!!!!!!!!!!!", zip_id, goods_id, current_pos, token)
            filename = generate_zip_path(zip_id, goods_id, username)
            # filename = "1.zip"      # "t.zip"

            CHUNK_SIZE = 1024 * 10
            path = os.path.dirname(os.path.abspath(__file__))
            local_file = os.path.join(path, 'download', filename)
            file_exists = os.path.exists(local_file)
            if not file_exists:
                print("Does not exist ")
                raise BaseError("1003")

            file_size = self.get_content_size(local_file)
            print("!!!!! file size: ", file_size)
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header("Content-Disposition", "attachment; filename=%s" % quote(filename))  # 中文支持
            self.set_header("File-Size", file_size)
            count = 0

            with open(local_file, 'rb', buffering=100000) as f:
                if current_pos is not None:  # For 算点续传
                    current_pos = int(current_pos) if not isinstance(current_pos, int) else current_pos
                    f.seek(current_pos)

                while True:
                    count += 1
                    print(f"Download api: {count}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")
                    chunk = f.read(CHUNK_SIZE)
                    print(len(chunk))
                    f.flush()
                    if not chunk:
                        break

                    self.write(chunk)
                    await self.flush()

                    # break for test ↓
                    # break

            download_logger.warning(f"\"DOWNLOAD FILE\" [Username: {username}] [Filename: {filename}] ")
            # message = {'msg': "Done!", 'error_code': "1000"}
            # self.write(message)
            self.finish()
            Shop_logging.warning(f"Download [{filename}] completed.")

        except TokenError as e:
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except BaseError as e:
            print("!!!!!!!!!1", e.error_msg)
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except DBError as e:
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except PersonalItemError as e:
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            print("E", e)
            self.write({'msg': "Unknown Error", 'error_code': '1010'})
            self.finish()


class UploadFileHandler(BaseHandler):
    """ zip 上传接口 (权限限制)  """

    @async_member_login_redirect
    async def get(self):
        self.render("test_upload.html")

    def save_chunk(self, save_path, loop):
        asyncio.set_event_loop(loop)
        file_metas = self.request.files['file']
        for meta in file_metas:
            with open(save_path, 'wb') as up:
                up.write(meta['body'])

    @async_member_login_redirect
    async def post(self):
        try:
            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            count = self.get_argument("count", None)
            file_uuid = self.get_argument("uuid", None)
            file_uuid = file_uuid.strip(" ")

            filename = self.get_argument("filename", None)
            total_chunk = self.get_argument("total_chunk", None)

            if filename is None:
                raise BaseError("1001")

            if filename.endswith("jpg") or filename.endswith("png") or int(total_chunk) <= 1:
                if filename.endswith("jpg") or filename.endswith("png"):
                    save_path = os.path.join("static/images/shop", filename)

                else:
                    save_path = os.path.join("download", filename)
                file_metas = self.request.files['file']
                for meta in file_metas:
                    with open(save_path, 'wb') as up:
                        up.write(meta['body'])
                await self.flush()
                self.write('success')

            else:
                uuid_path = f"{filename.split('.')[0]}_{file_uuid}_{username}"

                chunk_path = os.path.join("download", "tmp", uuid_path)

                if not os.path.exists(chunk_path):
                    os.mkdir(chunk_path)

                print(f"File upload API  file name: {filename} chunk count: {count}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")

                save_path = os.path.join(chunk_path, "%05d" % int(count))
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, self.save_chunk, save_path, loop)
                await self.flush()

                if len(os.listdir(chunk_path)) != int(total_chunk):
                    self.write("uploading")
                else:
                    download_logger.warning(f"\"UPLOAD FILE CHUNK\" [User: {username}] [File: {filename}]")
                    self.write('success')

        except TokenError as e:
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except BaseError as e:
            Shop_logging.warning(f"Download [{filename}] error: {e.error_msg}.")
            message = {'msg': e.error_msg, 'error_code': e.error_code}
            self.write(message)

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}
            self.write(message)


class MergeFileHandler(BaseHandler):
    """ 上传切片合并 API """

    def merge_file(self, chunk_path, file_path, username):
        files = sorted(os.listdir(chunk_path))
        with open(file_path, "wb+") as fd:
            for file in files:
                with open(os.path.join(chunk_path, file), "rb") as f:
                    data = f.read()
                    fd.write(data)
                    fd.flush()

                print( f"File merge API file name: {chunk_path}  Current count: {file}, 内存占用率: {psutil.virtual_memory().percent} | CPU 使用率: {psutil.cpu_percent(0)}")

        if username != ADMIN_USER:
            pass
            # Todo: 保存用户上传内容到表
        download_logger.warning(f"\"MERGE FILE\" [User: {username}] [File: {file_path}]")
        # remove_tmp_path(file_path, chunk_path)

    @async_member_login_redirect
    async def post(self):
        try:

            filename = self.get_argument("filename", None)
            total_chunk = self.get_argument("total_chunk", None)
            file_uuid = self.get_argument("uuid", None)
            # check_params(filename, total_chunk, file_uuid)

            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)

            if username != ADMIN_USER:
                image_path = self.get_argument("image_path", None)
                zip_name = self.get_argument("image_path", None)
                menu_id = self.get_argument("menu_id", None)
                # check_params(image_path, zip_name, menu_id)

            uuid_path = f"{filename.split('.')[0]}_{file_uuid}_{username}"
            chunk_path = os.path.join("download", "tmp", uuid_path)
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

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, self.merge_file, chunk_path, file_path, username)
            # loop.run_in_executor(None, remove_tmp_path, file_path, chunk_path)

            self.write("true")
        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}
            self.write(message)


class RecordTokenHandler(BaseHandler):
    @auth_login_redirect
    def post(self):
        try:

            cookie_token = self.get_secure_cookie("token")
            token = self.get_argument("Authorization", None)
            username = get_token_user(cookie_token, token)
            record_access_times(username)

            message = {'msg': 'Record access time successful. ', 'error_code': '1000'}

        except TokenError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except AuthError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            message = {'msg': "Unknown Error", 'error_code': '1010'}

        print("message: ", message)
        self.write(message)

    # @auth_login_redirect
    # def get(self):
    #     try:
    #         cookie_token = self.get_secure_cookie("token")
    #         token = self.get_argument("Authorization", None)
    #         username = get_token_user(cookie_token, token)
    #         record_access_times(username)
    #         message = {'msg': 'Record access time successful. ', 'error_code': '1000'}
    #
    #     except TokenError as e:
    #         message = {'msg': e.error_msg, 'error_code': e.error_code}
    #
    #     except AuthError as e:
    #         message = {'msg': e.error_msg, 'error_code': e.error_code}
    #
    #     except Exception as e:
    #         print(e)
    #
    #         message = {'msg': "Unknow Error", 'error_code': '1010'}
    #
    #     self.write(message)


class RecordUsageHandler(BaseHandler):
    @member_login_redirect
    def post(self):
        try:
            actor_id = self.get_argument("actor_id", None)
            record_type = self.get_argument("record_time", None) # 0: start 1: stop
            if record_type == 0:
                # create_record(username, actor_id) # 更新最后一个
                pass
            elif record_type == 1:
                # update_record(username, actor_id)
                pass

            message = {'msg': "Successful", 'error_code': "1000"}

        except BaseError as e:
            message = {'msg': e.error_msg, 'error_code': e.error_code}

        except Exception as e:
            print(e)
            message = {'msg': "Unknown Error", 'error_code': '1010'}
        self.write(message)


class TestHandler(BaseHandler):
    def get(self):
        # message = {'msg': "GOOD", 'error_code': "1000"}
        message = b"1dsdcdcdscsd"
        # sleep(1)
        self.set_header("File-Size", 163)

        print("Secure token: ", self.get_secure_cookie("token"))
        # self.set_secure_cookie("a", "123456tcookie")

        self.write(message)

    def post(self):
        print("Test api post")
        # self.set_header("Content-Length", 163)

        token = self.get_cookie("token", None)
        print("Token:", token)

        print("Secure Cookie", self.get_secure_cookie("a"))
        self.set_secure_cookie("a", "123456tcookie")

        self.write("!23")


""" 废弃 """
# class DownloadHandler(BaseHandler):
#     def get_content_size(self, file_path):
#         stat_result = os.stat(file_path)
#         content_size = stat_result[stat.ST_SIZE]
#         return content_size
#
#     def post(self):
#         try:
#             filename = self.get_argument("filename", "")
#
#             if len(filename) == 0:
#                 raise BaseError("1001")
#
#             file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download", filename)
#             file_exists = os.path.exists(file_path)
#             if not file_exists:
#                 raise BaseError("1003")
#
#             self.set_header('Content-Type', 'application/octet-stream')
#             self.set_header("Content-Disposition", "attachment; filename=%s" % quote(filename))  # 中文支持
#             # self.set_header('Content-Disposition', 'attachment; filename=' + filename)
#
#             file_size = self.get_content_size(file_path)
#             with open(file_path, 'rb') as f:
#                 while True:
#                     data = f.read(file_size)
#                     if not data:
#                         break
#                     self.write(data)
#             self.finish()
#
#         except BaseError as e:
#             message = {'msg': e.error_msg, 'error_code': e.error_code}
#             self.write(message)
#
#         except Exception as e:
#             self.write({'msg': "Unknow Error", 'error_code': '1010'})
#             self.finish()
