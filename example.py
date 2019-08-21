import ssl
import logging
import asyncio
import ruamel.yaml as yaml

from asyncblink import signal
from asyncspring import lobby


logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("example")
logger.setLevel(logging.DEBUG)


async def init_bot():
    with open("config.yaml", 'r') as yml_file:
        cfg = yaml.safe_load(yml_file)

    lobby_host = cfg["lobby"]["host"]
    lobby_port = cfg["lobby"]["port"]
    lobby_user = cfg["lobby"]["user"]
    lobby_pass = cfg["lobby"]["pass"]
    lobby_channels = cfg["lobby"]["channels"]
    enable_ssl = cfg["lobby"]["ssl"]

    if enable_ssl:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    else:
        ssl_context = False

    lobby_bot = await lobby.connect(lobby_host, port=lobby_port, use_ssl=ssl_context)

    lobby_bot.login(lobby_user, lobby_pass)

    for channel in lobby_channels:
        lobby_bot.channels_to_join.append(channel)

    logger.debug("Login success")

    def on_said(message, user, target, text):
        logger.info(message)

    def on_saidex(message, user, target, text):
        logger.info(message)

    # event signals
    signal("spring-raw").connect(on_said)
    signal("saidex").connect(on_saidex)

    # connection signals
    # signal("reconnected").connect(login)
    signal("connection-lost").connect(lobby.reconnect)

    logger.debug("init signals registered")


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(False)

    loop.run_until_complete(init_bot())
    loop.run_forever()


if __name__ == "__main__":
    main()
