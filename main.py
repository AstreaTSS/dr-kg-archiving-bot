import asyncio
import contextlib
import logging
import os
import sys

import interactions as ipy
import typing_extensions as typing
from interactions.ext import prefixed_commands as prefixed

from initialize import initialize

initialize()

import common.utils as utils

logger = logging.getLogger("kgarchivebot")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=os.environ["LOG_FILE_PATH"], encoding="utf-8", mode="a"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler(sys.stdout))


class KGArchiveBot(utils.KGArchiveBase):
    @ipy.listen("ready")
    async def on_ready(self) -> None:
        utcnow = ipy.Timestamp.utcnow()
        time_format = f"<t:{int(utcnow.timestamp())}:f>"

        connect_msg = (
            f"Logged in at {time_format}!"
            if self.init_load
            else f"Reconnected at {time_format}!"
        )

        await self.owner.send(connect_msg)

        self.init_load = False

        activity = ipy.Activity(
            name="Status",
            type=ipy.ActivityType.CUSTOM,
            state="Archiving servers",
        )
        await self.change_presence(activity=activity)

    @ipy.listen("resume")
    async def on_resume_func(self) -> None:
        activity = ipy.Activity(
            name="Status",
            type=ipy.ActivityType.CUSTOM,
            state="Archiving servers",
        )
        await self.change_presence(activity=activity)

    @ipy.listen(is_default_listener=True)
    async def on_error(self, event: ipy.events.Error) -> None:
        await utils.error_handle(event.error, ctx=event.ctx)

    def create_task(self, coro: typing.Coroutine) -> asyncio.Task:
        # see the "important" note below for why we do this (to prevent early gc)
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task

    async def stop(self) -> None:
        await super().stop()


intents = ipy.Intents.DEFAULT | ipy.Intents.MESSAGE_CONTENT
mentions = ipy.AllowedMentions.all()

bot = KGArchiveBot(
    activity=ipy.Activity(
        name="Status", type=ipy.ActivityType.CUSTOM, state="Loading..."
    ),
    status=ipy.Status.IDLE,
    sync_interactions=False,
    sync_ext=False,
    disable_dm_commands=True,
    allowed_mentions=mentions,
    intents=intents,
    auto_defer=ipy.AutoDefer(enabled=True, time_until_defer=0),
    logger=logger,
)
bot.init_load = True
prefixed.setup(bot)


async def start() -> None:
    ext_list = utils.get_all_extensions(os.environ["DIRECTORY_OF_FILE"])

    for ext in ext_list:
        try:
            bot.load_extension(ext)
        except ipy.errors.ExtensionLoadException:
            raise

    await bot.astart(os.environ["MAIN_TOKEN"])


if __name__ == "__main__":
    run_method = asyncio.run

    # use uvloop if possible
    with contextlib.suppress(ImportError):
        import uvloop  # type: ignore

        run_method = uvloop.run

    with contextlib.suppress(KeyboardInterrupt):
        run_method(start())
