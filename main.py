from asyncblink import signal

from spring import LobbyProtocolWrapper, LobbyProtocol, connections

import asyncio
import ruamel.yaml as yaml
import ssl
import logging

loop = asyncio.get_event_loop()
loop.set_debug(True)

logging.basicConfig(level=logging.DEBUG)


class Bot:

    async def init_bot(self):

        self.logger = logging.getLogger("asyncspring.main")
        self.logger.setLevel(logging.DEBUG)

        with open("config.yaml", 'r') as yml_file:
            cfg = yaml.safe_load(yml_file)

        self.lobby_host = cfg["lobby"]["host"]
        self.lobby_port = cfg["lobby"]["port"]
        self.lobby_user = cfg["lobby"]["user"]
        self.lobby_pass = cfg["lobby"]["pass"]
        self.enable_ssl = cfg["lobby"]["ssl"]

        if self.enable_ssl:
            sslctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        else:
            sslctx = False

        self.bot = await self.connect(self.lobby_host, port=self.lobby_port, use_ssl=sslctx)

        self.channels = cfg["lobby"]["channels"]

        for channel in self.channels:
            self.bot.channels_to_join.append(channel)

        self.login()

        signal("reconnected").connect(self.login)
        signal("connection-lost").connect(self.reconnect)

        @self.bot.on("SAID")
        def incoming_message(self, parsed, user, target, text):
            log.debug(parsed, user, target, text)
            self.bot.say(target, "{}: you said {}".format(user.nick, text))

    def login(self, args=None):
        for channel in self.channels:
            self.bot.channels_to_join.append(channel)
        self.bot.login(self.lobby_user, self.lobby_pass)

    async def connect(self, server, port=8200, use_ssl=False, name=None):
        """
        Connect to an SpringRTS Lobby server. Returns a proxy to an LobbyProtocol object.
        """
        protocol = None
        while protocol is None:
            try:
                transport, protocol = await loop.create_connection(LobbyProtocol, host=server, port=port, ssl=use_ssl)
            except ConnectionRefusedError as conn_error:
                self.logger.info("HOST DOWN! retry in 10 secs {}".format(conn_error))
                await asyncio.sleep(10)

        self.logger.info("connected")
        protocol.wrapper = LobbyProtocolWrapper(protocol)
        protocol.server_info = {"host": server, "port": port, "ssl": use_ssl}
        protocol.netid = "{}:{}:{}{}".format(id(protocol), server, port, "+" if use_ssl else "-")

        signal("netid-available").send(protocol)

        connections[protocol.netid] = protocol.wrapper

        return protocol.wrapper

    async def reconnect(self, client_wrapper):
        protocol = None
        server_info = client_wrapper.server_info

        self.logger.info("reconnecting")
        while protocol is None:
            await asyncio.sleep(10)
            try:
                transport, protocol = await loop.create_connection(LobbyProtocol, **server_info)
                client_wrapper.protocol = protocol

                signal("netid-available").send(protocol)

                signal("reconnected").send()

            except ConnectionRefusedError as conn_error:
                self.logger.info("HOST DOWN! retry in 10 secs {}".format(conn_error))


def main():

    bot = Bot()

    loop.run_until_complete(bot.init_bot())
    loop.run_forever()


if __name__ == "__main__":
    main()
