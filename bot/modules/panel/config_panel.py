"""
可调节设置
此处为控制面板2，主要是为了在bot中能够设置一些变量
部分目前有 导出日志，更改探针，更改emby线路，设置购买按钮

"""
import re

import bot as bot_module
from bot import bot, prefixes, bot_photo, Now, LOGGER, config, save_config, auto_update, moviepilot, sakura_b, reload_packages, packages
from pyrogram import filters

from bot.func_helper.filters import admins_on_filter
from bot.func_helper.fix_bottons import config_preparation, close_it_ikb, back_config_p_ikb, back_set_ikb, mp_config_ikb, back_config_p_ikb_with_package
from bot.func_helper.msg_utils import deleteMessage, editMessage, callAnswer, callListen, sendPhoto, sendFile
from bot.func_helper.scheduler import scheduler
from bot.scheduler.sync_mp_download import sync_download_tasks
from bot.func_helper.permissions import has_permission, get_user_role
from bot.func_helper.package_utils import (
    get_package_open_value,
    resolve_package_key,
    select_package,
    set_package_open_value,
)
from bot.func_helper.utils import get_users
from bot.schemas import EmbyPackage
import json
from pyromod.helpers import ikb


def _permission_text() -> str:
    lines = ["**🔐 当前权限配置**\n"]
    for perm, roles in (config.permissions or {}).items():
        roles_text = ", ".join(roles) if roles else "无"
        lines.append(f"- `{perm}`: {roles_text}")
    return "\n".join(lines)


def _format_roles() -> str:
    return "角色：`owner` / `admin` / `operator`"


def _perm_panel_buttons() -> "InlineKeyboardMarkup":
    labels = {
        "view_users": "查看用户数据",
        "manage_users": "管理用户",
        "open_registration": "开放注册",
        "manage_codes": "注册码/续期码",
        "config_basic": "基础配置",
        "config_advanced": "高级配置",
    }
    rows = []
    for key, label in labels.items():
        roles = (config.permissions or {}).get(key, [])
        enabled = "operator" in roles
        status = "✅" if enabled else "❎"
        rows.append([(f"{status} 允许次级管理员：{label}", f"perm_toggle:{key}")])
    rows.append([("👥 设置次级管理员", "set_operators"), ("👮🏻 设置管理员", "set_admins")])
    rows.append([("🔙 返回", "back_config")])
    return ikb(rows)


def _package_panel_buttons() -> "InlineKeyboardMarkup":
    rows = []
    packages = config.packages or {}
    if not packages:
        rows.append([("➕ 新建套餐", "package_add")])
    else:
        for key in packages.keys():
            rows.append([(f"📦 {key}", f"package_edit:{key}")])
        rows.append([("➕ 新建套餐", "package_add")])
    rows.append([("🔙 返回", "back_config")])
    return ikb(rows)


def _package_edit_buttons(package_key: str) -> "InlineKeyboardMarkup":
    rows = [
        [("API Key", f"package_set:{package_key}:emby_api"), ("Emby 地址", f"package_set:{package_key}:emby_url")],
        [("线路(普通)", f"package_set:{package_key}:emby_line"), ("线路(白名单)", f"package_set:{package_key}:emby_whitelist_line")],
        [("DB Host", f"package_set:{package_key}:db_host"), ("DB User", f"package_set:{package_key}:db_user")],
        [("DB Pwd", f"package_set:{package_key}:db_pwd"), ("DB Name", f"package_set:{package_key}:db_name")],
        [("DB Port", f"package_set:{package_key}:db_port"), ("设为默认", f"package_default:{package_key}")],
        [("删除套餐", f"package_delete:{package_key}")],
        [("🔙 返回", "package_panel")],
    ]
    return ikb(rows)


def _format_admin_lines() -> str:
    admins_text = ", ".join(map(str, config.admins or [])) or "无"
    operators_text = ", ".join(map(str, config.operators or [])) or "无"
    return f"管理员: {admins_text}\n次级管理员: {operators_text}"


def _paginate_members(members, page: int, per_page: int = 8):
    total = len(members)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return members[start:end], page, total_pages


def _member_select_buttons(candidates, action_prefix: str, page: int, back_callback: str):
    rows = []
    page_items, page, total_pages = _paginate_members(candidates, page)
    for tgid, name in page_items:
        label = f"➕ {name} ({tgid})"
        rows.append([(label, f"{action_prefix}:{tgid}")])
    nav_row = []
    if total_pages > 1:
        if page > 1:
            nav_row.append(("⬅️ 上一页", f"{action_prefix}_page:{page - 1}"))
        if page < total_pages:
            nav_row.append(("➡️ 下一页", f"{action_prefix}_page:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    rows.append([("🔙 返回", back_callback)])
    return ikb(rows)

async def _ensure_perm(call, perm: str):
    if not has_permission(call.from_user.id, perm):
        await callAnswer(call, "❌ 权限不足", True)
        return False
    return True


def _parse_reward_range(text: str):
    parts = [item for item in re.split(r"[\\s,，]+", text.strip()) if item]
    if len(parts) != 2:
        return None
    try:
        values = [int(item) for item in parts]
    except ValueError:
        return None
    low, high = min(values), max(values)
    return [low, high]


@bot.on_message(filters.command('config', prefixes=prefixes) & admins_on_filter)
async def config_p_set(_, msg):
    if not has_permission(msg.from_user.id, "config_basic"):
        return await sendPhoto(msg, photo=bot_photo, caption="❌ 权限不足，无法进入配置面板。")
    await deleteMessage(msg)
    package_key, buttons = select_package(prefix="panel:back_config", back_callback="back_start")
    if package_key is None:
        return await sendPhoto(msg, photo=bot_photo, caption="📦 请选择要配置的套餐：", buttons=buttons)
    await sendPhoto(msg, photo=bot_photo, caption="🌸 欢迎回来！\n\n👇点击你要修改的内容（推荐使用图形化配置）。",
                    buttons=config_preparation(package_key))


@bot.on_callback_query(filters.regex('^back_config$|^panel:back_config:') & admins_on_filter)
async def config_p_re(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, "✅ config")
    if call.data.startswith("panel:back_config:"):
        package_key = resolve_package_key(call.data.split(":")[-1])
    else:
        package_key, buttons = select_package(prefix="panel:back_config", back_callback="manage")
        if package_key is None:
            await callAnswer(call, "📦 请选择套餐", True)
            return await editMessage(call, "📦 请选择要配置的套餐：", buttons=buttons)
    await editMessage(call, "🌸 欢迎回来！\n\n👇点击你要修改的内容（推荐使用图形化配置）。", buttons=config_preparation(package_key))


@bot.on_callback_query(filters.regex("log_out") & admins_on_filter)
async def log_out(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, '🌐查询中...')
    # file位置以main.py为准
    send = await sendFile(call, file=f"log/log_{Now:%Y%m%d}.txt", file_name=f'log_{Now:%Y-%m-%d}.txt',
                          caption="📂 **导出日志成功！**", buttons=close_it_ikb)
    if send is not True:
        return LOGGER.info(f"【admin】：{call.from_user.id} - 导出日志失败！")

    LOGGER.info(f"【admin】：{call.from_user.id} - 导出日志成功！")


@bot.on_callback_query(filters.regex("set_tz") & admins_on_filter)
async def set_tz(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, '📌 设置探针')
    send = await editMessage(call,
                             "【设置探针】\n\n请依次输入探针地址，api_token，设置的检测多个id 如：\n**【地址】https://tz.susuyyds.xyz\n【api_token】xxxxxx\n【数字】1 2 3**\n取消点击 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, back_set_ikb('set_tz'))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_tz'))
    else:
        await txt.delete()
        try:
            c = txt.text.split("\n")
            s_tz = c[0]
            s_tzapi = c[1]
            s_tzid = c[2].split()
        except IndexError:
            await editMessage(call, f"请注意格式！您的输入如下：\n\n`{txt.text}`", buttons=back_set_ikb('set_tz'))
        else:
            config.tz_ad = s_tz
            config.tz_api = s_tzapi
            config.tz_id = s_tzid
            save_config()
            await editMessage(call,
                              f"【网址】\n{s_tz}\n\n【api_token】\n{s_tzapi}\n\n【检测的ids】\n{config.tz_id} **Done！**",
                              buttons=back_config_p_ikb)
            LOGGER.info(f"【admin】：{call.from_user.id} - 更新探针设置完成")


# 设置 emby 线路
@bot.on_callback_query(filters.regex('^set_line') & admins_on_filter)
async def set_emby_line(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, '📌 设置emby线路')
    package_key = resolve_package_key(call.data.split(":")[-1]) if ":" in call.data else resolve_package_key(None)
    send = await editMessage(call,
                             "💘【设置线路】\n\n对我发送向emby用户展示的emby地址吧\n取消点击 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_set_ikb('set_line', package_key))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_line', package_key))
    else:
        await txt.delete()
        package = packages[package_key]
        package.emby_line = txt.text
        config.packages = config.packages or {}
        config.packages[package_key] = package
        save_config()
        reload_packages()
        await editMessage(call, f"**【网址样式】:** \n\n{package.emby_line}\n\n设置完成！done！",
                          buttons=back_config_p_ikb_with_package(package_key) if package_key else back_config_p_ikb)
        LOGGER.info(f"【admin】：{call.from_user.id} - 更新emby线路为{package.emby_line}设置完成")

@bot.on_callback_query(filters.regex('^set_whitelist_line') & admins_on_filter)
async def set_whitelist_emby_line(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, '🌟 设置白名单线路')
    package_key = resolve_package_key(call.data.split(":")[-1]) if ":" in call.data else resolve_package_key(None)
    send = await editMessage(call,
                             "🌟【设置白名单线路】\n\n对我发送白名单用户专属的emby地址\n取消点击 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_set_ikb('set_whitelist_line', package_key))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_whitelist_line', package_key))
    else:
        await txt.delete()
        package = packages[package_key]
        package.emby_whitelist_line = txt.text
        config.packages = config.packages or {}
        config.packages[package_key] = package
        save_config()
        reload_packages()
        await editMessage(call, f"**【白名单线路】:** \n\n{package.emby_whitelist_line}\n\n设置完成！done！",
                          buttons=back_config_p_ikb_with_package(package_key) if package_key else back_config_p_ikb)
        LOGGER.info(f"【admin】：{call.from_user.id} - 更新白名单线路为{package.emby_whitelist_line}设置完成")

# 设置需要显示/隐藏的库
@bot.on_callback_query(filters.regex('set_block') & admins_on_filter)
async def set_block(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, '📺 设置显隐媒体库')
    send = await editMessage(call,
                             "🎬**【设置需要显示/隐藏的库】**\n\n对我发送库的名字，多个**中文逗号**隔开\n例: `SGNB 特效电影，纪录片`\n超时自动退出 or 点 /cancel 退出")
    if send is False:
        return

    txt = await callListen(call, 120)
    if txt is False:
        return await config_p_re(_, call)

    elif txt.text == '/cancel':
        # config.emby_block = []
        # save_config()
        await txt.delete()
        return await config_p_re(_, call)
        # await editMessage(call, '__已清空并退出，__ **会话已结束！**', buttons=back_set_ikb('set_block'))
        # LOGGER.info(f"【admin】：{call.from_user.id} - 清空 指定显示/隐藏内容库 设置完成")
    else:
        c = txt.text.split("，")
        config.emby_block = c
        save_config()
        await txt.delete()
        await editMessage(call, f"🎬 指定显示/隐藏内容如下: \n\n{'.'.join(config.emby_block or [])}\n设置完成！done！",
                          buttons=back_config_p_ikb)
        LOGGER.info(f"【admin】：{call.from_user.id} - 更新指定显示/隐藏内容库为 {config.emby_block} 设置完成")


# @bot.on_callback_query(filters.regex("set_buy") & admins_on_filter)
# async def set_buy(_, call):
#     if user_buy.stat:
#         user_buy.stat = False
#         save_config()
#         await callAnswer(call, '**👮🏻‍♂️ 已经为您关闭购买按钮啦！**')
#         LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} - 关闭了购买按钮")
#         return await config_p_re(_, call)
#
#     user_buy.stat = True
#     await editMessage(call, '**👮🏻‍♂️ 已经为您开启购买按钮啦！目前默认只使用一个按钮，如果需求请github联系**\n'
#                             '- 更换按钮请输入格式形如： \n\n`[按钮文字描述] - http://xxx`\n'
#                             '- 退出状态请按 /cancel，需要markdown效果的话请在配置文件更改')
#     save_config()
#     LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} - 开启了购买按钮")
#
#     txt = await callListen(call, 120, buttons=back_set_ikb('set_buy'))
#     if txt is False:
#         return
#
#     elif txt.text == '/cancel':
#         await txt.delete()
#         await editMessage(call, '__您已经取消输入__ 退出状态。', buttons=back_config_p_ikb)
#     else:
#         await txt.delete()
#         try:
#             buy_text, buy_button = txt.text.replace(' ', '').split('-')
#         except (IndexError, TypeError):
#             await editMessage(call, f"**格式有误，您的输入：**\n\n{txt.text}", buttons=back_set_ikb('set_buy'))
#         else:
#             d = [buy_text, buy_button, 'url']
#             keyboard = try_set_buy(d)
#             edt = await editMessage(call, "**🫡 按钮效果如下：**\n可点击尝试，确认后返回",
#                                     buttons=keyboard)
#             if edt is False:
#                 LOGGER.info(f'【admin】：{txt.from_user.id} - 更新了购买按钮设置 失败')
#                 return await editMessage(call, "可能输入的link格式错误，请重试。http/https+link",
#                                          buttons=back_config_p_ikb)
#             user_buy.button = d
#             save_config()
#             LOGGER.info(f'【admin】：{txt.from_user.id} - 更新了购买按钮设置 {user_buy.button}')


@bot.on_callback_query(filters.regex('set_update') & admins_on_filter)
async def set_auto_update(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    try:
        # 简化逻辑，只设置一次
        auto_update.status = not auto_update.status
        if auto_update.status:
            message = '👮🏻‍♂️您已开启 auto_update自动更新bot代码\n\n运行时间：12:30UTC+0800'
            LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已启用 auto_update自动更新bot代码")
        else:
            message = '👮🏻‍♂️ 您已关闭 auto_update自动更新bot代码，如您需要更换仓库，请于配置文件中git_repo填写'
            LOGGER.info(f"【admin】：管理员 {call.from_user.first_name} 已关闭 auto_update自动更新bot代码")

        await callAnswer(call, message, True)
        await config_p_re(_, call)
        save_config()
    except Exception as e:
        # 异常处理，记录错误信息
        LOGGER.error(f"【admin】：管理员 {call.from_user.first_name} 尝试更改 auto_update状态时出错: {e}")


@bot.on_callback_query(filters.regex('^set_mp$') & admins_on_filter)
async def mp_config_panel(_, call):
    """MoviePilot 设置面板"""
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, '⚙️ MoviePilot 设置')
    lv_text = '无'
    if moviepilot.lv == 'a':
        lv_text = '白名单'
    elif moviepilot.lv == 'b':
        lv_text = '普通用户'
    await editMessage(call, 
                     "⚙️ MoviePilot 设置面板\n\n"
                     f"当前状态：{'已开启' if moviepilot.status else '已关闭'}\n"
                     f"点播价格：{moviepilot.price} {sakura_b}/GB\n"
                     f"用户权限：{lv_text}可使用\n"
                     f"日志频道：{moviepilot.download_log_chatid or '未设置'}",
                     buttons=mp_config_ikb())

@bot.on_callback_query(filters.regex('^set_mp_status$') & admins_on_filter)
async def set_mp_status(_, call):
    """设置点播功能开关"""
    if not await _ensure_perm(call, "config_basic"):
        return
    try:
        moviepilot.status = not moviepilot.status
        if moviepilot.status:
            message = '👮🏻‍♂️ 您已开启 MoviePilot 点播功能'
            scheduler.add_job(sync_download_tasks, 'interval', seconds=60, id='sync_download_tasks')
        else:
            message = '👮🏻‍♂️ 您已关闭 MoviePilot 点播功能'
            scheduler.remove_job(job_id='sync_download_tasks')
        
        await callAnswer(call, message, True)
        save_config()
        await mp_config_panel(_, call)
    except Exception as e:
        LOGGER.error(f"设置点播状态时出错: {str(e)}")

@bot.on_callback_query(filters.regex('^set_mp_price$') & admins_on_filter)
async def set_mp_price(_, call):
    """设置点播价格"""
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, '💰 设置点播价格')
    await editMessage(call,
                     f"💰 设置点播价格\n\n"
                     f"当前价格：{moviepilot.price} {sakura_b}/GB\n"
                     f"请输入新的价格数值\n"
                     f"取消请点 /cancel")
    
    txt = await callListen(call, 120)
    if txt is False or txt.text == '/cancel':
        return await mp_config_panel(_, call)
    
    try:
        price = int(txt.text)
        if price < 0:
            raise ValueError
        moviepilot.price = price
        save_config()
        await editMessage(call, f"✅ 点播价格已设置为 {price} {sakura_b}/GB")
        await mp_config_panel(_, call)
    except ValueError:
        await editMessage(call, "❌ 请输入有效的数字")
        await mp_config_panel(_, call)

@bot.on_callback_query(filters.regex('set_mp_lv') & admins_on_filter)
async def set_mp_lv(_, call):
    """设置用户权限"""
    if not await _ensure_perm(call, "config_basic"):
        return
    moviepilot.lv = 'a' if moviepilot.lv == 'b' else 'b'
    message = '✅ 已设置为仅白名单用户可用' if moviepilot.lv == 'a' else '✅ 已设置为普通用户可用'
    await callAnswer(call, message, True)
    save_config()
    await mp_config_panel(_, call)

@bot.on_callback_query(filters.regex('set_mp_log_channel') & admins_on_filter)
async def set_mp_log_channel(_, call):
    """设置日志频道"""
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, '📝 设置日志频道')
    await editMessage(call,
                     f"📝 设置日志频道\n\n"
                     f"当前频道：{moviepilot.download_log_chatid or '未设置'}\n"
                     f"请输入频道 ID\n"
                     f"取消请点 /cancel")
    
    txt = await callListen(call, 120)
    if txt is False or txt.text == '/cancel':
        return await mp_config_panel(_, call)
    
    try:
        chat_id = int(txt.text)
        moviepilot.download_log_chatid = chat_id
        save_config()
        await editMessage(call, f"✅ 日志频道已设置为 {chat_id}")
        await mp_config_panel(_, call)
    except ValueError:
        await editMessage(call, "❌ 请输入有效的频道 ID")
        await mp_config_panel(_, call)


@bot.on_callback_query(filters.regex('leave_ban') & admins_on_filter)
async def open_leave_ban(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    # 切换状态
    package_key = resolve_package_key(call.data.split(":")[-1]) if ":" in call.data else resolve_package_key(None)
    current = get_package_open_value(package_key, "leave_ban")
    set_package_open_value(package_key, "leave_ban", not current)
    # 根据当前状态发送消息
    if get_package_open_value(package_key, "leave_ban"):
        message = '**👮🏻‍♂️ 您已开启 退群封禁，用户退群bot将会被封印，禁止入群**'
        log_message = "【admin】：管理员 {} 已调整 退群封禁设置为 True".format(call.from_user.first_name)
    else:
        message = '**👮🏻‍♂️ 您已关闭 退群封禁，用户退群bot将不会被封印了**'
        log_message = "【admin】：管理员 {} 已调整 退群封禁设置为 False".format(call.from_user.first_name)

    await callAnswer(call, message, True)
    await editMessage(call, "🌸 欢迎回来！\n\n👇点击你要修改的内容（推荐使用图形化配置）。", buttons=config_preparation(package_key))
    save_config()
    LOGGER.info(log_message)


@bot.on_callback_query(filters.regex('set_uplays') & admins_on_filter)
async def set_user_playrank(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    package_key = resolve_package_key(call.data.split(":")[-1]) if ":" in call.data else resolve_package_key(None)
    current = get_package_open_value(package_key, "uplays")
    set_package_open_value(package_key, "uplays", not current)
    if not get_package_open_value(package_key, "uplays"):
        message = '👮🏻‍♂️ 您已关闭 观影榜结算，自动召唤观影榜将不被计算积分'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已关闭 观影榜结算"
    else:
        message = '👮🏻‍♂️ 您已开启 观影榜结算，自动召唤观影榜将会被计算积分'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已启用 观影榜结算"

    await callAnswer(call, message, True)
    await editMessage(call, "🌸 欢迎回来！\n\n👇点击你要修改的内容（推荐使用图形化配置）。", buttons=config_preparation(package_key))
    save_config()
    LOGGER.info(log_message)


@bot.on_callback_query(filters.regex('^panel:toggle_open:') & admins_on_filter)
async def toggle_open_setting(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    parts = call.data.split(":")
    field = parts[2] if len(parts) > 2 else None
    package_key = resolve_package_key(parts[3]) if len(parts) > 3 else resolve_package_key(None)
    if field not in {"checkin", "exchange", "whitelist", "invite"}:
        await callAnswer(call, "❌ 未知配置项", True)
        return
    current = bool(get_package_open_value(package_key, field))
    set_package_open_value(package_key, field, not current)
    save_config()
    await config_p_re(_, call)


@bot.on_callback_query(filters.regex('^set_money_name$') & admins_on_filter)
async def set_money_name(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, '💰 设置积分名称')
    send = await editMessage(call,
                             f"💰【设置积分名称】\n\n请输入新的积分名称\n取消点击 /cancel\n\n当前积分名称: {config.money}")
    if send is False:
        return
    txt = await callListen(call, 120, back_set_ikb('set_money_name'))
    if txt is False:
        return
    if txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_money_name'))
        return
    await txt.delete()
    name = txt.text.strip()
    if not name:
        await editMessage(call, "❌ 积分名称不能为空。", buttons=back_set_ikb('set_money_name'))
        return
    config.money = name
    bot_module.sakura_b = name
    save_config()
    await editMessage(call, f"✅ 积分名称已更新为 {config.money}", buttons=back_config_p_ikb)


@bot.on_callback_query(filters.regex('^panel:set_open_value:') & admins_on_filter)
async def set_open_value(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    parts = call.data.split(":")
    field = parts[2] if len(parts) > 2 else None
    package_key = resolve_package_key(parts[3]) if len(parts) > 3 else resolve_package_key(None)
    labels = {
        "exchange_cost": "自动续期兑换消耗",
        "whitelist_cost": "兑换白名单消耗",
        "invite_cost": "兑换邀请码消耗",
    }
    if field not in labels:
        await callAnswer(call, "❌ 未知配置项", True)
        return
    current = get_package_open_value(package_key, field) or 0
    await callAnswer(call, f"🧮 设置{labels[field]}")
    prompt = (
        f"🧮【设置{labels[field]}】\n\n"
        f"请输入一个数字\n取消点击 /cancel\n\n"
        f"当前数值: {current} {config.money}"
    )
    send = await editMessage(call, prompt)
    if send is False:
        return
    txt = await callListen(call, 120, back_set_ikb(f'panel:set_open_value:{field}', package_key))
    if txt is False:
        return
    if txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**',
                          buttons=back_set_ikb(f'panel:set_open_value:{field}', package_key))
        return
    await txt.delete()
    try:
        value = int(txt.text)
    except ValueError:
        await editMessage(call, f"请注意格式! 您的输入如下: \n\n`{txt.text}`",
                          buttons=back_set_ikb(f'panel:set_open_value:{field}', package_key))
        return
    set_package_open_value(package_key, field, value)
    save_config()
    await editMessage(call, f"✅ {labels[field]} 已更新为 {value} {config.money}",
                      buttons=back_config_p_ikb_with_package(package_key))


@bot.on_callback_query(filters.regex('^panel:set_checkin_reward') & admins_on_filter)
async def set_checkin_reward(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    package_key = resolve_package_key(call.data.split(":")[-1]) if ":" in call.data else resolve_package_key(None)
    current = get_package_open_value(package_key, "checkin_reward") or [1, 10]
    await callAnswer(call, "🎯 设置签到奖励")
    send = await editMessage(call,
                             "🎯【设置签到奖励】\n\n"
                             "请输入奖励区间（例如：1 10）\n"
                             "取消点击 /cancel\n\n"
                             f"当前奖励区间: {current[0]}~{current[1]} {config.money}")
    if send is False:
        return
    txt = await callListen(call, 120, back_set_ikb('panel:set_checkin_reward', package_key))
    if txt is False:
        return
    if txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**',
                          buttons=back_set_ikb('panel:set_checkin_reward', package_key))
        return
    await txt.delete()
    reward_range = _parse_reward_range(txt.text)
    if not reward_range:
        await editMessage(call, f"请注意格式! 您的输入如下: \n\n`{txt.text}`",
                          buttons=back_set_ikb('panel:set_checkin_reward', package_key))
        return
    set_package_open_value(package_key, "checkin_reward", reward_range)
    save_config()
    await editMessage(call, f"✅ 签到奖励区间已更新为 {reward_range[0]}~{reward_range[1]} {config.money}",
                      buttons=back_config_p_ikb_with_package(package_key))


@bot.on_callback_query(filters.regex('set_kk_gift_days') & admins_on_filter)
async def set_kk_gift_days(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, '📌 设置赠送资格天数')
    send = await editMessage(call,
                             f"🤝【设置kk赠送资格】\n\n请输入一个数字\n取消点击 /cancel\n\n当前赠送资格天数: {config.kk_gift_days}")
    if send is False:
        return
    txt = await callListen(call, 120, back_set_ikb('set_kk_gift_days'))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_kk_gift_days'))
    else:
        await txt.delete()
        try:
            days = int(txt.text)
        except ValueError:
            await editMessage(call, f"请注意格式! 您的输入如下: \n\n`{txt.text}`",
                              buttons=back_set_ikb('set_kk_gift_days'))
        else:
            config.kk_gift_days = days
            save_config()
            await editMessage(call,
                              f"🤝 【赠送资格天数】\n\n{days}天 **Done!**",
                              buttons=back_config_p_ikb)
            LOGGER.info(f"【admin】：{call.from_user.id} - 更新赠送资格天数完成")


@bot.on_callback_query(filters.regex('set_fuxx_pitao') & admins_on_filter)
async def set_fuxx_pitao(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    config.fuxx_pitao = not config.fuxx_pitao
    if not config.fuxx_pitao:
        message = '👮🏻‍♂️ 您已关闭 皮套过滤功能，现在皮套人的消息不会被处理'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已调整 皮套过滤功能 False"
    else:
        message = '👮🏻‍♂️ 您已开启 皮套过滤功能，现在皮套人的消息将会被狙杀'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已调整 皮套过滤功能 True"

    await callAnswer(call, message, True)
    await config_p_re(_, call)
    save_config()
    LOGGER.info(log_message)
@bot.on_callback_query(filters.regex('set_red_envelope_status') & admins_on_filter)
async def set_red_envelope_status(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    config.red_envelope.status = not config.red_envelope.status
    if config.red_envelope.status:
        message = '👮🏻‍♂️ 您已开启 红包功能，现在用户可以发送红包了'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已调整 红包功能 True"
    else:
        message = '👮🏻‍♂️ 您已关闭 红包功能，现在用户不能发送红包了'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已调整 红包功能 False"
    await callAnswer(call, message, True)
    await config_p_re(_, call)
    save_config()
    LOGGER.info(log_message)

@bot.on_callback_query(filters.regex('set_red_envelope_allow_private') & admins_on_filter)
async def set_red_envelope_allow_private(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    config.red_envelope.allow_private = not config.red_envelope.allow_private
    if config.red_envelope.allow_private:
        message = '👮🏻‍♂️ 您已开启 专属红包，现在用户可以发送专属红包了'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已调整 专属红包功能 True"
    else:
        message = '👮🏻‍♂️ 您已关闭 专属红包，现在用户不能发送专属红包了'
        log_message = f"【admin】：管理员 {call.from_user.first_name} 已调整 专属红包功能 False"
    await callAnswer(call, message, True)
    await config_p_re(_, call)
    save_config()
    LOGGER.info(log_message)

@bot.on_callback_query(filters.regex('set_activity_check_days') & admins_on_filter)
async def set_activity_check_days(_, call):
    if not await _ensure_perm(call, "config_basic"):
        return
    await callAnswer(call, '📌 设置活跃检测天数')
    send = await editMessage(call,
                             f"🕰️【设置活跃检测天数】\n\n请输入一个数字（天数）\n取消点击 /cancel\n\n当前活跃检测天数: {config.activity_check_days}")
    if send is False:
        return
    txt = await callListen(call, 120, back_set_ikb('set_activity_check_days'))
    if txt is False:
        return

    elif txt.text == '/cancel':
        await txt.delete()
        await editMessage(call, '__您已经取消输入__ **会话已结束！**', buttons=back_set_ikb('set_activity_check_days'))
    else:
        await txt.delete()
        try:
            days = int(txt.text)
            if days <= 0:
                raise ValueError("天数必须大于0")
        except ValueError:
            await editMessage(call, f"请注意格式! 请输入大于0的数字。您的输入如下: \n\n`{txt.text}`",
                              buttons=back_set_ikb('set_activity_check_days'))
        else:
            config.activity_check_days = days
            save_config()
            await editMessage(call,
                              f"🕰️ 【活跃检测天数】\n\n{days}天 **Done!**",
                              buttons=back_config_p_ikb)
            LOGGER.info(f"【admin】：{call.from_user.id} - 更新活跃检测天数为{days}天完成")


@bot.on_callback_query(filters.regex("perm_panel") & admins_on_filter)
async def perm_panel(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    role = get_user_role(call.from_user.id)
    text = f"**🧭 权限管理**\n\n- 当前角色：`{role}`\n- 次级管理员列表：{', '.join(map(str, config.operators)) or '无'}\n\n"
    text += _permission_text() + f"\n\n{_format_roles()}"
    await editMessage(call, text, buttons=_perm_panel_buttons())


@bot.on_callback_query(filters.regex("set_operators") & admins_on_filter)
async def set_operators(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, "🔧 设置次级管理员")
    send = await editMessage(call, "请输入次级管理员 TGID，空格分隔。清空请输入 `none`，取消 /cancel")
    if send is False:
        return
    txt = await callListen(call, 120, buttons=back_set_ikb("set_operators"))
    if txt is False:
        return
    if txt.text == "/cancel":
        await txt.delete()
        return await editMessage(call, "已取消。", buttons=back_config_p_ikb)
    content = txt.text.strip()
    await txt.delete()
    if content.lower() == "none":
        config.operators = []
    else:
        ids = [int(x) for x in content.split()]
        config.operators = ids
    save_config()
    await editMessage(call, f"✅ 已更新次级管理员：{', '.join(map(str, config.operators)) or '无'}", buttons=back_config_p_ikb)


@bot.on_callback_query(filters.regex("set_admins") & admins_on_filter)
async def set_admins(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, "👮🏻 设置管理员")
    send = await editMessage(call, "请输入管理员 TGID，空格分隔。清空请输入 `none`，取消 /cancel")
    if send is False:
        return
    txt = await callListen(call, 120, buttons=back_set_ikb("set_admins"))
    if txt is False:
        return
    if txt.text == "/cancel":
        await txt.delete()
        return await editMessage(call, "已取消。", buttons=back_config_p_ikb)
    content = txt.text.strip()
    await txt.delete()
    if content.lower() == "none":
        config.admins = []
    else:
        ids = [int(x) for x in content.split()]
        config.admins = ids
    save_config()
    await editMessage(call, f"✅ 已更新管理员：{', '.join(map(str, config.admins)) or '无'}", buttons=back_config_p_ikb)


@bot.on_callback_query(filters.regex("set_permissions") & admins_on_filter)
async def set_permissions(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, "🔧 设置权限")
    available_perms = ", ".join((config.permissions or {}).keys())
    help_text = (
        "请按行输入权限配置，格式：`权限名=角色1,角色2`\n"
        "例如：`manage_codes=owner,admin,operator`\n"
        "支持权限：`{}`\n"
        "{}"
    ).format(available_perms, _format_roles())
    send = await editMessage(call, help_text)
    if send is False:
        return
    txt = await callListen(call, 180, buttons=back_set_ikb("set_permissions"))
    if txt is False:
        return
    if txt.text == "/cancel":
        await txt.delete()
        return await editMessage(call, "已取消。", buttons=back_config_p_ikb)
    await txt.delete()
    new_permissions = {}
    for line in txt.text.splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            return await editMessage(call, f"格式错误：`{line}`", buttons=back_set_ikb("set_permissions"))
        key, roles = line.split("=", 1)
        new_permissions[key.strip()] = [r.strip() for r in roles.split(",") if r.strip()]
    config.permissions = new_permissions
    save_config()
    await editMessage(call, "✅ 权限已更新。", buttons=back_config_p_ikb)


@bot.on_callback_query(filters.regex(r"^perm_toggle:") & admins_on_filter)
async def perm_toggle(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    _, perm_key = call.data.split(":", 1)
    current = (config.permissions or {}).get(perm_key, [])
    if "operator" in current:
        current = [r for r in current if r != "operator"]
    else:
        current.append("operator")
    config.permissions[perm_key] = current
    save_config()
    await perm_panel(_, call)


@bot.on_callback_query(filters.regex("set_config_any") & admins_on_filter)
async def set_config_any(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, "🧩 配置编辑器")
    help_text = (
        "请输入：`路径=值`，支持 JSON 值。\n"
        "示例：`open.all_user=500`\n"
        "示例：`emby_block=[\"A\",\"B\"]`\n"
        "取消 /cancel"
    )
    send = await editMessage(call, help_text)
    if send is False:
        return
    txt = await callListen(call, 180, buttons=back_set_ikb("set_config_any"))
    if txt is False:
        return
    if txt.text == "/cancel":
        await txt.delete()
        return await editMessage(call, "已取消。", buttons=back_config_p_ikb)
    await txt.delete()
    if "=" not in txt.text:
        return await editMessage(call, "格式错误，请使用 `路径=值`。", buttons=back_set_ikb("set_config_any"))
    path, raw_value = txt.text.split("=", 1)
    path = path.strip()
    raw_value = raw_value.strip()
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value
    try:
        target = config
        parts = path.split(".")
        for part in parts[:-1]:
            if isinstance(target, dict):
                target = target.setdefault(part, {})
            else:
                target = getattr(target, part)
        if isinstance(target, dict):
            target[parts[-1]] = value
        else:
            setattr(target, parts[-1], value)
        save_config()
    except Exception as exc:
        return await editMessage(call, f"❌ 更新失败：{exc}", buttons=back_set_ikb("set_config_any"))
    await editMessage(call, f"✅ 已更新 `{path}`。", buttons=back_config_p_ikb)


@bot.on_callback_query(filters.regex("admin_list") & admins_on_filter)
async def admin_list(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    text = "**👥 管理员列表管理**\n\n"
    text += _format_admin_lines()
    text += "\n\n请选择操作："
    rows = [
        [("➕ 新增管理员", "admin_add_page:1"), ("➕ 新增次级管理员", "operator_add_page:1")],
    ]
    for admin_id in config.admins or []:
        rows.append([(f"➖ 移除管理员 {admin_id}", f"admin_remove:{admin_id}")])
    for operator_id in config.operators or []:
        rows.append([(f"➖ 移除次级管理员 {operator_id}", f"operator_remove:{operator_id}")])
    rows.append([("🛠️ 高级模式：设置管理员", "set_admins"), ("🛠️ 高级模式：设置次级管理员", "set_operators")])
    rows.append([("🔙 返回", "back_config")])
    await editMessage(call, text, buttons=ikb(rows))


@bot.on_callback_query(filters.regex(r"^admin_add_page:") & admins_on_filter)
async def admin_add_page(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    page = int(call.data.split(":")[1])
    members = await get_users()
    candidates = [
        (tgid, name)
        for tgid, name in members.items()
        if tgid not in (config.admins or []) and tgid != config.owner
    ]
    candidates.sort(key=lambda item: (item[1] or "", item[0]))
    if not candidates:
        return await editMessage(call, "暂无可添加的管理员用户。", buttons=ikb([[("🔙 返回", "admin_list")]]))
    text = "**➕ 选择要添加的管理员**\n\n" + _format_admin_lines()
    buttons = _member_select_buttons(candidates, "admin_add", page, "admin_list")
    await editMessage(call, text, buttons=buttons)


@bot.on_callback_query(filters.regex(r"^operator_add_page:") & admins_on_filter)
async def operator_add_page(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    page = int(call.data.split(":")[1])
    members = await get_users()
    candidates = [
        (tgid, name)
        for tgid, name in members.items()
        if tgid not in (config.operators or []) and tgid != config.owner
    ]
    candidates.sort(key=lambda item: (item[1] or "", item[0]))
    if not candidates:
        return await editMessage(call, "暂无可添加的次级管理员用户。", buttons=ikb([[("🔙 返回", "admin_list")]]))
    text = "**➕ 选择要添加的次级管理员**\n\n" + _format_admin_lines()
    buttons = _member_select_buttons(candidates, "operator_add", page, "admin_list")
    await editMessage(call, text, buttons=buttons)


@bot.on_callback_query(filters.regex(r"^admin_add:") & admins_on_filter)
async def admin_add(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    tgid = int(call.data.split(":")[1])
    if tgid == config.owner:
        return await callAnswer(call, "❌ 不能添加所有者。", True)
    if config.admins is None:
        config.admins = []
    if tgid not in config.admins:
        config.admins.append(tgid)
        save_config()
    await admin_list(_, call)


@bot.on_callback_query(filters.regex(r"^admin_remove:") & admins_on_filter)
async def admin_remove(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    tgid = int(call.data.split(":")[1])
    if tgid == config.owner:
        return await callAnswer(call, "❌ 不能移除所有者。", True)
    if config.admins is None:
        config.admins = []
    if tgid in config.admins:
        config.admins.remove(tgid)
        save_config()
    await admin_list(_, call)


@bot.on_callback_query(filters.regex(r"^operator_add:") & admins_on_filter)
async def operator_add(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    tgid = int(call.data.split(":")[1])
    if tgid == config.owner:
        return await callAnswer(call, "❌ 不能添加所有者。", True)
    if config.operators is None:
        config.operators = []
    if tgid not in config.operators:
        config.operators.append(tgid)
        save_config()
    await admin_list(_, call)


@bot.on_callback_query(filters.regex(r"^operator_remove:") & admins_on_filter)
async def operator_remove(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    tgid = int(call.data.split(":")[1])
    if tgid == config.owner:
        return await callAnswer(call, "❌ 不能移除所有者。", True)
    if config.operators is None:
        config.operators = []
    if tgid in config.operators:
        config.operators.remove(tgid)
        save_config()
    await admin_list(_, call)


@bot.on_callback_query(filters.regex("package_panel") & admins_on_filter)
async def package_panel(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await editMessage(call, "📦 请选择要配置的套餐：", buttons=_package_panel_buttons())


@bot.on_callback_query(filters.regex("package_add") & admins_on_filter)
async def package_add(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    await callAnswer(call, "➕ 新建套餐")
    send = await editMessage(call, "请输入套餐名称（英文/数字，下划线），取消 /cancel")
    if send is False:
        return
    txt = await callListen(call, 120, buttons=back_set_ikb("package_add"))
    if txt is False:
        return
    if txt.text == "/cancel":
        await txt.delete()
        return await package_panel(_, call)
    name = txt.text.strip()
    await txt.delete()
    if not name:
        return await editMessage(call, "名称不能为空。", buttons=back_set_ikb("package_add"))
    config.packages = config.packages or {}
    if name in config.packages:
        return await editMessage(call, f"套餐 `{name}` 已存在。", buttons=back_set_ikb("package_add"))
    config.packages[name] = EmbyPackage(
        emby_api="",
        emby_url="",
        emby_line="",
        emby_whitelist_line=None,
        db_host=config.db_host,
        db_user=config.db_user,
        db_pwd=config.db_pwd,
        db_name=config.db_name,
        db_port=config.db_port,
    )
    save_config()
    reload_packages()
    await editMessage(call, f"✅ 已创建套餐 `{name}`。", buttons=_package_edit_buttons(name))


@bot.on_callback_query(filters.regex(r"^package_edit:") & admins_on_filter)
async def package_edit(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    package_key = call.data.split(":", 1)[1]
    package = (config.packages or {}).get(package_key)
    if not package:
        return await editMessage(call, "❌ 未找到套餐。", buttons=_package_panel_buttons())
    text = (
        f"**📦 套餐 {package_key}**\n\n"
        f"- emby_url: `{package.emby_url}`\n"
        f"- emby_api: `{package.emby_api}`\n"
        f"- emby_line: `{package.emby_line}`\n"
        f"- emby_whitelist_line: `{package.emby_whitelist_line}`\n"
        f"- db_host: `{package.db_host}`\n"
        f"- db_user: `{package.db_user}`\n"
        f"- db_pwd: `{package.db_pwd}`\n"
        f"- db_name: `{package.db_name}`\n"
        f"- db_port: `{package.db_port}`\n"
    )
    await editMessage(call, text, buttons=_package_edit_buttons(package_key))


@bot.on_callback_query(filters.regex(r"^package_set:") & admins_on_filter)
async def package_set(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    _, package_key, field = call.data.split(":", 2)
    package = (config.packages or {}).get(package_key)
    if not package:
        return await editMessage(call, "❌ 未找到套餐。", buttons=_package_panel_buttons())
    await callAnswer(call, "🛠️ 修改字段")
    send = await editMessage(call, f"请输入 `{field}` 的新值，取消 /cancel")
    if send is False:
        return
    txt = await callListen(call, 180, buttons=_package_edit_buttons(package_key))
    if txt is False:
        return
    if txt.text == "/cancel":
        await txt.delete()
        return await package_edit(_, call)
    value = txt.text.strip()
    await txt.delete()
    try:
        if field == "db_port":
            value = int(value)
        if field == "emby_whitelist_line" and value.lower() == "none":
            value = None
        setattr(package, field, value)
        config.packages[package_key] = package
        save_config()
        reload_packages()
    except Exception as exc:
        return await editMessage(call, f"❌ 更新失败：{exc}", buttons=_package_edit_buttons(package_key))
    await package_edit(_, call)


@bot.on_callback_query(filters.regex(r"^package_default:") & admins_on_filter)
async def package_default(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    package_key = call.data.split(":", 1)[1]
    if package_key not in (config.packages or {}):
        return await editMessage(call, "❌ 未找到套餐。", buttons=_package_panel_buttons())
    config.default_package = package_key
    save_config()
    reload_packages()
    await editMessage(call, f"✅ 已设置默认套餐为 `{package_key}`。", buttons=_package_edit_buttons(package_key))


@bot.on_callback_query(filters.regex(r"^package_delete:") & admins_on_filter)
async def package_delete(_, call):
    if not await _ensure_perm(call, "config_advanced"):
        return
    package_key = call.data.split(":", 1)[1]
    if not config.packages or package_key not in config.packages:
        return await editMessage(call, "❌ 未找到套餐。", buttons=_package_panel_buttons())
    if config.default_package == package_key:
        return await editMessage(call, "⚠️ 默认套餐不能删除。", buttons=_package_edit_buttons(package_key))
    del config.packages[package_key]
    save_config()
    reload_packages()
    await editMessage(call, f"✅ 已删除套餐 `{package_key}`。", buttons=_package_panel_buttons())
