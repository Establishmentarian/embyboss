from bot import admins, operators, owner, config


def get_user_role(user_id: int) -> str:
    if user_id == owner:
        return "owner"
    if user_id in admins:
        return "admin"
    if user_id in operators:
        return "operator"
    return "user"


def has_permission(user_id: int, perm: str) -> bool:
    if user_id == owner:
        return True
    role = get_user_role(user_id)
    allowed_roles = config.permissions.get(perm, [])
    return role in allowed_roles
