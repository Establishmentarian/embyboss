from contextlib import contextmanager
from typing import Optional, Tuple

from pyromod.helpers import ikb

from bot import default_package, package_by_level, packages, _open
from bot.sql_helper import reset_db_package, set_db_package


def get_package_key_by_level(lv: str) -> str:
    return package_by_level.get(lv, default_package)


def get_package_config(package_key: str):
    if package_key in packages:
        return packages[package_key]
    return packages[default_package]

_OPEN_FIELD_MAP = {
    "open_stat": "stat",
    "open_us": "open_us",
    "open_all_user": "all_user",
    "open_timing": "timing",
    "open_tem": "tem",
    "checkin": "checkin",
    "checkin_lv": "checkin_lv",
    "exchange": "exchange",
    "whitelist": "whitelist",
    "invite": "invite",
    "invite_lv": "invite_lv",
    "leave_ban": "leave_ban",
    "uplays": "uplays",
    "checkin_reward": "checkin_reward",
    "exchange_cost": "exchange_cost",
    "whitelist_cost": "whitelist_cost",
    "invite_cost": "invite_cost",
}


def get_package_open_value(package_key: str, field: str):
    package = get_package_config(package_key)
    if hasattr(package, field):
        value = getattr(package, field)
        if value is not None:
            return value
    fallback = _OPEN_FIELD_MAP.get(field)
    if fallback and hasattr(_open, fallback):
        return getattr(_open, fallback)
    return None


def set_package_open_value(package_key: str, field: str, value):
    package = get_package_config(package_key)
    if hasattr(package, field):
        setattr(package, field, value)
        return
    fallback = _OPEN_FIELD_MAP.get(field)
    if fallback and hasattr(_open, fallback):
        setattr(_open, fallback, value)


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


def resolve_package_key(package_key: Optional[str]) -> str:
    if package_key in packages:
        return package_key
    return default_package


def select_package(
    package_key: Optional[str] = None,
    prefix: str = "manage_pkg",
    back_callback: Optional[str] = "manage",
) -> Tuple[Optional[str], Optional[object]]:
    if package_key:
        return resolve_package_key(package_key), None
    if len(packages) == 1:
        return default_package, None
    rows = [[(f"📦 {key}", f"{prefix}:{key}")] for key in packages.keys()]
    if back_callback:
        rows.append([("🔙 返回", back_callback)])
    return None, ikb(rows)


@contextmanager
def db_package_context(package_key: str):
    token = set_db_package(package_key)
    try:
        yield
    finally:
        reset_db_package(token)
