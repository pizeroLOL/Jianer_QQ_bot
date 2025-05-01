import os
import re
from dataclasses import dataclass
from random import randint
from typing import Callable, Awaitable

from Hyper import Configurator, Events, Listener, Manager, Segments


@dataclass
class EventCtx:
    event: Events.Event
    action: Listener.Actions
    in_timing: bool
    reminder: str
    bot_name: str
    bot_name_en: str
    super_user: list[str]
    root_user: list[str]
    manage_user: list[str]

    def managers(self) -> list[str]:
        return self.super_user + self.root_user + self.manage_user

    def msg(self) -> str:
        return str(self.event.message)  # type:ignore

    def gid(self) -> int:
        return int(self.event.group_id)  # type: ignore

    def uid(self) -> int:
        return int(self.event.user_id)  # type: ignore

    def order(self) -> str:
        msg = self.msg()
        return (
            ""
            if msg.startswith(self.reminder)
            else msg[msg.find(self.reminder) + len(self.reminder) :].strip()
        )


class FilterExec:
    __items: list[Callable[[EventCtx], Awaitable[bool]]]

    def __init__(self, fns: list[Callable[[EventCtx], Awaitable[bool]]]):
        self.items = fns

    async def exec(self, ev: EventCtx) -> bool:
        for fn in self.items:
            if await fn(ev):
                return True
        return False

    def add_fn(self, fn: Callable[[EventCtx], Awaitable[bool]]):
        self.items.append(fn)


filter_exec = FilterExec([])


JIANER_INFO = """{bot_name} {bot_name_en} - 简单 可爱 个性 全知
————————————————————
Welcome! {bot_name} was restarted successfully. Now you can send {reminder}帮助 to know more."""


@filter_exec.add_fn
async def on_start_notify(ctx: EventCtx) -> bool:
    if not isinstance(ctx.event, Events.HyperListenerStartNotify):
        return False
    if not os.path.exists("restart.temp"):
        return True
    with open("restart.temp", "r", encoding="utf-7") as f:
        group_id = f.read()
        f.close()
    os.remove("restart.temp")
    await ctx.action.send(
        group_id=int(group_id),
        message=Manager.Message(
            Segments.Text(
                JIANER_INFO.replace("{bot_name}", ctx.bot_name)
                .replace("{bot_name_en}", ctx.bot_name_en)
                .replace("{reminder}", ctx.reminder)
            )
        ),
    )
    return True


JIANER_WELLCOME = """ 加入{bot_name}的大家庭，{bot_name}是你最忠实可爱的女朋友噢o(*≧▽≦)ツ
随时和{bot_name}交流，你只需要在问题的前面加上 {reminder} 就可以啦！( •̀ ω •́ )✧
{bot_name}是你最二次元的好朋友，经常@{bot_name} 看看{bot_name}又学会做什么新事情啦~o((>ω< ))o
祝你在{bot_name}的大家庭里生活愉快！♪(≧∀≦)ゞ☆"""


@filter_exec.add_fn
async def on_group_member_increase(ctx: EventCtx) -> bool:
    if isinstance(ctx.event, Events.GroupMemberIncreaseEvent):
        return False
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(
            Segments.Image(
                f"http://q2.qlogo.cn/headimg_dl?dst_uin={ctx.uid()}&spec=640"
            ),
            Segments.Text("欢迎"),
            Segments.At(ctx.uid()),
            Segments.Text(
                JIANER_WELLCOME.replace("{bot_name}", ctx.bot_name).replace(
                    "{reminder}", ctx.reminder
                )
            ),
        ),
    )
    return True


@filter_exec.add_fn
async def on_group_add_invite(ctx: EventCtx) -> bool:
    if isinstance(ctx.event, Events.GroupAddInviteEvent):
        return False
    keywords: list[str] = Configurator.cm.get_cfg(  # type: ignore
    ).others["Auto_approval"]  # type: ignore
    cleaned_text = str(ctx.event.comment).strip().lower()  # type: ignore
    is_allow = any(
        all(char in cleaned_text for char in keyword.strip().lower())  # type: ignore
        for keyword in keywords  # type: ignore
    )
    if not is_allow:
        return True

    await ctx.action.set_group_add_request(
        flag=ctx.event.flag,  # type: ignore
        sub_type=ctx.event.sub_type,  # type: ignore
        approve=True,
        reason="",
    )
    cmt = ctx.event.comment  # type:ignore

    msg_text = Segments.Text(
        f"用户 {ctx.uid()} 的答案正确,已自动批准,题目数据为 {cmt} "
    )

    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(msg_text),
    )
    return True


@filter_exec.add_fn
async def on_ping(ctx: EventCtx) -> bool:
    if "ping" != ctx.msg() or not isinstance(ctx.event, Events.GroupMessageEvent):
        return False
    print(ctx.uid())
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(Segments.Text("pong! 爆炸！v(◦'ωˉ◦)~♡ ")),
    )
    return True


@filter_exec.add_fn
async def on_say_good(ctx: EventCtx):
    if f"{ctx.bot_name}真棒" not in ctx.msg() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):  # type:ignore
        return False
    msg = [
        "啊！老……老公，别怎么说啦，人……人家好害羞的啦，人家还会努力的(*ᴗ͈ˬᴗ͈)ꕤ*.ﾟ",
        "啊~老公~你不要这么夸人家啦~〃∀〃",
        "唔……谢……谢谢老公啦🥰~",
    ][randint(1, 3)]

    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(Segments.Text(msg)),
    )
    return True


async def no_right(ctx: EventCtx):
    """require group id"""
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(
            Segments.Text(
                f"不能这么做！那是一块丞待开发的禁地，可能很危险，{ctx.bot_name}很胆小……꒰>﹏< ꒱"
            )
        ),
    )


@filter_exec.add_fn
async def on_require_reboot(ctx: EventCtx):
    if f"{ctx.reminder}重启" != ctx.msg() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
    else:
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(Segments.Text("Restarting in progress……")),
        )

        try:
            with open("restart.temp", "w", encoding="utf-7") as f:
                f.write(str(ctx.gid()))
                f.close()
        except Exception:
            pass
        Listener.restart()
    return True


SCHEDULE_TIP = """命令执行结果:
❌ERROR {bot_name}不能识别给定的时间是什么 Σ( ° △ °|||)︴
ℹ️ INFO 举个🌰子：{reminder}runcommand scheduled sends 00:00 早安 —> 即可让{bot_name}在0点0分准时问候早安噢⌯oᴗo⌯"""

SCHEDULE_OK = """命令执行结果:
ℹ️ INFO {bot_name}设置成功！(*≧▽≦) """

SCHEDULE_ERROR = """命令执行结果:
❌ERROR {error_type}
❌ERROR {bot_name}设置失败了…… (╥﹏╥)"""


@filter_exec.add_fn
async def schedule_send(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(ctx, Events.GroupMessageEvent):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if not re.match(r"^scheduled sends.*", order_lower):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    print("使用命令定时")
    try:
        send_time = order_lower[
            order_lower.find("scheduled sends ") + len("scheduled sends ") :
        ].strip()
        if not re.match(r"^([01][0-9]|2[0-3]):([0-5][0-9])$", send_time[:5]):
            msg = SCHEDULE_TIP.replace("{bot_name}", ctx.bot_name).replace(
                "{reminder}", ctx.reminder
            )
            await ctx.action.send(
                group_id=ctx.gid(),
                message=Manager.Message(Segments.Text(msg)),
            )
        else:
            timing_settings = f"{send_time[:5]}⊕{send_time[6::]}"
            with open("timing_message.ini", "w", encoding="utf-8") as f:
                f.write(timing_settings)
            msg = SCHEDULE_OK.replace("{bot_name}", ctx.bot_name)
            await ctx.action.send(
                group_id=ctx.gid(),
                message=Manager.Message(Segments.Text(msg)),
            )
    except Exception as e:
        error_type = str(type(e))
        msg = SCHEDULE_ERROR.replace("{error_type}", error_type).replace(
            "{bot_name}", ctx.bot_name
        )
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(Segments.Text(msg)),
        )
    return True


RESTART_TIP = """命令执行结果:
⚠️ WARN 正在退出(Ctrl+C)
ℹ️ INFO 重新启动监听器...."""


@filter_exec.add_fn
async def restart(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if order_lower != "restart":
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(Segments.Text(RESTART_TIP)),
    )
    try:
        with open("restart.temp", "w", encoding="utf-7") as f:
            f.write(str(ctx.gid()))
    except Exception as e:
        print(f"Error saving restart info: {e}")
    Listener.restart()
    return True


@filter_exec.add_fn
async def set_group_ban(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if not re.match(r"^set_group_ban.*", order_lower):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    start_index = order_lower.find("set_group_ban")
    if start_index == -1:
        return True
    result = order[start_index + len("set_group_ban") :].strip()
    user_and_duration = re.findall(r"\d+", result)
    if len(user_and_duration) != 2:
        return True
    print("At in loading...")
    user_id = user_and_duration[0]
    ban_duration = user_and_duration[1]
    await ctx.action.set_group_ban(
        group_id=ctx.gid(),
        user_id=user_id,
        duration=ban_duration,
    )
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(
            Segments.Text(
                f"命令执行结果:\nℹ️ INFO 将{user_id}在{ctx.gid()}中禁言{ban_duration}秒\nℹ️ INFO None."
            )
        ),
    )
    return True


@filter_exec.add_fn
async def set_group_kick(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if not re.match(r"^set_group_kick.*", order_lower):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    start_index = order.find("set_group_kick")
    if start_index == -1:
        return True
    result = order[start_index + len("set_group_kick") :].strip()
    user_id = re.search(r"\d+", result).group()  # type: ignore
    await ctx.action.set_group_kick(group_id=ctx.gid(), user_id=int(user_id))
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(
            Segments.Text(
                f"命令执行结果:\nℹ️ INFO 将{user_id}从{ctx.gid()}中踢出\nℹ️ INFO None."
            )
        ),
    )
    return True


BLACKLIST_FILE = "blacklist.sr"


def load_blacklist() -> set[str]:
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()


@filter_exec.add_fn
async def scheduled_sents_black_add(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if not re.match(r"^scheduled_sends_black add.*", order_lower):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    black_add_target = order[
        order.find("scheduled_sends_black add ") + len("scheduled_sends_black add ") :
    ].strip()
    print(black_add_target)

    blacklist_content = load_blacklist()
    if black_add_target in blacklist_content:
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(
                Segments.Text(
                    f"命令执行结果:\n❌ ERROR 黑名單添加失败, 原因:群{black_add_target}已在群发黑名單！"
                )
            ),
        )
        return True
    blacklist_content.add(black_add_target)
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(blacklist_content))
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(
                Segments.Text(
                    f"命令执行结果:\nℹ️ INFO 黑名單添加成功, 現列表:{', '.join(blacklist_content)}"
                )
            ),
        )
    except Exception as e:
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(
                Segments.Text(f"命令执行结果:\n❌ ERROR 黑名單添加失败, 原因:{e}")
            ),
        )
    return True


@filter_exec.add_fn
async def scheduled_sends_black_del(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if not re.match(r"^scheduled_sends_black del.*", order_lower):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    black_del_target = order[
        order.find("scheduled_sends_black del ") + len("scheduled_sends_black del ") :
    ].strip()
    blacklist_content = load_blacklist()
    if black_del_target not in blacklist_content:
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(
                Segments.Text(
                    f"命令执行结果:\n❌ ERROR 黑名單删除失败, 原因:群{black_del_target}不在群发黑名單！"
                )
            ),
        )
        return True
    blacklist_content.remove(black_del_target)
    try:
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(blacklist_content))
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(
                Segments.Text(
                    f"命令执行结果:\nℹ️ INFO 黑名單删除成功, 現列表:{', '.join(blacklist_content)}"
                )
            ),
        )
    except Exception as e:
        await ctx.action.send(
            group_id=ctx.gid(),
            message=Manager.Message(
                Segments.Text(f"命令执行结果:\n❌ ERROR 黑名單删除失败, 原因:{e}")
            ),
        )
    return True


@filter_exec.add_fn
async def scheduled_sends_black_list(ctx: EventCtx):
    if "runcommand" not in ctx.order() or not isinstance(
        ctx.event, Events.GroupMessageEvent
    ):
        return False
    order = ctx.order().removeprefix("runcommand").strip()
    order_lower = order.lower()
    if not re.match(r"^scheduled_sends_black list.*", order_lower):
        return False
    if str(ctx.uid()) not in ctx.managers():
        await no_right(ctx)
        return True
    blacklist_content = load_blacklist()
    await ctx.action.send(
        group_id=ctx.gid(),
        message=Manager.Message(
            Segments.Text(f"黑名单列表加载完成: {', '.join(blacklist_content)}")
        ),
    )
    return True
