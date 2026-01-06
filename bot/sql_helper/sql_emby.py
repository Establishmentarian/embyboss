"""
基本的sql操作
"""
from bot.sql_helper import Base, Session, get_engine, package_keys
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, case
from sqlalchemy import func
from sqlalchemy import or_
from bot import LOGGER



class Emby(Base):
    """
    emby表，tg主键，默认值lv，us，iv
    """
    __tablename__ = 'emby'
    tg = Column(BigInteger, primary_key=True, autoincrement=False)
    embyid = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    pwd = Column(String(255), nullable=True)
    pwd2 = Column(String(255), nullable=True)
    lv = Column(String(1), default='d')
    cr = Column(DateTime, nullable=True)
    ex = Column(DateTime, nullable=True)
    us = Column(Integer, default=0)
    iv = Column(Integer, default=0)
    ch = Column(DateTime, nullable=True)


for _package_key in package_keys():
    Emby.__table__.create(bind=get_engine(_package_key), checkfirst=True)


def sql_add_emby(tg: int, package_key: str = None):
    """
    添加一条emby记录，如果tg已存在则忽略
    """
    with Session(package_key) as session:
        try:
            emby = Emby(tg=tg)
            session.add(emby)
            session.commit()
        except:
            pass

def sql_delete_emby_by_tg(tg, package_key: str = None):
    """
    根据tg删除一条emby记录
    """
    with Session(package_key) as session:
        try:
            emby = session.query(Emby).filter(Emby.tg == tg).first()
            if emby:
                session.delete(emby)
                session.commit()
                LOGGER.info(f"删除数据库记录成功 {tg}")
                return True
            else:
                LOGGER.info(f"数据库记录不存在 {tg}")
                return False
        except Exception as e:
            LOGGER.error(f"删除数据库记录时发生异常 {e}")
            session.rollback()
            return False

def sql_clear_emby_iv(package_key: str = None):
    """
    清除所有emby的iv
    """
    with Session(package_key) as session:
        try:
            session.query(Emby).update({Emby.iv: 0})
            session.commit()
            return True
        except Exception as e:
            LOGGER.error(f"清除所有emby的iv时发生异常 {e}")
            return False

def sql_delete_emby(tg=None, embyid=None, name=None, package_key: str = None):
    """
    根据tg, embyid或name删除一条emby记录
    至少需要提供一个参数，如果所有参数都为None，则返回False
    """
    def _delete_with_session(session):
        try:
            conditions = []
            if tg is not None:
                conditions.append(Emby.tg == tg)
            if embyid is not None:
                conditions.append(Emby.embyid == embyid)
            if name is not None:
                conditions.append(Emby.name == name)

            if not conditions:
                LOGGER.warning("sql_delete_emby: 所有参数都为None，无法删除记录")
                return False

            condition = or_(*conditions)
            LOGGER.debug(f"删除数据库记录，条件: tg={tg}, embyid={embyid}, name={name}")
            emby = session.query(Emby).filter(condition).with_for_update().first()
            if emby:
                LOGGER.info(f"删除数据库记录 {emby.name} - {emby.embyid} - {emby.tg}")
                session.delete(emby)
                try:
                    session.commit()
                    LOGGER.info(f"成功删除数据库记录: tg={tg}, embyid={embyid}, name={name}")
                    return True
                except Exception as e:
                    LOGGER.error(f"删除数据库记录时提交事务失败 {e}")
                    session.rollback()
                    return False
            else:
                LOGGER.info(f"数据库记录不存在: tg={tg}, embyid={embyid}, name={name}")
                return False
        except Exception as e:
            LOGGER.error(f"删除数据库记录时发生异常 {e}")
            session.rollback()
            return False

    if package_key:
        with Session(package_key) as session:
            return _delete_with_session(session)

    for key in package_keys():
        with Session(key) as session:
            result = _delete_with_session(session)
            if result:
                return True
    return False


def sql_update_embys(some_list: list, method=None, package_key: str = None):
    """ 根据list中的tg值批量更新一些值 ，此方法不可更新主键"""
    with Session(package_key) as session:
        if method == 'iv':
            try:
                mappings = [{"tg": c[0], "iv": c[1]} for c in some_list]
                session.bulk_update_mappings(Emby, mappings)
                session.commit()
                return True
            except:
                session.rollback()
                return False
        if method == 'ex':
            try:
                mappings = [{"tg": c[0], "ex": c[1]} for c in some_list]
                session.bulk_update_mappings(Emby, mappings)
                session.commit()
                return True
            except:
                session.rollback()
                return False
        if method == 'bind':
            try:
                # mappings = [{"name": c[0], "embyid": c[1]} for c in some_list] 没有主键不能插入的这是emby表
                mappings = [{"tg": c[0], "name": c[1], "embyid": c[2]} for c in some_list]
                session.bulk_update_mappings(Emby, mappings)
                session.commit()
                return True
            except Exception as e:
                print(e)
                session.rollback()
                return False


def sql_get_emby(tg, package_key: str = None):
    """
    查询一条emby记录，可以根据tg, embyid或者name来查询
    """
    def _get_with_session(session):
        try:
            emby = session.query(Emby).filter(or_(Emby.tg == tg, Emby.name == tg, Emby.embyid == tg)).first()
            return emby
        except:
            return None

    if package_key:
        with Session(package_key) as session:
            return _get_with_session(session)

    for key in package_keys():
        with Session(key) as session:
            emby = _get_with_session(session)
            if emby:
                setattr(emby, "_package_key", key)
                return emby
    return None


# def sql_get_emby_by_embyid(embyid):
#     """
#     Retrieve an Emby object from the database based on the provided Emby ID.
#
#     Parameters:
#         embyid : The Emby ID used to identify the Emby object.
#
#     Returns:
#         tuple: A tuple containing a boolean value indicating whether the retrieval was successful
#                and the retrieved Emby object. If the retrieval was unsuccessful, the boolean value
#                will be False and the Emby object will be None.
#     """
#     with Session() as session:
#         try:
#             emby = session.query(Emby).filter((Emby.embyid == embyid)).first()
#             return True, emby
#         except Exception as e:
#             return False, None


def get_all_emby(condition, package_key: str = None):
    """
    查询所有emby记录
    """
    def _get_all_with_session(session):
        try:
            return session.query(Emby).filter(condition).all()
        except:
            return None

    if package_key:
        with Session(package_key) as session:
            return _get_all_with_session(session)

    all_embies = []
    for key in package_keys():
        with Session(key) as session:
            embies = _get_all_with_session(session)
            if embies:
                all_embies.extend(embies)
    return all_embies


def sql_update_emby(condition, package_key: str = None, **kwargs):
    """
    更新一条emby记录，根据condition来匹配，然后更新其他的字段
    """
    def _update_with_session(session):
        try:
            emby = session.query(Emby).filter(condition).first()
            if emby is None:
                return False
            for k, v in kwargs.items():
                setattr(emby, k, v)
            session.commit()
            return True
        except Exception as e:
            LOGGER.error(e)
            return False

    if package_key:
        with Session(package_key) as session:
            return _update_with_session(session)

    for key in package_keys():
        with Session(key) as session:
            if _update_with_session(session):
                return True
    return False


#
# def sql_change_emby(name, new_tg):
#     with Session() as session:
#         try:
#             emby = session.query(Emby).filter_by(name=name).first()
#             if emby is None:
#                 return False
#             emby.tg = new_tg
#             session.commit()
#             return True
#         except Exception as e:
#             print(e)
#             return False


def sql_count_emby(package_key: str = None):
    """
    # 检索有tg和embyid的emby记录的数量，以及Emby.lv =='a'条件下的数量
    # count = sql_count_emby()
    :return: int, int, int
    """
    def _count_with_session(session):
        try:
            count = session.query(
                func.count(Emby.tg).label("tg_count"),
                func.count(Emby.embyid).label("embyid_count"),
                func.count(case((Emby.lv == "a", 1))).label("lv_a_count")
            ).first()
        except Exception:
            return None, None, None
        return count.tg_count, count.embyid_count, count.lv_a_count

    if package_key:
        with Session(package_key) as session:
            return _count_with_session(session)

    totals = [0, 0, 0]
    for key in package_keys():
        with Session(key) as session:
            counts = _count_with_session(session)
            if counts[0] is None:
                continue
            totals[0] += counts[0]
            totals[1] += counts[1]
            totals[2] += counts[2]
    return tuple(totals)
