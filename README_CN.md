<img src='static/img/logo.png' width='400' title='MeowShop, online shopping site'>

A shopping websites that sell virtual items made by [Topaz](https://topaz1618.github.io/about)|[Website](http://topazaws.com/)|[Blog](https://topaz1618.github.io/blog/)

[英文 README](https://github.com/Topaz1618/FileManageSystem/blob/master/README.md)


# Features:
    - 用户注册/登录/登出(原注册流程基于短信验证码，已暂时关闭)
    - 注册自动送七天会员 (会员有机会获得免费虚拟商品)
    - 会员充值

    - 商品
        - 收藏商品
        - 商品打折
        - 促销商品，新上架商品展示
        - 商品基础信息显示
        - 商品分类过滤
        - 商品排序
        - 在线支付

    - 订单部分
        - 订单列表
        - 订单基本信息显示: 第三方单号, 付款时间, 折扣金额，实际支付金额
        - 订单删除
        - 超时订单自动关闭

    - 后台管理
        - 增加功能
        - 增加
        - 商品发布
        - 商品修改(价格，折扣)
        - 商品删除

    - 个人信息显示:
        - 注册时间
        - 用户名
        - 退出登录
        - 密码修改(已有功能，暂未开启)


# Environment
    - Python3
    - Tornado
    - Ubuntu16.04/ Mac OS
    - Mysql


## Requirements
- tornado >= 6.1
- PyJWT == 1.7.1

## Installation (Ubuntu & Mac OS)
1. Download MeowFile
```
    $ git clone git@github.com:Topaz1618/MeowShop.git
```

2. Install dependencies
```
    pip install -r requirements.txt
```

3. Create database & Generate admin user
```
    python models.py
```

4. Modify configuration
```
    $ cd MeowFile
    $ vim config.py
    USERNAME = "root"
    PASSWORD = "123456"
    HOST = "127.0.0.1"
    PORT = "3306"
    DATABASE = "aaaDB"

    DEBUG_PAY = True    // Open sandbox test (Set to false in the production environment)
    APPID = "2021000116669851"  // Alipay App ID
    APP_NOTIFY_URL = "https://www.123.com/update_order"   // Callback URL
    ALIPAY_PUBLIC_KEY_PATH = "alipay_public_key.pem"    // Alipay Public Key
    APP_PRIVATE_KEY_PATH = "app_private_key.pem"        // Private key
```

## Run
```
    python apps.py
```

## Screenshots

## 【商城首页】
<img src='static/images/upload.gif' title='MeowFile, A file management system'>

## 【商城页】
<img src='static/images/download1.gif' title='MeowFile, A file management system'>

## 【我的收藏】
<img src='static/images/user_list.png' width='800' title='MeowFile, A file management system'>

## 【商品页】
<img src='static/images/log.gif' title='MeowFile, A file management system'>

## 【后台】
<img src='static/images/create_user.gif' title='MeowFile, A file management system'>

## 【其它页面】
Not logged in or access the wrong path）
<img src='static/images/others.gif' title='MeowFile, A file management system'>

## GIF 生成命令
```
    ffmpeg -i test.mp4 -s 1920x1080 -r 10 -vf scale=800:450 output.gif //  -r: specify frame rate
```
[查看更多 ffmpeg](https://topaz1618.github.io/about)


[Topaz](https://topaz1618.github.io/about)|[Website](http://topazaws.com/)|[Blog](https://topaz1618.github.io/blog/)

## License
Licensed under the MIT license