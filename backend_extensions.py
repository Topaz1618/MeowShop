import random
import string
import jwt
import hmac
import hashlib
import os
from time import time
from datetime import datetime, date, timedelta
from sqlalchemy import distinct, func, or_, and_

from models import conn_db, ShopUser, ShopSecondaryMenu,  ShopZipFiles, ShopFeatures, \
    ShopGoods, ShopViewVideo, ShopMember, ShopPersonalItems, ShopMainMenu, ShopCustomItems
from shop_enum import CreateType, DeleteType, GoodsType, MemberLevel, ResourceType
from base_extensions import get_user_id
from shop_extensions import generate_zip_dict, generate_feature_dict
from order_extensions import handsel_member
from config import TEST_USER, SECRET

from shop_utils import ts_to_string, string_to_ts
from code import AuthError, PayError, DBError, TokenError, BaseError, PersonalItemError, ShopError


def check_if_user_exists(username):
    session = conn_db()
    user_exists = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
    if user_exists is not None:
        session.close()
        raise AuthError("1001")
    session.close()
    return True


def check_if_item_exists(item_id):
    session = conn_db()
    menu_item_obj = session.query(ShopSecondaryMenu).filter(ShopSecondaryMenu.id == item_id).first()
    if menu_item_obj is None:
        session.close()
        return False

    session.close()
    return True


def check_if_character_exists(character_id):
    session = conn_db()
    character_obj = session.query(ShopZipFiles).filter(ShopZipFiles.id == character_id).first()
    if character_obj is None:
        session.close()
        return False

    session.close()
    return True


def check_is_admin(username):
    session = conn_db()
    user_obj = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
    if user_obj is None:
        session.close()
        raise AuthError("1002")
    is_admin = user_obj.is_admin
    session.close()
    return is_admin


def check_if_member(username):

    session = conn_db()
    user_obj = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
    uid = user_obj.id

    member_obj = session.query(ShopUser).filter(ShopMember.id == uid, ShopMember.is_expired == False).first()
    is_member = 1 if member_obj is not None else 0

    session.close()
    return is_member


def create_internal_user(username, password):
    session = conn_db()
    try:
        password = hmac.new(SECRET, password.encode(), hashlib.md5).hexdigest()
        user = ShopUser(phonenum=username, password=password, access_times=0)
        session.add(user)
        session.commit()
        session.close()
    except:
        session.close()
        raise AuthError("1013")


def add_package_type(parent_id, type_name):
    session = conn_db()
    type_obj = session.query(ShopSecondaryMenu).filter(ShopSecondaryMenu.parent_id == parent_id,
                                                          ShopSecondaryMenu.name == type_name).first()
    if type_obj is not None:
        if type_obj.is_delete == True:
            type_obj.is_delete = False
            session.commit()
            session.close()
        else:
            session.close()
            raise DBError("4003")
    else:
        try:
            package_type = ShopSecondaryMenu(
                parent_id=parent_id,
                name=type_name,
            )
            session.add(package_type)
            session.commit()
            session.close()
        except Exception as e:
            print(">>>", e)
            session.close()
            raise DBError("4002")


def get_user_list():
    session = conn_db()
    user_obj_list = session.query(ShopUser).all()
    data = []
    for user_obj in user_obj_list:
        data.append([user_obj.id, user_obj.phonenum])

    return data


def bind_custom_items(userlist, zip_id, item_type):
    if len(userlist ) == 0:
        return

    session = conn_db()

    if not isinstance(zip_id, int):
        zip_id = int(zip_id)


    users = userlist.split(",")
    for user in users:
        uid = get_user_id(user)
        item_obj = session.query(ShopCustomItems).filter(
            ShopCustomItems.uid == uid,
            ShopCustomItems.resource_id == zip_id,
            ShopCustomItems.resource_type == item_type,
        ).first()

        if item_obj is None:
            custom_item = ShopCustomItems(
                uid=uid,
                resource_id=zip_id,
                resource_type=item_type,
            )

            session.add(custom_item)

    session.commit()
    session.close()


def create_zip_file(parent_id, resource_name, zip_name, img_name,  is_common, is_component, description, username, userlist):
    print(">>>> create", parent_id, zip_name, img_name,  is_common, is_component, description)

    session = conn_db()

    is_exists = check_if_item_exists(parent_id)
    if not is_exists:
        session.close()
        raise DBError("4004")

    zip_obj = session.query(ShopZipFiles).filter(
        ShopZipFiles.parent_id == parent_id,
        ShopZipFiles.zip_name == zip_name,
        ShopZipFiles.img_path == img_name,

    ).first()

    if zip_obj is not None:
        session.close()
        raise DBError("4003")

    try:
        zip_file = ShopZipFiles(
            zip_name=zip_name,
            name=resource_name,
            img_path=img_name,
            parent_id=parent_id,
            description=description,
            is_component=bool(int(is_component)),
            is_common=int(is_common),
        )
        session.add(zip_file)
        session.commit()
        zip_id = zip_file.id

        session.close()

        bind_custom_items(userlist, zip_id, GoodsType.ZIP.value)

        return zip_id

    except Exception as e:
        print("db error", e)
        session.close()
        raise DBError("4002")


def create_video_record(video_name, img_path, title, version, description, bind_type, bind_id):
    session = conn_db()

    video_obj = session.query(ShopViewVideo).filter(
        ShopViewVideo.title == title,
    ).all()

    title_counts = len(video_obj)
    if title_counts > 0:
        title = f"{title}({title_counts})"

    user_obj = session.query(ShopUser).filter(
        ShopUser.phonenum == "15600803270",
    ).first()

    uid = user_obj.id

    print("video_name, img_path, title, version, description. ", video_name, img_path, title, version, description, uid, bind_type, bind_id)

    try:
        video_record = ShopViewVideo(
            uid=uid,
            video_name=video_name,
            img_path=img_path,
            title=title,
            version=version,
            description=description,
            bind_type=bind_type,
            bind_id=bind_id,
        )
        session.add(video_record)
        session.commit()
        session.close()

    except Exception as e:
        session.close()
        raise DBError("4002")


def update_package_img(zip_id, img_name):
    session = conn_db()
    type_obj = session.query(ShopZipFiles).filter(
        ShopZipFiles.id == zip_id,
    ).first()

    if type_obj is None:
        session.close()
        raise DBError("4004")

    try:
        type_obj.img_path = img_name,
        session.commit()
        zip_id = type_obj.id
        session.close()
        print(zip_id)
        return zip_id

    except Exception as e:
        session.close()
        raise DBError("4002")


def get_resource_list(resource_type):
    print("Resource_id", resource_type)
    session = conn_db()
    data = {
        "zip_list": [],
        "feature_list": [],
    }

    if resource_type == "0":
        zip_list_obj = session.query(ShopZipFiles).filter(ShopZipFiles.is_delete == 0).all()
        for zip_obj in zip_list_obj:
            superior_obj = session.query(ShopSecondaryMenu).filter(
                ShopSecondaryMenu.id == zip_obj.parent_id,
                ShopSecondaryMenu.is_delete == 0
            ).first()
            data["zip_list"].append((zip_obj.name, zip_obj.id, superior_obj.name ))

    elif resource_type == "1":
        feature_list_obj = session.query(ShopFeatures).filter(ShopFeatures.is_delete == 0, ShopZipFiles.is_common == 0).all()
        for feature_obj in feature_list_obj:
            superior_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.id == feature_obj.character_id,
                ShopZipFiles.is_delete == 0
            ).first()
            if superior_obj is not None:
                data["feature_list"].append((feature_obj.feature_name, feature_obj.id, superior_obj.name))

    elif resource_type == "2":
        zip_list_obj = session.query(ShopZipFiles).filter(ShopZipFiles.is_delete == 0, ShopZipFiles.is_common == 0).all()
        for zip_obj in zip_list_obj:
            data["zip_list"].append((zip_obj.zip_name, zip_obj.id))

        feature_list_obj = session.query(ShopFeatures).filter(ShopFeatures.is_delete == 0, ShopFeatures.is_common== 0).all()
        for feature_obj in feature_list_obj:
            data["feature_list"].append((feature_obj.feature_name, feature_obj.id))

    else:
        session.close()
        raise BaseError("1002")

    session.close()
    return data


def get_all_items():
    session = conn_db()
    data = {
        "zip_list": [],
        "feature_list": [],
        "goods_list": [],
    }

    zip_list_obj = session.query(ShopZipFiles).filter(ShopZipFiles.is_delete == 0).all()
    for zip_obj in zip_list_obj:
        menu_obj = session.query(ShopSecondaryMenu).filter(ShopSecondaryMenu.id == zip_obj.parent_id).first()

        data["zip_list"].append({
            "id": zip_obj.id,
            "name": zip_obj.name,
            "zip_name": zip_obj.zip_name,
            "menu": menu_obj.name,
        })

    feature_list_obj = session.query(ShopFeatures).filter(ShopFeatures.is_delete == 0).all()
    for feature_obj in feature_list_obj:
        character_obj = session.query(ShopZipFiles).filter(ShopZipFiles.id == feature_obj.character_id).first()

        data["feature_list"].append({
            "name": feature_obj.feature_name,
            "id": feature_obj.id,
            "menu": character_obj.name,
            }
        )

    goods_list_obj = session.query(ShopGoods).filter(ShopGoods.is_delete == 0).all()
    for goods_obj in goods_list_obj:
        data["goods_list"].append({
            "id": goods_obj.id,
            "name": goods_obj.goods_name,
            "menu": goods_obj.menu_path,
        })

    print("data", data)

    session.close()
    return data


def get_secondary_menu(main_menu_id):
    session = conn_db()
    data = {
        "zip_list": [],
        "feature_list": [],
    }
    try:
        secondary_menu_list = session.query(ShopSecondaryMenu).filter(
            ShopSecondaryMenu.parent_id == main_menu_id,
            ShopSecondaryMenu.is_delete == 0,
        ).all()

        for secondary_menu_obj in secondary_menu_list:
            print(">>>", secondary_menu_obj.name, secondary_menu_obj.id)
            data["zip_list"].append((secondary_menu_obj.name, secondary_menu_obj.id))

        zip_obj_list = session.query(ShopZipFiles).filter(ShopZipFiles.is_delete==0).all()

        for zip_obj in zip_obj_list:
            package_obj = session.query(ShopSecondaryMenu).filter(ShopSecondaryMenu.id == zip_obj.parent_id).first()
            print("package_obj.parent_id", type(package_obj.parent_id), package_obj.parent_id)
            if package_obj.parent_id == 1:
                data["feature_list"].append((zip_obj.name, zip_obj.id))

    except Exception as e:
        session.close()
        raise DBError("4005")

    session.close()
    return data


def get_video_list(username):
    session = conn_db()
    try:
        user_obj = session.query(ShopUser).filter(
            ShopUser.phonenum == username,
        ).first()

        if user_obj is None:
            session.close()
            raise DBError("4004")
        uid = user_obj.id



        data = {}
        video_obj_list = session.query(ShopViewVideo).filter(ShopViewVideo.uid==uid, ShopViewVideo.is_delete==0).all()
        for video_obj in video_obj_list:
            data[video_obj.title] = {
                "id": video_obj.id,
                "version": video_obj.version,
                "video_name": video_obj.video_name,
                "video_download_url": os.path.join("download", video_obj.video_name),
                "img_path": video_obj.img_path,
                "img_download_url": os.path.join("download", video_obj.img_path),
                "description": video_obj.description,
                "create_time": str(video_obj.create_time),
            }

        session.close()
        return data

    except Exception as e:
        session.close()
        raise DBError("4005")


def create_feature(character_id, feature_name, feature_flag, description, is_common, username):

    is_exists = check_if_character_exists(character_id)
    session = conn_db()
    if not is_exists:
        session.close()
        raise DBError("4004")

    session = conn_db()
    type_obj = session.query(ShopFeatures).filter(
        ShopFeatures.character_id == character_id,
        ShopFeatures.feature_name == feature_name
    ).first()

    if type_obj is not None:
        if type_obj.is_delete == 0:
            session.close()
            raise DBError("4003")
        else:
            type_obj.is_delete = 0
            session.commit()
            feature_id = type_obj.id
            session.close()
            return feature_id
    try:
        uid = get_user_id(username)
        feature_flag = 1 if feature_flag is None else feature_flag
        print(type(description), description)
        print(">>>>", feature_name, character_id, feature_name, feature_flag, is_common, description)
        new_feature = ShopFeatures(
            owner_id=uid,
            character_id=character_id,
            feature_name=feature_name,
            feature_flag=feature_flag,
            is_common=int(is_common),
            description=description,
        )
        session.add(new_feature)
        session.commit()

        feature_id = new_feature.id
        print(feature_id)

        session.close()
        return feature_id

    except Exception as e:
        print(e)
        session.close()
        raise DBError("4002")


def create_new_goods(goods_name, goods_type, zip_id, feature_id, goods_price, discount, short_desc, description, is_discount):
    try:
        session = conn_db()
        print("!!!!! ", goods_name, goods_type, zip_id, feature_id, goods_price, discount, short_desc, description, is_discount)

        is_discount = 0 if is_discount is None else is_discount
        if not isinstance(goods_type, int):
            goods_type = int(goods_type)

        if goods_type == GoodsType.ZIP.value:
            zip_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.id == zip_id,
            ).first()

            secondary_id = zip_obj.parent_id
            secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
                ShopSecondaryMenu.id == secondary_id,
            ).first()

            if secondary_menu_obj is None:
                session.close()
                raise ShopError("7003")

            secondary_menu_name = secondary_menu_obj.name
            main_id = secondary_menu_obj.parent_id
            main_menu_obj = session.query(ShopMainMenu).filter(
                ShopMainMenu.id == main_id,
            ).first()
            if main_menu_obj is None:
                session.close()
                raise ShopError("7004")

            main_menu_name = main_menu_obj.name

        elif goods_type == GoodsType.FEATURE.value:   # feature

            feature_obj = session.query(ShopFeatures).filter(
                ShopFeatures.id == feature_id,
            ).first()
            secondary_id = feature_obj.character_id
            print("NEW ID: ", type(secondary_id), secondary_id)
            secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
                ShopSecondaryMenu.id == secondary_id,
            ).first()

            if secondary_menu_obj is None:
                session.close()
                raise ShopError("7003")

            secondary_menu_name = secondary_menu_obj.name
            main_menu_name = "Feature"


        else:
            session.close()
            raise BaseError("1002")

        # menu_path = f"{main_menu_name}_{secondary_menu_name}"

        # 加上主类型
        new_goods = ShopGoods(
            goods_name=goods_name,
            goods_type=goods_type,
            zip_id=zip_id,
            feature_id=feature_id,
            menu_path=main_menu_name,
            goods_price=goods_price,
            discount=discount,
            short_desc=short_desc,
            description=description,
            is_discount=bool(is_discount),
        )

        session.add(new_goods)
        session.commit()

        goods_id = new_goods.id

        session.close()
        return goods_id

    except Exception as e:
        print(e)
        session.close()
        raise DBError("4002")


def delete_multi_resource(resource_type, resource_list):
    waring_list = list()
    print(resource_list, type(resource_list))
    if isinstance(resource_list, str):
        resource_list = resource_list.split(",")

    for resource_id in resource_list:
        if not isinstance(resource_id, int):
            resource_id = int(resource_id)

        warning_name = delete_resource(resource_type, resource_id, is_multi=True)
        if warning_name is not None:
            waring_list.append(warning_name)

    return waring_list


def delete_resource(resource_type, resource_id, is_multi=False):
    try:
        session = conn_db()

        if not isinstance(resource_type, int):
            resource_type = int(resource_type)

        if resource_type == DeleteType.ZIP.value:
            zip_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.id == resource_id).first()
            if zip_obj is None:
                session.close()
                raise DBError("4004")
            else:
                subordinate_obj = session.query(ShopGoods).filter(
                    ShopGoods.zip_id == zip_obj.id,
                    ShopGoods.is_delete == 0
                ).first()
                if subordinate_obj is not None:
                    session.close()
                    if not is_multi:
                        raise DBError("4006")
                    else:
                        return zip_obj.name

                zip_obj.is_delete = 1

        elif resource_type == DeleteType.FEATURE.value:
            feature_obj = session.query(ShopFeatures).filter(
                ShopFeatures.id == resource_id).first()

            if feature_obj is None:
                session.close()
                raise DBError("4004")
            else:
                subordinate_obj = session.query(ShopGoods).filter(
                    ShopGoods.feature_id == feature_obj.id,
                    ShopGoods.is_delete == 0).first()
                if subordinate_obj is not None:
                    session.close()
                    if not is_multi:
                        raise DBError("4006")
                    else:
                        return feature_obj.feature_name

                feature_obj.is_delete = 1

        elif resource_type == DeleteType.GOODS.value:
            goods_obj = session.query(ShopGoods).filter(
                ShopGoods.id == resource_id).first()

            if goods_obj is None:
                session.close()
                raise DBError("4004")
            else:
                goods_obj.is_delete = 1

        elif resource_type == DeleteType.SECONDARY_MENU.value:
            package_obj = session.query(ShopSecondaryMenu).filter(
                ShopSecondaryMenu.id == resource_id).first()

            if package_obj is None:
                session.close()
                raise DBError("4004")
            else:
                subordinate_obj = session.query(ShopZipFiles).filter(
                    ShopZipFiles.parent_id == package_obj.id,
                    ShopZipFiles.is_delete == 0
                ).first()
                if subordinate_obj is not None:
                    session.close()
                    if not is_multi:
                        raise DBError("4006")
                    else:
                        return package_obj.name

                package_obj.is_delete = 1

        elif resource_type == DeleteType.VIEW_VIDEO.value:
            view_obj = session.query(ShopViewVideo).filter(
                ShopViewVideo.id == resource_id,
            ).first()
            if view_obj is None:
                session.close()
                raise DBError("4006")

            view_obj.is_delete = 1

        else:
            session.close()
            raise BaseError("1002")

        session.commit()
        session.close()
    except Exception as e:
        print("!!!!!", e)


def check_is_related(user_id):
    session = conn_db()
    user_obj = session.query(ShopUser).filter(ShopUser.id == user_id).first()

    data = False
    if user_obj is not None:
        data = user_obj.phonenum

    session.commit()
    session.close()

    return data


def generate_zip_path(zip_id, goods_id, username):
    print(f"zip id: {zip_id} goods id: {goods_id} username: {username}")
    uid = get_user_id(username)
    session = conn_db()
    if zip_id is not None:
        zip_obj = session.query(ShopZipFiles).filter(
            ShopZipFiles.id == zip_id,
            ShopZipFiles.is_delete == 0
        ).first()
        if zip_obj is None:
            session.close()
            raise DBError("4004")

        # zip_id = zip_obj.id
        zip_name = zip_obj.zip_name
        goods_obj = session.query(ShopGoods).filter(ShopGoods.zip_id == zip_id).first()
        if goods_obj is None:
            session.close()
            raise DBError("4004")   # 商品不存在

        goods_id = goods_obj.id

    elif goods_id is not None:
        goods_obj = session.query(ShopGoods).filter(ShopGoods.id == goods_id).first()
        if goods_obj is None:
            session.close()
            raise DBError("4004")

        goods_id = goods_obj.id

        zip_id = goods_obj.zip_id
        if zip_id is None:
            session.close()
            raise PersonalItemError("8001")

        zip_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.id == zip_id,
                ShopZipFiles.is_delete == 0
            ).first()

        if zip_obj is None:
            session.close()
            raise DBError("4004")

        zip_name = zip_obj.zip_name

    else:
        session.close()
        raise BaseError("1001")     # Todo: 传参错误

    personal_item_obj = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
        ShopPersonalItems.item_id == goods_id,
    ).first()

    if personal_item_obj is None:
        session.close()
        raise PersonalItemError("8000")     # 当前用户未购买此商品

    session.close()
    return zip_name


def count_registered_user(old_users_list):
    session = conn_db()

    register_amount = session.query(func.count(distinct(ShopUser.id))).filter(
        *[ShopUser.phonenum != name for name in TEST_USER]
    ).scalar()

    # access_sum = session.query(func.sum(distinct(ShopUser.access_times))).filter(
    #     *[ShopUser.phonenum != name for name in TEST_USER]
    # ).scalar()
    #
    # avg_counts = int(access_sum / total)

    usage_amount = session.query(func.count(distinct(ShopUser.id))).filter(
        and_(
        *[ShopUser.phonenum != name for name in TEST_USER],
        or_(
            *[ShopUser.phonenum == name for name in old_users_list],
            ShopUser.access_times > 0,
        ))
    ).scalar()

    day_time = date.today()

    today_usage_amount = session.query(func.count(distinct(ShopUser.id))).filter(
        *[ShopUser.phonenum != name for name in TEST_USER],
        ShopUser.last_access_time > day_time
    ).scalar()

    print(">>>", today_usage_amount)

    session.close()
    return register_amount, usage_amount, today_usage_amount


def count_internal_user():
    session = conn_db()
    utc_time = datetime.utcnow()

    internal_user_amount = session.query(func.count(ShopMember.id)).filter(
        ShopMember.senior_expire_time >= utc_time + timedelta(days=1*12*30),
    ).scalar()
    old_test_user = len(TEST_USER)
    print("!!!!!", internal_user_amount)
    return internal_user_amount + old_test_user


def generate_user_dict(user_list_obj, access_count_list=None):
    data = []
    for user_obj in user_list_obj:
        user = user_obj.phonenum
        if access_count_list is None:
            old_access_count = 0
        else:
            old_access_count = int(access_count_list[user]) if user in access_count_list else 0

        register_time = str(user_obj.register_time).split(" ")[0]
        access_times = user_obj.access_times
        if user_obj.last_access_time == "0" or user_obj.last_access_time is None:
            last_access_time = "--"
        else:
            last_access_time = user_obj.last_access_time
        # last_access_time = user_obj.last_access_time if user_obj.last_access_time != "0" else "--"
        # access_count = int(access_times) + old_access_count if old_access_count > 0 else int(access_times)

        total_time = access_times * 60
        data.append({
            "user": user,
            "access_count": access_times,
            "old_access_count": old_access_count,
            "last_access_time": last_access_time,
            "register_time": register_time,
            "total_time": total_time,
        })
    return data


def get_registered_user_info(start, end, access_count_list):
    session = conn_db()

    # user_list_obj = session.query(ShopUser).filter(
    #     *[ShopUser.phonenum != name for name in TEST_USER]
    # ).order_by(ShopUser.id.desc())[start:end]

    utc_time = datetime.utcnow()
    user_list_obj = session.query(ShopUser).filter(
        *[ShopUser.phonenum != name for name in TEST_USER]).join(ShopMember).filter(
        ShopMember.senior_expire_time <= utc_time + timedelta(days=30 * 12 * 100),
    ).order_by(ShopUser.id.desc())

    data = generate_user_dict(user_list_obj, access_count_list)

    return data


def get_internal_user_info(start, end):
    session = conn_db()
    utc_time = datetime.utcnow()
    internal_list = []

    internal_list_obj = session.query(ShopMember).filter(
        ShopMember.senior_expire_time >= utc_time + timedelta(days=1 * 12 * 30)
    ).all()

    for internal_obj in internal_list_obj:
        internal_list.append(internal_obj.id)

    user_list_obj = session.query(ShopUser).filter(
        or_(
            *[ShopUser.phonenum == name for name in TEST_USER],
            *[ShopUser.id == id for id in internal_list],
        )
    ).order_by(ShopUser.id.desc())[start:end]

    data = generate_user_dict(user_list_obj)

    return data


def record_access_times(username):
    session = conn_db()
    user_obj = session.query(ShopUser).filter(
        ShopUser.phonenum == username,
    ).first()

    if user_obj is None:
        session.close()
        raise AuthError("1002")

    if user_obj.access_times is None:
        user_obj.access_times = 0

    user_obj.access_times += 1
    session.commit()
    session.close()


def renewal_membership(username, package_name=None):
    uid = get_user_id(username)
    session = conn_db()

    handsel_member(username, package_name=package_name)

    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
    ).first()

    data = {
        "username": username,
        "expire_time": member_obj.senior_expire_time
    }

    session.close()
    return data


def modify_user_permission(username, persisson):
    uid = get_user_id(username)
    session = conn_db()

    if not isinstance(persisson, int):
        persisson = int(persisson)

    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
    ).first()

    if member_obj is None:
        session.close()
        raise AuthError("1011")

    if member_obj.is_expired == 1:
        session.close()
        raise AuthError("1011")

    prev_permission = member_obj.grade_type

    if (prev_permission == persisson):
        raise AuthError("1014")

    member_obj.grade_type = persisson
    session.commit()
    data = {
        "username": username,
        "permission": member_obj.grade_type,
        "prev_permission": prev_permission,
    }
    session.close()
    return data


def update_goods_info(goods_id, goods_name, price, discount, short_desc, product_desc, is_discount):
    try:
        session = conn_db()
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.id == goods_id).first()

        if goods_obj is None:
            session.close()
            raise DBError("4004")

        if goods_name is not None:
            goods_obj.goods_name = goods_name

        if price is not None:
            goods_obj.goods_price = price

        if discount is not None:
            goods_obj.discount = discount

        if short_desc is not None:
            goods_obj.short_desc = short_desc

        if product_desc is not None:
            goods_obj.description = product_desc

        print(type(is_discount), is_discount)
        print("Before", goods_obj.goods_name, goods_obj.goods_price, goods_obj.is_discount)

        goods_obj.is_discount = int(is_discount)
        session.commit()
        print("After", goods_obj.goods_name, goods_obj.goods_price, goods_obj.is_discount)
        session.close()

    except Exception as e:
        print("!!!!!1", e)
        # raise Exception


def update_zip_info(zip_id, name, menu_id, is_common, is_component, is_related_product, main_menu_id, new_resource_name, userlist):
    try:
        session = conn_db()

        if zip_id != "undefined":
            zip_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.id == zip_id).first()
        else:
            zip_obj = session.query(ShopZipFiles).filter(
                ShopZipFiles.name == name).first()

        if zip_obj is None:
            session.close()
            raise DBError("4004")

        zip_id = zip_obj.id
        # if name is not None:
        #     zip_obj.name = new_resource_name

        if menu_id is not None and menu_id != "undefined":
            zip_obj.parent_id = menu_id

        if is_common is not None:
            zip_obj.is_common = is_common

        if is_component is not None:
            zip_obj.is_component = is_component

        if new_resource_name is not None:
            zip_obj.name = new_resource_name

        bind_custom_items(userlist, zip_id, GoodsType.ZIP.value)

        session.commit()
        session.close()

    except Exception as e:
        print("Update zip info error:", e)
        raise ShopError("7013")


def update_feature_info(feature_id, name, character_id, is_common):
    try:
        session = conn_db()
        feature_obj = session.query(ShopFeatures).filter(
            ShopFeatures.id == feature_id
        ).first()

        if feature_obj is None:
            session.close()
            raise DBError("4004")

        if name is not None:
            feature_obj.feature_name = name

        if is_common is not None:
            feature_obj.is_common = is_common

        if character_id is not None:
            feature_obj.character_id = character_id

        session.commit()
        session.close()

    except Exception as e:
        print("Update feature info error:", e)
        raise ShopError("7013")


def get_single_zip_info(zip_id, zip_name=None):
    session = conn_db()
    if zip_id is not None:
        zip_obj = session.query(ShopZipFiles).filter(
            ShopZipFiles.id == zip_id).all()
    else:
        zip_obj = session.query(ShopZipFiles).filter(
            ShopZipFiles.name == zip_name).all()

    if len(zip_obj) == 0:
        raise DBError("4004")

    data = generate_zip_dict(zip_obj, zip_bought_list=dict())
    return data


def get_single_feature_info(feature_id, feature_name=None):
    session = conn_db()
    if feature_id is not None:
        feature_obj = session.query(ShopFeatures).filter(
            ShopFeatures.id == feature_id).all()

    else:
        feature_obj = session.query(ShopFeatures).filter(
            ShopFeatures.feature_name == feature_name).all()

    if len(feature_obj) == 0:
        raise DBError("4004")

    data = generate_feature_dict(feature_obj, feature_bought_list=dict())
    return data


def check_user_exists(username, authority):
    """

    :param username:
    :param authority: 0: 定制资源  1: 公共资源(登录可见，原免费资源)  2: VIP 资源  3: 内部定制资源
    :return:
    """
    session = conn_db()
    user_exists = session.query(ShopUser).filter(ShopUser.phonenum == username).first()
    if user_exists is None:
        session.close()
        raise AuthError("1002")

    uid = get_user_id(username)
    if not isinstance(authority, int):
        authority = int(authority)

    if authority == ResourceType.COMMON_RESOURCE.value or authority == ResourceType.VIP_RESOURCE.value:
        raise Exception

    member_obj = session.query(ShopMember).filter(ShopMember.uid == uid).first()
    if member_obj is None:
        raise Exception

    if authority == ResourceType.CUSTOM_RESOURCE.value:
        if member_obj.grade_type != MemberLevel.CUSTOM_USER.value:
            raise AuthError("1016")

    elif authority == ResourceType.INTERNAL_COMMON_RESOURCE.value:
        if member_obj.grade_type != MemberLevel.INTERNAL_CUSTOM_USER.value:
            raise AuthError("1015")

    session.close()
    return True


def get_bind_user_list(resource_id, resource_type):
    session = conn_db()
    item_obj_list = session.query(ShopCustomItems).filter(
        ShopCustomItems.resource_id == resource_id,
        ShopCustomItems.resource_type == resource_type,
    ).all()

    data = list()
    for item_obj in item_obj_list:
        uid = item_obj.uid
        user_obj = session.query(ShopUser).filter(ShopUser.id == uid).first()
        if user_obj is not None:
            data.append({
                "uid": uid,
                "username": user_obj.phonenum,
            })

    return data


def update_user_type(username, user_type):
    uid = get_user_id(username)
    session = conn_db()
    member_obj = session.query(ShopMember).filter(ShopMember.uid == uid).first()
    if member_obj is not None:
        if not isinstance(user_type, int):
            user_type = int(user_type)
        member_obj.grade_type = user_type
        session.commit()

    session.close()


def modify_record_permission(username, permission):
    uid = get_user_id(username)
    session = conn_db()

    if not isinstance(permission, int):
        persisson = int(permission)

    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
    ).first()

    if member_obj is None:
        session.close()
        raise AuthError("1011")

    if member_obj.is_expired == 1:
        session.close()
        raise AuthError("1011")

    prev_permission = member_obj.record_permission

    if (prev_permission == permission):
        raise AuthError("1014")

    member_obj.record_permission = permission
    session.commit()
    data = {
        "username": username,
        "permission": member_obj.record_permission,
        "prev_permission": prev_permission,
    }
    session.close()
    return data


def get_record_right(username):
    session = conn_db()
    uid = get_user_id(username)

    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
    ).first()

    if member_obj is None:
        session.close()
        raise AuthError("1011")

    record_permission = member_obj.record_permission

    session.close()
    return record_permission