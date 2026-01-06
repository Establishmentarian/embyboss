from contextlib import contextmanager

from bot import default_package, package_by_level, packages
from bot.sql_helper import reset_db_package, set_db_package


def get_package_key_by_level(lv: str) -> str:
    return package_by_level.get(lv, default_package)


def get_package_config(package_key: str):
    if package_key in packages:
        return packages[package_key]
    return packages[default_package]


def get_line_for_level(lv: str) -> str:
    package_key = get_package_key_by_level(lv)
    package = get_package_config(package_key)
    return package.emby_line


def get_line_for_user(user) -> str:
    if not user:
        return get_line_for_level("b")
    package_key = get_package_key_for_user_record(user)
    package = get_package_config(package_key)
    line = package.emby_line
    if user.lv == "a" and package.emby_whitelist_line:
        line = f"{line}\n{package.emby_whitelist_line}"
    return line


def get_package_key_for_user_record(user) -> str:
    if not user:
        return default_package
    return getattr(user, "_package_key", get_package_key_by_level(user.lv))


@contextmanager
def db_package_context(package_key: str):
    token = set_db_package(package_key)
    try:
        yield
    finally:
        reset_db_package(token)
