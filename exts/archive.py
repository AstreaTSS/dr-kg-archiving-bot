import asyncio
import importlib
import os
import urllib.parse

import attrs
import interactions as ipy
import tomli
from interactions.ext import prefixed_commands as prefixed

import common.utils as utils

with open(f"{os.environ["DIRECTORY_OF_FILE"]}/kg_config.toml", "rb") as config_file:
    CONFIG = tomli.load(config_file)


@attrs.define()
class BaseChannel:
    id: int = attrs.field()
    name: str = attrs.field()

    @property
    def path(self) -> str:
        return CONFIG["archive_location"]

    @property
    def base_url(self) -> str:
        return os.environ["WEBSITE_BASE"] + CONFIG["github_name"]


@attrs.define()
class Category(BaseChannel):
    internal_name: str = attrs.field()
    channels: list["Channel"] = attrs.field(factory=list)

    @property
    def path(self) -> str:
        return f"{super().path}/{self.internal_name}"

    @property
    def url_quote(self) -> str:
        return urllib.parse.quote(f"{self.internal_name}/{self.internal_name}")

    @property
    def url_path(self) -> str:
        return f"{self.base_url}/{self.url_quote}"

    def mkdir(self) -> None:
        os.mkdir(self.path)


@attrs.define()
class Channel(BaseChannel):
    category: Category = attrs.field()
    threads: list["Thread"] = attrs.field(factory=list)

    @property
    def path(self) -> str:
        return f"{super().path}/{self.category.internal_name}/{self.id}.html"

    @property
    def url_quote(self) -> str:
        return urllib.parse.quote(f"{self.category.internal_name}/{self.id}.html")

    @property
    def url_path(self) -> str:
        return f"{self.base_url}/{self.url_quote}"

    @property
    def folder_path(self) -> str:
        return self.path.replace(".html", "")

    @property
    def proper_name(self) -> str:
        return self.name.replace("-", " ").title()

    def mkdir(self) -> None:
        os.mkdir(self.folder_path)


@attrs.define()
class Thread(BaseChannel):
    channel: Channel = attrs.field()

    @property
    def path(self) -> str:
        return f"{super().path}/{self.channel.category.internal_name}/{self.channel.id}/{self.id}.html"

    @property
    def url_quote(self) -> str:
        return urllib.parse.quote(
            f"{self.channel.category.internal_name}/{self.channel.id}/{self.id}.html"
        )

    @property
    def url_path(self) -> str:
        return f"{self.base_url}/{self.url_quote}"


class Archive(utils.Extension):
    def __init__(self, bot: utils.KGArchiveBase) -> None:
        self.bot: utils.KGArchiveBase = bot

    @prefixed.prefixed_command()
    @ipy.check(ipy.is_owner())
    @ipy.check(ipy.guild_only())
    async def archive(self, ctx: prefixed.PrefixedContext) -> None:
        categories: list[Category] = []

        await ctx.reply(
            embeds=utils.make_embed("Here we go. This will take a *long* time.")
        )

        async with ctx.channel.typing:
            for category_entry in CONFIG["categories"]:
                category = Category(
                    category_entry["id"],
                    category_entry["name"],
                    category_entry["internal_name"],
                )
                category.mkdir()

                category_channel: ipy.GuildCategory = ctx.guild.get_channel(
                    category_entry["id"]
                )
                for discord_channel in category_channel.text_channels:
                    channel = Channel(
                        discord_channel.id, discord_channel.name, category
                    )

                    threads = await discord_channel.fetch_all_threads()

                    if threads.threads:
                        channel.mkdir()

                        for discord_thread in threads.threads:
                            thread = Thread(
                                discord_thread.id, discord_thread.name, channel
                            )
                            channel.threads.append(thread)

                        command_list = [
                            os.environ["CLI_EXECUTABLE"],
                            "export -t",
                            f'"{os.environ["MAIN_TOKEN"]}"',
                            " -c",
                            " ".join([str(t.id) for t in channel.threads]),
                            "-o",
                            f'"{channel.folder_path}/%c.html"',
                            "--utc",
                            "--parallel 10",
                            "--media --reuse-media --fuck-russia",
                        ]
                        command = " ".join(command_list)

                        process = await asyncio.create_subprocess_shell(command)
                        await process.wait()

                    category.channels.append(channel)

                command_list = [
                    os.environ["CLI_EXECUTABLE"],
                    "export -t",
                    f'"{os.environ["MAIN_TOKEN"]}"',
                    " -c",
                    " ".join([str(c.id) for c in category.channels]),
                    "-o",
                    f'"{category.path}/%c.html"',
                    "--utc",
                    "--parallel 10",
                    "--media --reuse-media --fuck-russia",
                ]
                command = " ".join(command_list)

                process = await asyncio.create_subprocess_shell(command)
                await process.wait()

                with open(
                    f"{category.path}/{category.internal_name}.md",
                    "w",
                    encoding="utf-8",
                ) as md_file:
                    md_file.write(f"# {category.name}\n\nAll Locations:\n")

                    # TODO: add some control over this
                    # md_file.write(
                    #     f"# Season {CONFIG['season_num']} - {category.name}\n\nAll"
                    #     " Locations:\n"
                    # )
                    for channel in category.channels:
                        md_file.write(
                            f"* [{channel.proper_name}]({channel.url_path})\n"
                        )

                        for thread in channel.threads:
                            md_file.write(f"  * [{thread.name}]({thread.url_path})\n")
                    md_file.write(f"\n[Back to Home]({channel.base_url})")

                categories.append(category)

            with open(
                f"{CONFIG['archive_location']}/README.md", "w", encoding="utf-8"
            ) as md_file:
                md_file.write("# Home Page\n\nAll Categories:\n")

                for category in categories:
                    md_file.write(f"* [{category.name}]({category.url_path})\n")

        await ctx.reply(embeds=utils.make_embed("Done!"))


def setup(bot: utils.KGArchiveBase) -> None:
    importlib.reload(utils)
    Archive(bot)
