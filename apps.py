import os.path
import asyncio
import ssl

import tornado.httpserver
import tornado.web
import tornado.options
from tornado.options import define, options

from base import IndexHandler, PageErrorHandler, GetVerisonHandler, UploadFileHandler, MergeFileHandler, DownloadZipHandler, \
    DownloadHandler, TestHandler, RecordTokenHandler, RecordUsageHandler

from auth import LoginHandler, LogoutHandler,  \
    RegisterHandler, VerifyCodeHandler, RestPasswordView

from backend import StatusHandler, BackendHandler, GetResourceHandler,  CreateGoodsHanler, ManagerResources, ManagerMenuHandler,\
    GetVideoListHandler, ManagerViewFilesHandler, RenewalMemberHandler, UpdateGoodsHanler, IncreaseUserHandler, ShowInternalUsersHandler,\
    ModifyResourcesHandler, GetAllResourceHandler, ShowGoodsItemsHandler, ShowOrdersHandler, SingleResourceHandler, CreateZipHandler, \
    CreateFeatureHandler, CreateVideoHandler, ModifyUserPerHandler,  ModifyZipHandler, ModifyFeatureHandler, CreateGuideHandler, \
    CheckUserExistsHandler, GetBindUsersHandler, ModifyRecordPerHandler, GetRecordPerHandler

from transaction import ALiPayHandler, AliUpdateOrderHandler, OrderListHandler, QueryOrderHandler,  DeleteOrderHandler, CloseOrderHandler, \
    PayAgainHandler, SingleOrderHandler

from shop import StoreCatalogHandler, SingleProductHandler, FeatureListHandler, ZipListHandler, ComponentListHandler, \
    AddMyHeartHandler, DeleteMyHeartHandler, MyItemsHandler, MyHeartItemsHandler, CheckIsBoughtHandler, AboutUsHandler, \
    FeedbackHandler, PackageListHandler, UserInfoHandler, CheckIsMemberHandler, PayPageHandler, NotifyPurchasedHandler, \
    AllProductsHandler, CountGoodsHandler

from tmp_file.tcp_demo import MyServer

define("port", default=8001, help="run on the given port", type=int)

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

        (r'/register', RegisterHandler),
        (r'/login', LoginHandler),
        (r'/logout', LogoutHandler),
        (r'/reset_password', RestPasswordView),

        (r'/record_token', RecordTokenHandler),
        (r'/request-verifycode', VerifyCodeHandler),
        (r'/forget-password', RestPasswordView),

        # 后台
        (r'/backend', BackendHandler),
        (r'/create_guide', CreateGuideHandler),
        (r'/create_zip', CreateZipHandler),
        (r'/create_feature', CreateFeatureHandler),
        (r'/create_video', CreateVideoHandler),
        (r'/status', StatusHandler),
        (r'/renewal_member', RenewalMemberHandler),
        (r'/modify_user_per', ModifyUserPerHandler),        # 修改用户权限
        (r'/modify_record_permission', ModifyRecordPerHandler),  # 修改录播直播权限

        (r'/check_user_exists', CheckUserExistsHandler),    # 修改用户权限
        (r'/get_bind_users', GetBindUsersHandler),
        (r'/get_record_permission', GetRecordPerHandler),  # 获取用户直播录播权限

        (r'/modify_zip', ModifyZipHandler),             # 修改包权限
        (r'/modify_feature', ModifyFeatureHandler),     # 修改功能权限, 功能页面


        (r'/add_internal_user', IncreaseUserHandler),
        (r'/internal_users', ShowInternalUsersHandler),
        (r'/menu_items', ManagerMenuHandler),
        (r'/create_goods', CreateGoodsHanler),
        (r'/update_goods', UpdateGoodsHanler),
        (r'/goods_list', ShowGoodsItemsHandler),
        (r'/view_orders', ShowOrdersHandler),
        (r'/manager_resources', ManagerResources),
        (r'/modify_resources', ModifyResourcesHandler),
        (r'/single_resource', SingleResourceHandler),
        (r'/get_resource', GetResourceHandler),
        (r'/all_resources', GetAllResourceHandler),

        # (r'/zip_items', GetZipItemsHandler),

        (r'/get_video_list', GetVideoListHandler),
        (r'/manager_view_videos', ManagerViewFilesHandler),

        # 支付宝支付
        (r'/alipay', ALiPayHandler),
        (r'/update_order', AliUpdateOrderHandler),
        (r'/pay_again', PayAgainHandler),
        (r'/query_order', QueryOrderHandler),
        # (r'/pay_result', PayResultHandler),

        # Shop
        (r'/', IndexHandler),                # 首页
        # (r'/', StoreCatalogHandler),                # 首页

        (r'/user_info', UserInfoHandler),  # 查看个人会员信息
        (r'/about_us', AboutUsHandler),
        (r'/feedback', FeedbackHandler),
        (r'/notify_purchased', NotifyPurchasedHandler),

        (r'/store_catalog', StoreCatalogHandler),
        (r'/single_product', SingleProductHandler),
        (r'/feature_list', FeatureListHandler),
        (r'/zip_list', ZipListHandler),
        (r'/component_list', ComponentListHandler),
        (r'/get_items', AllProductsHandler),  # 废弃

        (r'/package_list', PackageListHandler),

        (r'/order_list', OrderListHandler),
        (r'/single_order', SingleOrderHandler),
        (r'/delete_order', DeleteOrderHandler),
        (r'/close_order', CloseOrderHandler),
        (r'/count_goods', CountGoodsHandler),

        (r'/pay', PayPageHandler),  # 付款方式选择页面
        (r'/my_heart', MyHeartItemsHandler),

        (r'/add_myheart', AddMyHeartHandler),
        (r'/delete_myheart', DeleteMyHeartHandler),

        (r'/my_items', MyItemsHandler),  # 个人购买物品

        (r'/check_is_bought', CheckIsBoughtHandler),
        (r'/check_version', GetVerisonHandler),
        (r'/check_is_member', CheckIsMemberHandler),

        # Uplpad & download API
        (r'/upload_file', UploadFileHandler),  # 断点切片上传
        (r'/merge_file', MergeFileHandler),
        (r'/download/(.*)', DownloadHandler),  # For Shop 客户端下载, 视频下载等
        (r'/download_zip', DownloadZipHandler),  # Zip 下载

        # 其它
        (r'/record_usage', RecordUsageHandler),  # 断点切片上传

        # For test
        (r'/test', TestHandler),

        # 404
        ('.*', PageErrorHandler),


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

    # tcp_server = MyServer()
    # tcp_server.listen(8013)

    # tcp_frame = TCPFrameServer()
    # tcp_server.listen(8014)

    # tornado.ioloop.IOLoop.current().start()
    asyncio.get_event_loop().run_forever()
