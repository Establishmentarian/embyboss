from bot.sql_helper import Base, Session, get_engine, package_keys
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy import or_


class Emby2(Base):
    """
    emby表，tg主键，默认值lv，us，iv
    """
    __tablename__ = 'emby2'
    embyid = Column(String(255), primary_key=True, autoincrement=False)
    name = Column(String(255), nullable=True)
    pwd = Column(String(255), nullable=True)
    pwd2 = Column(String(255), nullable=True)
    lv = Column(String(1), default='d')
    cr = Column(DateTime, nullable=True)
    ex = Column(DateTime, nullable=True)
    expired = Column(Integer, nullable=True)


for _package_key in package_keys():
    Emby2.__table__.create(bind=get_engine(_package_key), checkfirst=True)


def sql_add_emby2(embyid, name, cr, ex, pwd='5210', pwd2='1234', lv='b', expired=0, package_key: str = None):
    """
    添加一条emby记录，如果tg已存在则忽略
    """
    with Session(package_key) as session:
        try:
            emby = Emby2(embyid=embyid, name=name, pwd=pwd, pwd2=pwd2, lv=lv, cr=cr, ex=ex, expired=expired)
            session.add(emby)
            session.commit()
        except:
            pass


def sql_get_emby2(name, package_key: str = None):
    """
    查询一条emby记录，可以根据, embyid或者name来查询
    """
    def _get_with_session(session):
        try:
            emby = session.query(Emby2).filter(or_(Emby2.name == name, Emby2.embyid == name)).first()
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


def get_all_emby2(condition, package_key: str = None):
    """
    查询所有emby记录
    """
    def _get_all_with_session(session):
        try:
            return session.query(Emby2).filter(condition).all()
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


def sql_update_emby2(condition, package_key: str = None, **kwargs):
    """
    更新一条emby记录，根据condition来匹配，然后更新其他的字段
    """
    with Session(package_key) as session:
        try:
            # 用filter来过滤，注意要加括号
            emby = session.query(Emby2).filter(condition).first()
            if emby is None:
                return False
            # 然后用setattr方法来更新其他的字段，如果有就更新，如果没有就保持原样
            for k, v in kwargs.items():
                setattr(emby, k, v)
            session.commit()
            return True
        except:
            return False


def sql_delete_emby2(embyid, package_key: str = None):
    """
    根据tg删除一条emby记录
    """
    with Session(package_key) as session:
        try:
            emby = session.query(Emby2).filter_by(embyid=embyid).first()
            if emby:
                session.delete(emby)
                try:
                    session.commit()
                    return True
                except Exception as e:
                    # 记录错误信息
                    print(e)
                    # 回滚事务
                    session.rollback()
                    return False
            else:
                return None
        except Exception as e:
            # 记录错误信息
            print(e)
            return False
def sql_delete_emby2_by_name(name, package_key: str = None):
    """
    根据name删除一条emby记录
    """
    with Session(package_key) as session:
        try:
            emby = session.query(Emby2).filter_by(name=name).first()
            if emby:
                session.delete(emby)
                session.commit()
                return True
            else:
                return False
        except Exception as e:
            # 记录错误信息
            print(e)
            return False
