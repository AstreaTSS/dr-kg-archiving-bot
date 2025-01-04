import os
import platform
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import requests
from dotenv import load_dotenv

IS_INITIALIZED = False

__all__ = ("initialize", "is_initialized", "set_initialized")


def is_initialized() -> bool:
    return IS_INITIALIZED


def set_initialized() -> None:
    global IS_INITIALIZED
    IS_INITIALIZED = True


def initialize() -> None:
    if is_initialized():
        return

    load_dotenv(override=True)

    file_location = Path(__file__).parent.absolute().as_posix()
    os.environ["DIRECTORY_OF_FILE"] = file_location
    os.environ["LOG_FILE_PATH"] = f"{file_location}/discord.log"

    cli_path = Path(__file__).parent.absolute().joinpath("cli")

    if os.path.exists(cli_path):
        output = subprocess.run(
            [cli_path.joinpath("DiscordChatExporter.Cli").as_posix(), "--version"],
            capture_output=True,
            check=True,
        )
        version = output.stdout.decode("utf-8").strip()

        response = requests.get(
            "https://api.github.com/repos/Tyrrrz/DiscordChatExporter/releases/latest"
        )
        response.raise_for_status()
        json_data = response.json()
        latest_version: str = json_data["tag_name"]

        if latest_version.count(".") == 1:
            latest_version += ".0"

        latest_version = f"v{latest_version}"

        if version != latest_version:
            shutil.rmtree(cli_path)

    if not os.path.exists(cli_path):
        os.mkdir(cli_path)

        match platform.system():
            case "Windows":
                os_name = "win"
            case "Darwin":
                os_name = "osx"
            case "Linux":
                os_name = "linux"
            case _:
                raise ValueError("Unsupported operating system.")

        match platform.machine():
            case "x86_64":
                arch = "x64"
            case "amd64":
                arch = "x64"
            case "x86":
                arch = "x86"
            case "i386":
                arch = "x86"
            case "i686":
                arch = "x86"
            case "armv7l":
                arch = "arm"
            case "armv6l":
                arch = "arm"
            case "aarch64":
                arch = "arm64"
            case "arm64":
                arch = "arm64"
            case _:
                raise ValueError("Unsupported architecture.")

        if os_name != "win" and arch == "x86":
            raise ValueError("Unsupported operating system or architecture.")

        url = f"https://github.com/Tyrrrz/DiscordChatExporter/releases/latest/download/DiscordChatExporter.Cli.{os_name}-{arch}.zip"

        response = requests.get(url)
        response.raise_for_status()

        with open(cli_path.joinpath("cli.zip"), "wb") as file:
            file.write(response.content)

        with ZipFile(cli_path.joinpath("cli.zip"), "r") as zip_ref:
            zip_ref.extractall(cli_path)

        os.remove(cli_path.joinpath("cli.zip"))
        os.chmod(cli_path.joinpath("DiscordChatExporter.Cli"), 0o755)  # noqa: S103

    os.environ["CLI_EXECUTABLE"] = cli_path.joinpath(
        "DiscordChatExporter.Cli"
    ).as_posix()

    set_initialized()
