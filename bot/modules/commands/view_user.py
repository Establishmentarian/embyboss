from bot.func_helper.emby import emby
from pyrogram import filters
from bot import bot, bot_name, packages, default_package
from bot.func_helper.filters import staff_on_filter
from bot.func_helper.permissions import has_permission
from bot.func_helper.msg_utils import editMessage
from bot.func_helper.fix_bottons import whitelist_page_ikb, normaluser_page_ikb,devices_page_ikb 
from bot.sql_helper.sql_emby import get_all_emby, Emby
from bot.func_helper.msg_utils import callAnswer
import math
from pyromod.helpers import ikb


def _package_select_buttons(prefix: str):
    rows = [[(f"📦 {key}", f"{prefix}:{key}")] for key in packages.keys()]
    rows.append([("🔙 返回", "manage")])
    return ikb(rows)


def _resolve_package_key(package_key: str):
    if package_key in packages:
        return package_key
    return default_package

@bot.on_callback_query(filters.regex('^whitelist$') & staff_on_filter)
async def list_whitelist(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    if len(packages) > 1:
        await callAnswer(call, "📦 请选择套餐", True)
        return await editMessage(call, "📦 请选择要查看的套餐：", buttons=_package_select_buttons("whitelist_pkg"))
    await callAnswer(call, '🔍 白名单用户列表')
    page = 1
    whitelist_users = get_all_emby(Emby.lv == 'a', package_key=default_package)
    total_users = len(whitelist_users)
    total_pages = math.ceil(total_users / 20)

    text = await create_whitelist_text(whitelist_users, page, default_package)
    keyboard = await whitelist_page_ikb(total_pages, page, default_package)

    await editMessage(call, text, buttons=keyboard)


@bot.on_callback_query(filters.regex('^whitelist_pkg:') & staff_on_filter)
async def list_whitelist_by_package(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    package_key = _resolve_package_key(call.data.split(":", 1)[1])
    await callAnswer(call, f'🔍 白名单用户列表 - {package_key}')
    page = 1
    whitelist_users = get_all_emby(Emby.lv == 'a', package_key=package_key)
    total_users = len(whitelist_users)
    total_pages = math.ceil(total_users / 20)

    text = await create_whitelist_text(whitelist_users, page, package_key)
    keyboard = await whitelist_page_ikb(total_pages, page, package_key)
    await editMessage(call, text, buttons=keyboard)


@bot.on_callback_query(filters.regex('^normaluser$') & staff_on_filter)
async def list_normaluser(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    if len(packages) > 1:
        await callAnswer(call, "📦 请选择套餐", True)
        return await editMessage(call, "📦 请选择要查看的套餐：", buttons=_package_select_buttons("normaluser_pkg"))
    await callAnswer(call, '🔍 普通用户列表')
    page = 1
    normal_users = get_all_emby(Emby.lv == 'b', package_key=default_package)
    total_users = len(normal_users)
    total_pages = math.ceil(total_users / 20)

    text = await create_normaluser_text(normal_users, page, default_package)
    keyboard = await normaluser_page_ikb(total_pages, page, default_package)
    await editMessage(call, text, buttons=keyboard)


@bot.on_callback_query(filters.regex('^normaluser_pkg:') & staff_on_filter)
async def list_normaluser_by_package(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    package_key = _resolve_package_key(call.data.split(":", 1)[1])
    await callAnswer(call, f'🔍 普通用户列表 - {package_key}')
    page = 1
    normal_users = get_all_emby(Emby.lv == 'b', package_key=package_key)
    total_users = len(normal_users)
    total_pages = math.ceil(total_users / 20)

    text = await create_normaluser_text(normal_users, page, package_key)
    keyboard = await normaluser_page_ikb(total_pages, page, package_key)
    await editMessage(call, text, buttons=keyboard)


@bot.on_callback_query(filters.regex('^whitelist:') & staff_on_filter)
async def whitelist_page(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    _, page, package_key = call.data.split(':', 2)
    page = int(page)
    package_key = _resolve_package_key(package_key)
    await callAnswer(call, f'🔍 打开第{page}页')
    whitelist_users = get_all_emby(Emby.lv == 'a', package_key=package_key)
    total_users = len(whitelist_users)
    total_pages = math.ceil(total_users / 20)

    text = await create_whitelist_text(whitelist_users, page, package_key)
    keyboard = await whitelist_page_ikb(total_pages, page, package_key)

    await editMessage(call, text, buttons=keyboard)

@bot.on_callback_query(filters.regex('^normaluser:') & staff_on_filter)
async def normaluser_page(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    _, page, package_key = call.data.split(':', 2)
    page = int(page)
    package_key = _resolve_package_key(package_key)
    await callAnswer(call, f'🔍 打开第{page}页')
    normal_users = get_all_emby(Emby.lv == 'b', package_key=package_key)
    total_users = len(normal_users)
    total_pages = math.ceil(total_users / 20)

    text = await create_normaluser_text(normal_users, page, package_key)
    keyboard = await normaluser_page_ikb(total_pages, page, package_key)

    await editMessage(call, text, buttons=keyboard)

async def create_whitelist_text(users, page, package_key: str):
    start = (page - 1) * 20
    end = start + 20
    text = f"**白名单用户列表** (套餐: `{package_key}`)\n\n"
    for user in users[start:end]:
        text += f"TGID: `{user.tg}` | Emby用户名: [{user.name}](tg://user?id={user.tg})\n"
    text += f"第 {page} 页,共 {math.ceil(len(users) / 20)} 页, 共 {len(users)} 人"
    return text

async def create_normaluser_text(users, page, package_key: str):
    start = (page - 1) * 20
    end = start + 20
    text = f"**普通用户列表** (套餐: `{package_key}`)\n\n"
    for user in users[start:end]:
        text += f"TGID: `{user.tg}` | Emby用户名: [{user.name}](tg://user?id={user.tg})\n"
    text += f"第 {page} 页,共 {math.ceil(len(users) / 20)} 页, 共 {len(users)} 人"
    return text

@bot.on_callback_query(filters.regex('^user_devices$|^devices:') & staff_on_filter)
async def user_devices(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    # 获取页码
    if call.data == 'user_devices':
        if len(packages) > 1:
            await callAnswer(call, "📦 请选择套餐", True)
            return await editMessage(call, "📦 请选择要查看的套餐：", buttons=_package_select_buttons("devices_pkg"))
        page = 1
        package_key = default_package
        await callAnswer(call, '🔍 用户设备列表')
    else:
        _, page, package_key = call.data.split(':', 2)
        page = int(page)
        package_key = _resolve_package_key(package_key)
        await callAnswer(call, f'🔍 打开第{page}页')

    page_size = 20
    # 计算offset
    offset = (page - 1) * page_size
    
    # 获取用户设备信息
    success, result, has_prev, has_next = await emby.get_emby_user_devices(
        offset=offset,
        limit=page_size,
        package_key=package_key,
    )
    if not success:
        return await callAnswer(call, '🤕 Emby 服务器连接失败!')

    text = f'**💠 用户设备列表** (套餐: `{package_key}`)\n\n'
    for name, device_count, ip_count in result:
        text += f'用户名: [{name}](https://t.me/{bot_name}?start=userip-{name}) | 设备: {device_count} | IP: {ip_count}\n'
    text += f"\n第 {page} 页"
    await editMessage(call, text, buttons=devices_page_ikb(has_prev, has_next, page, package_key))


@bot.on_callback_query(filters.regex('^devices_pkg:') & staff_on_filter)
async def user_devices_by_package(_, call):
    if not has_permission(call.from_user.id, "view_users"):
        return await callAnswer(call, "❌ 权限不足", True)
    package_key = _resolve_package_key(call.data.split(":", 1)[1])
    page = 1
    await callAnswer(call, f'🔍 用户设备列表 - {package_key}')

    page_size = 20
    offset = (page - 1) * page_size
    success, result, has_prev, has_next = await emby.get_emby_user_devices(
        offset=offset,
        limit=page_size,
        package_key=package_key,
    )
    if not success:
        return await callAnswer(call, '🤕 Emby 服务器连接失败!')

    text = f'**💠 用户设备列表** (套餐: `{package_key}`)\n\n'
    for name, device_count, ip_count in result:
        text += f'用户名: [{name}](https://t.me/{bot_name}?start=userip-{name}) | 设备: {device_count} | IP: {ip_count}\n'
    text += f"\n第 {page} 页"
    await editMessage(call, text, buttons=devices_page_ikb(has_prev, has_next, page, package_key))
