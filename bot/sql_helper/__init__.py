"""
初始化数据库
"""
from contextvars import ContextVar
from typing import Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from bot import default_package, packages

# 创建Base对象
Base = declarative_base()

_current_package: ContextVar[Optional[str]] = ContextVar("current_package", default=None)
_engines: Dict[str, object] = {}


def _build_engine(package_key: str):
    package = packages[package_key]
    db_host = package.db_host
    db_user = package.db_user
    db_pwd = package.db_pwd
    db_name = package.db_name
    db_port = package.db_port
    return create_engine(
        f"mysql+pymysql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}?utf8mb4",
        echo=False,
        echo_pool=False,
        pool_size=16,
        pool_recycle=60 * 30,
    )


def _ensure_engine(package_key: str):
    if package_key not in _engines:
        _engines[package_key] = _build_engine(package_key)
        Base.metadata.create_all(bind=_engines[package_key], checkfirst=True)
    return _engines[package_key]


def get_engine(package_key: Optional[str] = None):
    package_key = package_key or default_package
    return _ensure_engine(package_key)


def set_db_package(package_key: Optional[str]):
    return _current_package.set(package_key)


def reset_db_package(token):
    _current_package.reset(token)


def current_package_key() -> str:
    return _current_package.get() or default_package


def package_keys():
    return list(packages.keys())


def Session(package_key: Optional[str] = None):
    key = package_key or current_package_key()
    engine = _ensure_engine(key)
    return sessionmaker(bind=engine, autoflush=False)()

