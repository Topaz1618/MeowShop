import os

from code import BaseError
from shop_enum import CreateType, ZipType, CreateAuthority
from backend_extensions import check_is_admin, check_if_member


def check_create_permissions(username, create_type):
    is_member = check_if_member(username)
    if not is_member:
        raise BaseError("1005")
    if create_type != CreateType.ZIP.value:
        raise BaseError("1005")

    return True


def check_if_creatable(parent_id):
    if not isinstance(parent_id, int):
        parent_id = int(parent_id)

    print("Pid", parent_id)

    if parent_id == ZipType.ACTOR.value:
        is_creatable = CreateAuthority.ACTOR.value

    elif parent_id == ZipType.SCENE.value:
        is_creatable = CreateAuthority.SCENE.value

    elif parent_id == ZipType.ACTION.value:
        is_creatable = CreateAuthority.ACTION.value

    elif parent_id == ZipType.SHOT.value:
        is_creatable = CreateAuthority.SHOT.value

    else:
        raise BaseError("1002")

    if not is_creatable:
        raise BaseError("1005")


def check_access_log(access_log):

    data = list()

    with open(access_log, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break

            line_tmp = line.strip("\n").split(" ")
            ip_addr = line_tmp[-1]
            access_times = line_tmp[-2]
            data.append([ip_addr, access_times])

    return data

