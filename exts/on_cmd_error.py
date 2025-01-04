import importlib

import interactions as ipy
from interactions.ext import prefixed_commands as prefixed

import common.utils as utils

ValidContexts = prefixed.PrefixedContext | ipy.InteractionContext


class OnCMDError(utils.Extension):
    def __init__(self, bot: utils.KGArchiveBase) -> None:
        self.bot: utils.KGArchiveBase = bot

    @staticmethod
    async def handle_send(ctx: ValidContexts, content: str) -> None:
        embed = utils.error_embed_generate(content)
        if isinstance(ctx, prefixed.PrefixedContext):
            await ctx.reply(embeds=embed)
        else:
            await ctx.send(
                embeds=embed,
                ephemeral=(not ctx.responded and not ctx.deferred) or ctx.ephemeral,
            )

    @ipy.listen(disable_default_listeners=True)
    async def on_command_error(
        self,
        event: ipy.events.CommandError,
    ) -> None:
        if not isinstance(event.ctx, ValidContexts):
            return await utils.error_handle(event.error)

        if isinstance(event.error, ipy.errors.CommandOnCooldown):
            await self.handle_send(
                event.ctx,
                "You're doing that command too fast! Try again in"
                f" `{event.error.cooldown.get_cooldown_time():.2f}` seconds.",
            )

        elif isinstance(event.error, utils.CustomCheckFailure | ipy.errors.BadArgument):
            await self.handle_send(event.ctx, str(event.error))
        elif isinstance(event.error, ipy.errors.CommandCheckFailure):
            if event.ctx.guild_id:
                await self.handle_send(
                    event.ctx,
                    "You do not have the proper permissions to use that command.",
                )
        else:
            await utils.error_handle(event.error, ctx=event.ctx)

    @ipy.listen(ipy.events.ModalError, disable_default_listeners=True)
    async def on_modal_error(self, event: ipy.events.ModalError) -> None:
        await self.on_command_error.callback(self, event)

    @ipy.listen(ipy.events.ComponentError, disable_default_listeners=True)
    async def on_component_error(self, event: ipy.events.ComponentError) -> None:
        await self.on_command_error.callback(self, event)


def setup(bot: utils.KGArchiveBase) -> None:
    importlib.reload(utils)
    OnCMDError(bot)
