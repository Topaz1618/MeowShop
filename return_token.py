import jwt
from time import time, sleep

from auth import BaseHandler
from config import SECRET_KEY, TOKEN_TIMEOUT, MODEL_LIST
from models import conn_db, ShopModelToken
from shop_utils import descry_token, store_token_msg, encry_file

from tornado import web


class ReturnTokenHandler(BaseHandler):
    @staticmethod
    def _create_token(username, machine_id, model_name):
        data = {
            "timestamp": time(),
            "username": username,
            "machine_id": machine_id,
            "model_name": model_name,
        }
        SECRET_KEY = 'bm9i17d=7168!(6t$8dsw)j5bn1(dl_%c(=-6d0-zexgv+y2p9'
        token = jwt.encode(data, SECRET_KEY, algorithm='HS256')
        return token

    async def post(self):
        username = self.get_argument("username", "")
        machine_id = self.get_argument("machine_id", "")
        model_name = self.get_argument("model_name", "")
        token = self._create_token(username, machine_id, model_name)
        self.write({'msg': token.decode(), 'error_code': '1000'})


class ReturnTimesHandler(BaseHandler):
    def post(self):
        username = self.get_argument("username", "")
        machine_id = self.get_argument("machine_id", "")
        ip = self.get_argument("ip", "")
        # ip = self.get_client_ip()
        # ip = "127.0.0.1"
        print(">>>>", username, machine_id, ip)

        session = conn_db()
        token_obj = session.query(ShopModelToken).filter(
            ShopModelToken.user == username,
            ShopModelToken.machine_id == machine_id,
            ShopModelToken.remote_ip == str(ip),
        ).first()

        if token_obj is not None:
            start_time = token_obj.start_time
            end_time = token_obj.end_time
            data = {
                "start_time": start_time,
                "end_time": end_time,
            }

            self.write({"msg": data, "error_code": "1000"})
        else:
            self.write({"msg": "Error msg", "error_code": "-1"})


class ReturnModelFile(BaseHandler):
    async def get(self):
        raise web.HTTPError(333)

    async def post(self):
        try:
            encryed_token_hex = self.get_argument("Authorization", "")
            encryed_token = bytes.fromhex(encryed_token_hex)

            model_name = self.get_argument("model_name", "")
            model_name = "man01"

            token = descry_token(encryed_token)
            store_status = store_token_msg(token)
            if not store_status:
                raise web.HTTPError(400)
                # self.write({"message": "License error", "error_code": "-1"})
                # self.finish()
            else:

                model_file = MODEL_LIST[model_name]
                encry_text, encry_model = encry_file(token, model_file)
                print(">>>> len", len(encry_text))

                # with open(encry_model, 'rb') as f:
                #     buf_size = 10240
                #     while True:
                #         data = f.read(buf_size)
                #         if not data:
                #             break
                #         print(">>>>> ")
                #         self.write(data)
                #         print("send data", len(data))
                # self.flush()

                encry_text_copy = encry_text
                while True:
                    buf_size = 10240
                    if len(encry_text_copy) > buf_size:
                        data = encry_text_copy[:buf_size]
                        self.write(data)
                    else:
                        data = encry_text_copy
                        self.write(data)
                        break
                    encry_text_copy = encry_text_copy[buf_size:]
                self.flush()

        except web.HTTPError as e:
            print("Error", e)
            raise web.HTTPError(400)





