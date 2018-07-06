from spring import connect

import asyncio
import yaml

loop = asyncio.get_event_loop()
loop.set_debug(True)


async def init_bot():

    with open("config.yaml", 'r') as yml_file:
        cfg = yaml.load(yml_file)

    bot = await connect(cfg["lobby"]["host"], port=cfg["lobby"]["port"])
    bot.login(cfg["lobby"]["user"], cfg["lobby"]["passwd"])

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
