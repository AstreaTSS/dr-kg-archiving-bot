import os
import subprocess
import typing
import urllib.parse
from pathlib import Path

import attr
import discord
import rtoml
from discord.ext import commands

config = rtoml.load(Path(os.environ.get("CONFIG_PATH")))

os.environ.get("DIRECTORY_OF_FILE")


@attr.s
class BaseChannel:
    id: int = attr.ib()
    name: str = attr.ib()

    @property
    def path(self) -> str:
        return config["archive_location"]

    @property
    def base_url(self) -> str:
        return os.environ.get("WEBSITE_BASE") + config["github_name"]


@attr.s(slots=True)
class Category(BaseChannel):
    internal_name: str = attr.ib()
    channels: typing.List["Channel"] = attr.ib(factory=list)

    @property
    def path(self):
        return f"{super().path}/{self.internal_name}"

    @property
    def url_quote(self):
        return urllib.parse.quote(f"{self.internal_name}/{self.internal_name}.md")

    @property
    def url_path(self):
        return f"{self.base_url}/{self.url_quote}"

    def mkdir(self):
        os.mkdir(self.path)


@attr.s(slots=True)
class Channel(BaseChannel):
    category: Category = attr.ib()
    threads: typing.List["Thread"] = attr.ib(factory=list)

    @property
    def path(self):
        return f"{super().path}/{self.category.internal_name}/{self.id}.html"

    @property
    def url_quote(self):
        return urllib.parse.quote(f"{self.category.internal_name}/{self.id}.html")

    @property
    def url_path(self):
        return f"{self.base_url}/{self.url_quote}"

    @property
    def folder_path(self):
        return self.path.replace(".html", "")

    @property
    def proper_name(self):
        return self.name.replace("-", " ").title()

    def mkdir(self):
        os.mkdir(self.folder_path)


@attr.s(slots=True)
class Thread(BaseChannel):
    channel: Channel = attr.ib()

    @property
    def path(self):
        return f"{super().path}/{self.channel.category.internal_name}/{self.channel.id}/{self.id}.html"

    @property
    def url_quote(self):
        return urllib.parse.quote(
            f"{self.channel.category.internal_name}/{self.channel.id}/{self.id}.html"
        )

    @property
    def url_path(self):
        return f"{self.base_url}/{self.url_quote}"


class Archive(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def unarchive_threads(self, ctx: commands.Context):
        async with ctx.channel.typing():
            for category_entry in config["categories"]:
                category: discord.CategoryChannel = ctx.guild.get_channel(
                    category_entry["id"]
                )  # type: ignore
                for channel in category.text_channels:
                    async for archived_channel in channel.archived_threads(limit=None):
                        await archived_channel.edit(archived=False)
                        await archived_channel.join()

        await ctx.reply("Done!")

    async def archive(self, ctx: commands.Context):
        categories: typing.List[Category] = []

        await ctx.reply("Here we go. This will take a *long* time.")

        async with ctx.channel.typing():
            for category_entry in config["categories"]:
                category = Category(
                    category_entry["id"],
                    category_entry["name"],
                    category_entry["internal_name"],
                )
                category.mkdir()

                category_channel: discord.CategoryChannel = ctx.guild.get_channel(
                    category.id
                )  # type: ignore
                for discord_channel in category_channel.text_channels:
                    channel = Channel(
                        discord_channel.id, discord_channel.name, category
                    )

                    if discord_channel.threads:
                        channel.mkdir()

                        for discord_thread in discord_channel.threads:
                            thread = Thread(
                                discord_thread.id, discord_thread.name, channel
                            )
                            channel.threads.append(thread)

                        subprocess.run(
                            [
                                "dotnet",
                                str(os.environ.get("EXPORTER_DLL_PATH")),
                                "export -t",
                                f'"{os.environ.get("MAIN_TOKEN")}"',
                                "-b -c",
                                " ".join([str(t.id) for t in channel.threads]),
                                "-o",
                                f"{channel.folder_path}/%c",
                                "--dateformat u",
                                "--media --reuse-media",
                            ]
                        )

                    category.channels.append(channel)

                subprocess.run(
                    [
                        "dotnet",
                        str(os.environ.get("EXPORTER_DLL_PATH")),
                        "export -t",
                        f'"{os.environ.get("MAIN_TOKEN")}"',
                        "-b -c",
                        " ".join([str(c.id) for c in category.channels]),
                        "-o",
                        f"{category.path}/%c",
                        "--dateformat u",
                        "--media --reuse-media",
                    ]
                )

                with open(
                    f"{category.path}/{category.internal_name}.md",
                    "w",
                    encoding="utf-8",
                ) as md_file:
                    md_file.write(
                        f"# Season {config['season_num']} - {category.name}\n\nAll Locations:\n"
                    )
                    for channel in category.channels:
                        md_file.write(
                            f"* [{channel.proper_name}]({channel.url_path})\n"
                        )

                        for thread in channel.threads:
                            md_file.write(f"  * [{thread.name}]({thread.url_path})\n")
                    md_file.write(f"\n[Back to Home]({channel.base_url})")

                categories.append(category)

            with open(
                f"{config['archive_location']}/README.md", "w", encoding="utf-8"
            ) as md_file:
                md_file.write("# Home Page\n\nAll Categories:\n")

                for category in categories:
                    md_file.write(f"* [{category.name}]({category.url_path})\n")

        await ctx.reply("Done!")


def setup(bot):
    bot.add_cog(Archive(bot))
