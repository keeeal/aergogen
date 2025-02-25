from argparse import ArgumentParser
from pathlib import Path

from aergogen.bot import AergoGen
from aergogen.utils.config import Config, read_from_env_var
from aergogen.utils.logging import get_logger

LOGGER = get_logger(__name__)


def main(config_file: Path) -> None:
    try:
        token = read_from_env_var("DISCORD_TOKEN_FILE")
    except Exception as error:
        LOGGER.error(error)
        return

    config = Config.from_yaml(config_file, create_if_not_found=True)
    bot = AergoGen(**config.bot.model_dump())
    bot.run(token)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path, default="config.yaml")
    main(**vars(parser.parse_args()))
