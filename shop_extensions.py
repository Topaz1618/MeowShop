import os
import math
from time import time
from sqlalchemy import distinct, func, or_, and_

from config import NEW_PRODUCT_DURATION, PRODUCT_PAGE_LIMIT, MYHEART_PAGE_LIMIT, MYITEMS_PAGE_LIMIT
from shop_enum import GoodsType, AuthorityLevel, MemberLevel, ResourceType
from shop_utils import string_to_ts, get_filter_str
from code import AuthError, BaseError, ShopError, DBError, TokenError
from base_extensions import get_user_id
from models import conn_db, ShopZipFiles, ShopFeatures, ShopSecondaryMenu, ShopMainMenu, ShopMember, \
    ShopGoods, ShopPersonalItems, ShopMyHeartItems, ShopCustomItems


def check_is_member(uid):
    session = conn_db()
    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
        ShopMember.is_expired == False,
    ).first()

    if not member_obj:
        session.close()
        raise AuthError("1012")

    session.close()


# def check_if_goods_exists(goods_name):
#     session = conn_db()
#     goods_obj = session.query(ShopGoods).filter(
#         ShopGoods.goods_name == goods_name,
#         ShopGoods.is_delete == 0,
#     ).first()
#     if goods_obj is None:
#         session.close()
#         return False
#
#     session.close()
#     return True


def check_is_bought(uid, goods_id):
    session = conn_db()
    bought_obj = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
        ShopPersonalItems.item_id == goods_id,
    ).first()
    if bought_obj is None:
        return False
    else:
        return True


def get_user_info(username):
    uid = get_user_id(username)
    session = conn_db()
    data = {}
    member_obj = session.query(ShopMember).filter(
        ShopMember.uid == uid,
    ).first()
    if member_obj is None:
        data["is_member"] = False
    else:
        data["is_member"] = True
        data["recharge_time"] = str(member_obj.recharge_time)
        data["member_level"] = member_obj.grade_type
        expire_time = member_obj.junior_expire_time if member_obj.grade_type == 1 else member_obj.senior_expire_time
        data["expire_time"] = str(expire_time)
        data["is_expired"] = member_obj.is_expired

    session.close()
    print("data", data)
    return data


def get_goods_name(goods_id):
    session = conn_db()
    goods_obj = session.query(ShopGoods).filter(
        ShopGoods.id == goods_id,
    ).first()
    if goods_obj is None:
        session.close()
        raise DBError("4004")

    goods_name = goods_obj.goods_name
    session.close()
    return goods_name


def get_total_num():
    try:
        session = conn_db()
        total = session.query(func.count(distinct(ShopGoods.id))).filter(
            ShopGoods.is_delete == 0,
        ).scalar()

        session.close()
        return total
    except Exception as e:
        raise DBError("4007")


def get_my_heart_num(uid):
    session = conn_db()
    total = session.query(func.count(distinct(ShopMyHeartItems.id))).filter(
        ShopMyHeartItems.uid == uid,
        ShopMyHeartItems.is_delete == 0,
    ).scalar()

    session.close()
    return total


def get_myitems_num(uid):
    session = conn_db()
    total = session.query(func.count(distinct(ShopPersonalItems.id))).filter(
        ShopPersonalItems.uid == uid,
    ).scalar()

    session.close()
    return total


def paging_goods_list(filter_list):
    try:
        session = conn_db()

        print(f"Before: {time()}")

        total = session.query(func.count(distinct(ShopGoods.id))).filter(
            ShopGoods.is_delete == 0,
            or_(*[ShopGoods.menu_path == name for name in filter_list]),
        ).scalar()

        print(f"After: {time()} {total}")
        session.close()
        return total
    except Exception as e:
        raise DBError("4008")


def get_component_total_counts(menu):
    session = conn_db()

    menu_obj = session.query(ShopSecondaryMenu).filter(
        ShopSecondaryMenu.name == menu,
    ).first()

    if menu_obj is None:
        session.close()
        raise ShopError("7003")

    menu_id = menu_obj.id

    total = session.query(func.count(distinct(ShopZipFiles.id))).filter(
        ShopZipFiles.parent_id == menu_id,
        ShopZipFiles.is_delete == False,
    ).scalar()

    session.close()
    return total


def get_resource_total_counts(goods_type, uid=None):
    session = conn_db()

    if goods_type == GoodsType.FEATURE:
        print(f"Before: {time()}")
        total = session.query(func.count(distinct(ShopFeatures.id))).filter(
            ShopFeatures.is_delete == False,
        ).scalar()

    elif goods_type == GoodsType.ZIP:
        if uid is None:
            total = session.query(func.count(distinct(ShopZipFiles.id))).filter(
                ShopZipFiles.is_delete == False,
            ).scalar()
        else:
            if not isinstance(uid, int):
                uid = int(uid)

            member_obj = session.query(ShopMember).filter(
                ShopMember.uid == uid,
            ).first()

            if member_obj is None:
                raise TokenError("5006")

            user_level = member_obj.grade_type

            if user_level == MemberLevel.INTERNAL_USER.value:
                total = session.query(func.count(distinct(ShopZipFiles.id))).filter(
                    ShopZipFiles.is_delete == False,
                ).scalar()

            elif user_level == MemberLevel.CUSTOM_USER.value:
                all_custom_items = session.query(ShopCustomItems).filter(
                    ShopCustomItems.uid == uid,
                    ShopCustomItems.resource_type == GoodsType.ZIP.value,
                ).all()

                custom_list = list()
                type_list = [ResourceType.COMMON_RESOURCE.value, ResourceType.VIP_RESOURCE.value]
                for zid in all_custom_items:
                    custom_list.append(zid.resource_id)

                total = session.query(func.count(distinct(ShopZipFiles.id))).filter(
                    ShopZipFiles.is_delete == False,
                    or_(
                        *[ShopZipFiles.is_common == type_id for type_id in type_list],
                        *[ShopZipFiles.id == id for id in custom_list],
                    )
                ).scalar()

            elif user_level == MemberLevel.SENIOR_MEMBER.value:
                type_list = [ResourceType.COMMON_RESOURCE.value, ResourceType.VIP_RESOURCE.value]

                total = session.query(func.count(distinct(ShopZipFiles.id))).filter(
                    ShopZipFiles.is_delete == False,
                    or_(
                        *[ShopZipFiles.is_common == type_id for type_id in type_list],
                    )
                ).scalar()

            elif user_level == MemberLevel.INTERNAL_CUSTOM_USER.value:
                type_list = [ResourceType.COMMON_RESOURCE.value, ResourceType.VIP_RESOURCE.value, ResourceType.INTERNAL_COMMON_RESOURCE.value]

                total = session.query(func.count(distinct(ShopZipFiles.id))).filter(
                    ShopZipFiles.is_delete == False,
                    or_(*[ShopZipFiles.is_common == type_id for type_id in type_list],)
                ).scalar()

    else:
        raise BaseError("1002")

    print(f"After: {time()} {total}")
    session.close()
    return total


def count_goods_type():
    try:
        session = conn_db()

        goods_count_list = dict()

        main_menu_list = session.query(ShopMainMenu).all()
        for main_menu in main_menu_list:
            current_menu = main_menu.name
            print(current_menu)
            current_menu_count = session.query(func.count(distinct(ShopGoods.id))).filter(
                ShopGoods.is_delete == 0,
                ShopGoods.menu_path == current_menu,
            ).scalar()
            goods_count_list[current_menu] = current_menu_count

        current_menu_count = session.query(func.count(distinct(ShopGoods.id))).filter(
            ShopGoods.is_delete == 0,
            ShopGoods.menu_path == "Feature",
        ).scalar()
        goods_count_list["Feature"] = current_menu_count

        print(">>> ", goods_count_list)
        session.close()
        return goods_count_list
    except Exception as e:
        raise ShopError("7011")


def generate_bought_list(uid):
    feature_bought_list = list()
    zip_bought_list = list()
    session = conn_db()

    personal_obj_list = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
    ).all()

    for personal_obj in personal_obj_list:
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.id == personal_obj.item_id,
        ).first()
        if goods_obj is None:
            session.close()
            raise DBError("4004")

        if goods_obj.goods_type == GoodsType.FEATURE.value:
            feature_bought_list.append(goods_obj.feature_id)

        elif goods_obj.goods_type == GoodsType.ZIP.value:
            zip_bought_list.append(goods_obj.zip_id)

    session.close()

    return feature_bought_list, zip_bought_list


def get_good_info(resource_id, goods_type):
    session = conn_db()
    goods_info = {"is_related_product": False}

    if goods_type == GoodsType.ZIP:
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.zip_id == resource_id,
            ShopGoods.goods_type == 0,
        ).first()

    elif goods_type == GoodsType.FEATURE:
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.goods_type == 1,
            ShopGoods.feature_id == resource_id,
        ).first()

    else:
        raise BaseError("1002")

    if goods_obj is not None:
        goods_info = {
            "goods_id": goods_obj.id,
            "goods_name": goods_obj.goods_name,
            "goods_price": goods_obj.goods_price,
            "is_related_product": True,
        }

    return goods_info


def generate_zip_dict(zip_obj_list, zip_bought_list):
    data = []
    session = conn_db()
    for zip_obj in zip_obj_list:

        secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
            ShopSecondaryMenu.id == zip_obj.parent_id,
        ).first()

        if secondary_menu_obj is None:
            session.close()
            raise ShopError("7003")

        secondary_menu = secondary_menu_obj.name
        secondary_menu_id = secondary_menu_obj.id

        main_menu_obj = session.query(ShopMainMenu).filter(
            ShopMainMenu.id == secondary_menu_obj.parent_id,
        ).first()
        if main_menu_obj is None:
            session.close()
            raise ShopError("7004")

        main_menu = main_menu_obj.name
        main_menu_id = main_menu_obj.id

        zip_id = zip_obj.id
        is_bought = True if zip_id in zip_bought_list else False
        goods_info = get_good_info(zip_id, GoodsType.ZIP)

        data.append({
            "id": zip_obj.id,
            "name": zip_obj.name,
            "zip_name": zip_obj.zip_name,
            "main_menu_id": main_menu_id,
            "main_menu": main_menu,
            "secondary_menu_id": secondary_menu_id,
            "secondary_menu": secondary_menu,
            'classification_info': f'{main_menu}+{secondary_menu}',
            'classification_value': 1,
            # "parent_id": i.parent_id,
            "img_path": f"static/images/shop/{zip_obj.img_path}",
            "Authority": zip_obj.is_common,  # 0: 付费, 1: 免费 2: 会员付费
            "create_time": str(zip_obj.create_time),
            "description": zip_obj.description,
            "is_component": zip_obj.is_component,
            "is_bought": is_bought,
            "goods_info": goods_info,
        })

    session.close()
    return data


def generate_feature_dict(feature_obj_list, feature_bought_list):
    data = []
    session = conn_db()
    for feature_obj in feature_obj_list:

        character_obj = session.query(ShopZipFiles).filter(
            ShopZipFiles.id == feature_obj.character_id,
        ).first()

        if character_obj is None:
            session.close()
            raise ShopError("7005")

        character = character_obj.zip_name
        if character.endswith(".zip"):
            character = character.split(".zip")[0]
        character_id = character_obj.id

        secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
            ShopSecondaryMenu.id == character_obj.parent_id,
        ).first()

        if secondary_menu_obj is None:
            session.close()
            raise ShopError("7003")

        secondary_menu = secondary_menu_obj.name
        secondary_menu_id = secondary_menu_obj.id

        feature_id = feature_obj.id
        is_bought = True if feature_id in feature_bought_list else False

        goods_info = get_good_info(feature_id, GoodsType.FEATURE)

        data.append({
            "id": feature_obj.id,
            "name": feature_obj.feature_name,
            "Authority": feature_obj.is_common,
            "secondary_menu": secondary_menu,
            "secondary_menu_id": secondary_menu_id,
            "character": character,
            "character_id": character_id,
            "classification_info": f"{secondary_menu}",
            "classification_value": 1,
            "feature_flag": feature_obj.feature_flag,
            "description": feature_obj.description,
            "create_time": str(feature_obj.create_time),
            "is_bought": is_bought,
            "goods_info": goods_info,
        })

    session.close()
    return data

# 保留, 购买用逻辑(2021.5.20 之前修改)
# def generate_zip_items(uid, start, end):
#
#     check_is_member(uid)
#
#     _, zip_bought_list = generate_bought_list(uid)
#
#     session = conn_db()
#     zip_obj_list = session.query(ShopZipFiles).filter(
#         ShopZipFiles.is_delete == False,)[start:end]
#
#     data = generate_zip_dict(zip_obj_list, zip_bought_list)
#
#     session.close()
#     return data


def generate_zip_items(uid, start, end, is_admin=False):
    session = conn_db()

    if is_admin:
        zip_obj_list = session.query(ShopZipFiles).filter(
            ShopZipFiles.is_delete == False,
        )[start:end]   # 0: 定制,  2: VIP

    else:
        if not isinstance(uid, int):
            uid = int(uid)

        member_obj = session.query(ShopMember).filter(
            ShopMember.uid == uid,
            ShopMember.is_expired == 0,
        ).first()

        print(member_obj.id, uid, member_obj.grade_type)

        if member_obj is None:
            session.close()
            raise AuthError("1012")

        member_level = member_obj.grade_type

        if member_level == MemberLevel.INTERNAL_USER.value:
            zip_obj_list = session.query(ShopZipFiles).filter(
                ShopZipFiles.is_delete == False,
            ).all()

        elif member_level == MemberLevel.CUSTOM_USER.value:
            all_custom_items = session.query(ShopCustomItems).filter(
                ShopCustomItems.uid == uid,
                ShopCustomItems.resource_type == GoodsType.ZIP.value,
            ).all()

            custom_list = list()
            type_list = [ResourceType.COMMON_RESOURCE.value, ResourceType.VIP_RESOURCE.value]
            for zid in all_custom_items:
                custom_list.append(zid.resource_id)

            zip_obj_list = session.query(ShopZipFiles).filter(
                ShopZipFiles.is_delete == False,
                or_(
                    *[ShopZipFiles.is_common == type_id for type_id in type_list],
                    *[ShopZipFiles.id == id for id in custom_list],
                )
            ).all()

        elif member_level == MemberLevel.SENIOR_MEMBER.value:
            type_list = [ResourceType.COMMON_RESOURCE.value, ResourceType.VIP_RESOURCE.value]

            zip_obj_list = session.query(ShopZipFiles).filter(
                ShopZipFiles.is_delete == False,
                or_(*[ShopZipFiles.is_common == type_id for type_id in type_list],)
            ).all()

        elif member_level == MemberLevel.INTERNAL_CUSTOM_USER.value:
            type_list = [ResourceType.COMMON_RESOURCE.value, ResourceType.VIP_RESOURCE.value, ResourceType.INTERNAL_COMMON_RESOURCE.value]

            zip_obj_list = session.query(ShopZipFiles).filter(
                ShopZipFiles.is_delete == False,
                or_(*[ShopZipFiles.is_common == type_id for type_id in type_list], )
            ).all()

        else:
            raise AuthError("1012")

    data = []
    session = conn_db()
    for zip_obj in zip_obj_list:
        secondary_menu_obj = session.query(ShopSecondaryMenu).filter(
            ShopSecondaryMenu.id == zip_obj.parent_id,
        ).first()
        if secondary_menu_obj is None:
            session.close()
            raise ShopError("7003")

        secondary_menu = secondary_menu_obj.name
        secondary_menu_id = secondary_menu_obj.id

        main_menu_obj = session.query(ShopMainMenu).filter(
            ShopMainMenu.id == secondary_menu_obj.parent_id,
        ).first()
        if main_menu_obj is None:
            session.close()
            raise ShopError("7004")

        main_menu = main_menu_obj.name
        main_menu_id = main_menu_obj.id

        is_bought = False
        zip_id = zip_obj.id
        goods_info = get_good_info(zip_id, GoodsType.ZIP)

        data.append({
            "id": zip_obj.id,
            "name": zip_obj.name,
            "zip_name": zip_obj.zip_name,
            "main_menu_id": main_menu_id,
            "main_menu": main_menu,
            "secondary_menu_id": secondary_menu_id,
            "secondary_menu": secondary_menu,
            'classification_info': f'{main_menu}+{secondary_menu}',
            'classification_value': 1,
            # "parent_id": i.parent_id,
            "img_path": f"static/images/shop/{zip_obj.img_path}",
            "Authority": zip_obj.is_common,  # 0: 付费, 1: 免费 2: 会员付费
            "create_time": str(zip_obj.create_time),
            "description": zip_obj.description,
            "is_component": zip_obj.is_component,
            "is_bought": is_bought,
            "goods_info": goods_info,
        })

    session.close()


    session.close()
    return data


def generate_feature_items(uid, start, end):
    check_is_member(uid)
    feature_bought_list, _ = generate_bought_list(uid)
    session = conn_db()

    feature_obj_list = session.query(ShopFeatures).filter(
        ShopFeatures.is_delete == False,
    )[start:end]

    data = generate_feature_dict(feature_obj_list, feature_bought_list)

    return data


def get_image_path(zip_id):
    session = conn_db()
    zip_obj = session.query(ShopZipFiles).filter(ShopZipFiles.id == zip_id).first()
    if zip_obj is None:
        session.close()
        raise DBError("4004")

    image_name = zip_obj.img_path
    image_path = os.path.join("static", "images", "shop", image_name)
    session.close()
    return image_path


def generate_goods_dict(goods_list_obj, uid=None):
    try:
        session = conn_db()
        goods_list = list()
        for goods_obj in goods_list_obj:
            goods_type = goods_obj.goods_type
            resource_id = goods_obj.feature_id if goods_type else goods_obj.zip_id

            if int(goods_type) == GoodsType.ZIP.value:
                zip_obj_list = session.query(ShopZipFiles).filter(
                    ShopZipFiles.is_delete == False,
                    ShopZipFiles.id == resource_id,
                ).all()

                data_info_list = generate_zip_dict(zip_obj_list, zip_bought_list=list())
                data_info = data_info_list[0]
                image_path = get_image_path(goods_obj.zip_id)
                main_menu = data_info.get("main_menu")
                secondary_menu = data_info.get("secondary_menu")

            else:
                feature_obj_list = session.query(ShopFeatures).filter(
                    ShopFeatures.is_delete == False,
                    ShopFeatures.id == resource_id,
                ).all()

                data_info_list = generate_feature_dict(feature_obj_list, feature_bought_list=list())
                data_info = data_info_list[0]
                main_menu = "Feature"
                image_path = "static/images/shop/cat_work.png"
                secondary_menu = data_info.get("secondary_menu")

            is_new = False
            if goods_obj.create_time is not None:
                is_new = False if time() - string_to_ts(str(goods_obj.create_time)) > NEW_PRODUCT_DURATION else True

            is_bought = False
            if uid is not None:
                is_bought_obj = session.query(ShopPersonalItems).filter(
                    ShopPersonalItems.uid == uid,
                    ShopPersonalItems.item_id == goods_obj.id).first()

                if is_bought_obj is not None:
                    is_bought = True

            goods_list.append({
                "goods_id": goods_obj.id,
                "goods_name": goods_obj.goods_name,
                "image_path": image_path,
                "goods_type": goods_obj.goods_type,
                "resource_id": resource_id,
                "price": goods_obj.goods_price,
                "discount": goods_obj.discount,
                "is_discount": goods_obj.is_discount,
                "main_menu": main_menu,
                "secondary_menu": secondary_menu,
                "is_new": is_new,
                "is_bought": is_bought,
                "short_desc": goods_obj.short_desc,
                "desc": goods_obj.description,
            })
        session.close()
        return goods_list

    except Exception as e:
        raise ShopError("7010")


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


def get_product_dict(goods_name, uid=None):
    session = conn_db()

    goods_obj = session.query(ShopGoods).filter(
        ShopGoods.goods_name == goods_name,
        ShopGoods.is_delete == 0).all()

    if goods_obj is None or len(goods_obj) == 0:
        session.close()
        raise DBError("4004")

    data = generate_goods_dict(goods_obj, uid)
    session.close()
    return data


def slice_product_data(start, end, is_sort, filter_list, uid, is_filter=None):
    session = conn_db()
    if is_filter is None:
        is_filter = True if not "All" in filter_list else False

    print("filter list: ", filter_list, start, end)
    try:
        if is_sort == "1":  # 降序
            if not is_filter:
                goods_list_obj = session.query(ShopGoods).filter(
                    ShopGoods.is_delete == 0,
                ).order_by(ShopGoods.goods_price.desc())[start:end]
            else:
                goods_list_obj = session.query(ShopGoods).filter(
                    or_(*[ShopGoods.menu_path == name for name in filter_list])).order_by(
                    ShopGoods.goods_price.desc())[start:end]

        elif is_sort == "2":    # 升序
            if not is_filter:
                goods_list_obj = session.query(ShopGoods).filter(
                    ShopGoods.is_delete == 0,
                ).order_by(ShopGoods.goods_price)[start:end]
            else:
                goods_list_obj = session.query(ShopGoods).filter(
                    or_(*[ShopGoods.menu_path == name for name in filter_list])).order_by(
                    ShopGoods.goods_price)[start:end]

        else:
            if not is_filter:
                goods_list_obj = session.query(ShopGoods).filter(
                    ShopGoods.is_delete == 0,
                )[start:end]
            else:
                goods_list_obj = session.query(ShopGoods).filter(
                    or_(*[ShopGoods.menu_path == name for name in filter_list]))[start:end]
    except Exception as e:
        raise ShopError("7009")

    goods_list = generate_goods_dict(goods_list_obj, uid)  # 加个分类列表,

    session.close()
    return goods_list


def get_myheart_list(uid, start=0, end=3, is_shop=False):

    session = conn_db()
    if is_shop:
        # 只获取三个
        myheart_list_obj = session.query(ShopMyHeartItems).filter(
            ShopMyHeartItems.is_delete == 0,
            ShopMyHeartItems.uid == uid,
        )[start:end]
        # 获取全部
    else:
        myheart_list_obj = session.query(ShopMyHeartItems).filter(
            ShopMyHeartItems.is_delete == 0,
            ShopMyHeartItems.uid == uid,
        )[start:end]

    myheart_list = []
    for myheart_obj in myheart_list_obj:
        goods_id = myheart_obj.goods_id
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.id == goods_id,
        ).first()
        if goods_obj.goods_type == GoodsType.ZIP.value:
            image_path = get_image_path(goods_obj.zip_id)
        else:
            image_path = "static/images/shop/cat_work.png"

        myheart_list.append({
            "goods_id": goods_id,
            "goods_name": goods_obj.goods_name,
            "goods_price": goods_obj.goods_price,
            "image_path": image_path,
            "create_time": str(myheart_obj.create_time),
        })

    session.close()
    return myheart_list


def get_myitems_list(uid, start, end):
    session = conn_db()
    myitems_list_obj = session.query(ShopPersonalItems).filter(
        ShopPersonalItems.uid == uid,
    )[start:end]

    myitems_list = []
    for myitems_obj in myitems_list_obj:
        goods_id = myitems_obj.item_id
        goods_obj = session.query(ShopGoods).filter(
            ShopGoods.id == goods_id,
        ).first()
        if goods_obj.goods_type == GoodsType.ZIP.value:
            image_path = get_image_path(goods_obj.zip_id)
        else:
            image_path = "static/images/shop/cat_work.png"

        myitems_list.append({
            "goods_id": goods_id,
            "goods_name": goods_obj.goods_name,
            "goods_price": goods_obj.goods_price,
            "image_path": image_path,
            "desc": goods_obj.short_desc,
            "menu": goods_obj.menu_path,

        })
    return myitems_list


def add_my_heart(username, goods_id):
    uid = get_user_id(username)
    session = conn_db()

    myheart_obj = session.query(ShopMyHeartItems).filter(
        ShopMyHeartItems.uid == uid,
        ShopMyHeartItems.goods_id == goods_id,
        ShopMyHeartItems.is_delete == 0,
    ).first()

    if myheart_obj is not None:
        session.close()
        raise ShopError("7006")

    new_myheart_items = ShopMyHeartItems(
        uid=uid,
        goods_id=goods_id,
    )
    session.add(new_myheart_items)
    session.commit()
    session.close()


def delete_my_heart(username, goods_id):
    uid = get_user_id(username)
    session = conn_db()

    myheart_obj = session.query(ShopMyHeartItems).filter(
        ShopMyHeartItems.uid == uid,
        ShopMyHeartItems.goods_id == goods_id,
        ShopMyHeartItems.is_delete == 0,
    ).first()

    if myheart_obj is None:
        session.close()
        raise ShopError("7007")

    myheart_obj.is_delete = 1

    session.commit()
    session.close()


def get_page_info(current_page, filter_list, is_sort, uid):
    is_filter = True if not "All" in filter_list else False

    total = get_total_num()

    if is_filter:
        total_data = paging_goods_list(filter_list)
    else:
        total_data = total

    total_page = total_data / PRODUCT_PAGE_LIMIT
    total_page = math.ceil(total_page)
    start = (current_page - 1) * PRODUCT_PAGE_LIMIT
    end = total_data if PRODUCT_PAGE_LIMIT * current_page > total_data else PRODUCT_PAGE_LIMIT * current_page

    filter_str = get_filter_str(filter_list) if "All" not in filter_list else "All"

    goods_list = slice_product_data(start, end, is_sort, filter_list, uid)
    print(goods_list)

    page_info = {
        "start": start,
        "end": end,
        "limit": PRODUCT_PAGE_LIMIT,
        "total": total,
        "total_data": total_data,
        "current_page": current_page,
        "total_page": total_page,
        "is_sort": is_sort,
        # "is_filter": is_filter,
        "goods_list": goods_list,
        "filter_str": filter_str,
    }
    return page_info


def generate_component_list(uid, current_menu, start, end):
    check_is_member(uid)
    _, zip_bought_list = generate_bought_list(uid)

    session = conn_db()

    menu_obj = session.query(ShopSecondaryMenu).filter(
        ShopSecondaryMenu.name == current_menu,
    ).first()

    if menu_obj is None:
        session.close()
        raise ShopError("7003")

    menu_id = menu_obj.id

    componet_obj_list = session.query(ShopZipFiles).filter(
        ShopZipFiles.parent_id == menu_id,
        ShopZipFiles.is_component == True,
        # ShopZipFiles.is_component == False,
    )[start:end]

    data = generate_zip_dict(componet_obj_list, zip_bought_list)

    return data









