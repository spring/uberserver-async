from .spring import connect

import asyncio
import yaml
import ssl
from hashlib import md5
from base64 import b64encode as ENCODE_FUNC

loop = asyncio.get_event_loop()
loop.set_debug(True)


def encode_password(password):
    return ENCODE_FUNC(md5(password.encode()).digest()).decode()

async def init_bot():

    with open("config.yaml", 'r') as yml_file:
        cfg = yaml.load(yml_file)

    lobby_host = cfg["lobby"]["host"]
    lobby_port = cfg["lobby"]["port"]
    lobby_user = cfg["lobby"]["user"]
    lobby_pass = encode_password(cfg["lobby"]["pass"])
    enable_ssl = cfg["lobby"]["ssl"]

    if enable_ssl:
        sslctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    else:
        sslctx = False

    bot = await connect(lobby_host, port=lobby_port, use_ssl=sslctx)
    bot.login(lobby_user, lobby_pass)

    @bot.on("message")
    def incoming_message(parsed, user, target, text):
        # parsed is an RFC1459Message object
        # user is a User object with nick, user, and host attributes
        # target is a string representing nick/channel the message was sent to
        # text is the text of the message
        bot.say(target, "{}: you said {}".format(user.nick, text))


def main():

    print("connect to springlobby")

    loop.run_until_complete(init_bot())
    loop.run_forever()


if __name__ == "__main__":
    main()
