from enum import Enum


class CreateType(Enum):
    CREATE_SECONDARY_MENU = 0
    ZIP = 1
    FEATURE = 2
    GOODS = 3
    VIDEO = 4


class DeleteType(Enum):
    SECONDARY_MENU = 0
    ZIP = 1
    FEATURE = 2
    GOODS = 3
    VIEW_VIDEO = 4


class GetType(Enum):
    DEFAULT = 0
    MAIN_MENU = 1
    RESOURCES = 2


class GoodsType(Enum):
    ZIP = 0
    FEATURE = 1


class ZipType(Enum):
    ACTOR = 1
    SCENE = 2
    ACTION = 3
    SHOT = 4


class CreateAuthority(Enum):
    SCENE = False
    SHOT = False
    ACTOR = True
    ACTION = True


class PayChannel(Enum):
    WXPAY = 0
    ALIPAY = 1
    Free = 2


class RechargeStatus(Enum):
    SUCCESS = 0
    FAIL = 1


class OrderStatus(Enum):
    SUCCESS = 0
    NOTPAY = 1
    PAYERROR = 2
    REVOKED = 3
    CLOSED = 4
    USERPAYING = 5


class OwnerEnum(Enum):
    PAID = 0
    AllUSER = 1
    MEMBER = 2


class MemberLevel(Enum):
    NON_MEMBER = 0  # 非会员
    JUNIOR_MEMBER = 1  # 初级会员(已废弃)
    SENIOR_MEMBER = 2   # VIP(原高级会员)
    CUSTOM_USER = 3     # 定制用户(可查看定制压缩包)
    INTERNAL_USER = 4   # 内部用户(可查看所有压缩包)
    INTERNAL_CUSTOM_USER = 5  # 内部定制用户(可查看内部定制压缩包)


class ResourceType(Enum):
    CUSTOM_RESOURCE = 0     # 定制资源
    COMMON_RESOURCE = 1     # 公共资源
    VIP_RESOURCE = 2        # VIP
    INTERNAL_COMMON_RESOURCE = 3   # 内部定制资源


class AuthorityLevel(Enum):
    CUSTOM = 0  # 非会员
    VIP = 2


class PayStatus(Enum):
    SUCCESS = "Success"  # 非会员
    Fail = "Fail"


class RecordLevel(Enum):
    RECORD = 0  # 录播
    LIVE = 1    # 直播
    RECORD_LIVE = 2     # 录播 + 直播
