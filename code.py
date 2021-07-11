

class BaseError(Exception):
    def __init__(self, error_code):
        super().__init__(self)
        self.error_dic = {
            '1001': 'Get params failed. ',
            '1002': 'Type of input error. ',
            '1003': 'File does not exists. ',
            '1004': 'File receiving. ',
            '1005': 'Permission error. ',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = self.error_code

    def __str__(self):
        return self.error_msg


class AuthError(Exception):
    def __init__(self, error_code):
        super().__init__(self)
        self.error_dic = {
            '1001': 'user exists',
            '1002': "User does not exists",
            '1003': 'register failed',
            '1004': 'password failed',
            '1005': 'Password format failed',
            '1006': 'verify code does not exists or already expired or already used.',
            '1007': 'The verify code sent failed. ',
            '1008': 'Get phone number failed',
            '1009': 'phone number format failed. ',
            '1010': '已领取会员',
            "1011": '会员已过期 ',
            "1012": "Membership has expired",
            "1013": "创建内部测试用户失败",
            "1014": "已指定相同权限, 请勿重复设置",
            "1015": "仅允许【内部定制用户】绑定【内部定制商品】",
            "1016": "仅允许【定制用户】绑定【定制商品】",
            "1017": 'Please Check Email Format.',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = self.error_code

    def __str__(self):
        return self.error_msg



class PayError(Exception):
    def __init__(self, error_code, error_message=None):
        super().__init__(self)
        self.error_dic = {
            '3001': 'Product does not exist',
            '3002': 'Trade number does not exists',
            '3003': 'Recharge does not exists.',
            '3004': 'Payment Failed',
            '3005': 'Price failed',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = error_message

    def __str__(self):
        return self.error_msg


class DBError(Exception):
    def __init__(self, error_code, error_message=None):
        super().__init__(self)
        self.error_dic = {
            '4001': 'Get recharge list failed. ',
            '4002': 'Add new item failed. ',
            '4003': 'Item has already exists. ',
            '4004': 'Item does not exists. ',
            '4005': 'Get object failed',
            '4006': 'The currently deleted item is being referenced. ',
            '4007': 'Statistics of all data error. ',
            '4008': 'Statistical classification data error',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = error_message

    def __str__(self):
        return self.error_msg


class TokenError(Exception):
    def __init__(self, error_code, error_message=None):
        super().__init__(self)
        self.error_dic = {
            '5000': 'Get token failed. ',
            '5001': 'Token has already expired. ',
            '5002': 'Illegal Ip. ',
            '5003': 'Token does not exist. ',
            '5005': 'token does not match the user. ',
            "5006": 'Current user is not member. ',
            "5007": 'Member has expired. ',
            "5008": 'Current user is not admin.',
            "5009": 'Token format error.',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = error_message

    def __str__(self):
        return self.error_msg


class BackstageError(Exception):
    def __init__(self, error_code, error_message=None):
        super().__init__(self)
        self.error_dic = {
            '6000': 'Permission denied. ',
            '6001': 'Token has already expired. ',
            '6002': 'Illegal Ip. ',
            '6003': 'Token does not exist. ',
            '6004': 'token does not match the user',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = error_message

    def __str__(self):
        return self.error_msg


class ShopError(Exception):
    def __init__(self, error_code, error_message=None):
        super().__init__(self)
        self.error_dic = {
            '7000': '第三方订单号不存在. ',
            '7001': '订单号不存在. ',
            '7002': 'Current page does not exists. ',
            '7003': 'Secondary menu does not exists. ',
            '7004': 'Main menu does not exists.',
            '7005': 'Character does not exists.',
            '7006': 'The current product has been favorited. ',
            '7007': 'Item not collected. ',
            '7008': 'Statistics data error.',
            '7009': 'Data classification or sorting error.',
            '7010': 'Generate product data error.',
            '7011': 'Statistical product type error.',
            '7012': '找不到对应订单',
            '7013': '商城更新资源失败',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = error_message

    def __str__(self):
        return self.error_msg


class PersonalItemError(Exception):
    def __init__(self, error_code, error_message=None):
        super().__init__(self)
        self.error_dic = {
            '8000': 'User did not purchase this product. ',
            '8001': 'Product type does not support download. ',
        }
        self.error_code = error_code
        if self.error_code in self.error_dic:
            self.error_msg = self.error_dic.get(self.error_code)
        else:
            self.error_msg = error_message

    def __str__(self):
        return self.error_msg
