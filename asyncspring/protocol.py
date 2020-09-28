#!/usr/bin/env python3
# coding=utf-8

import re
import asyncio
import importlib
import collections
import logging
from copy import copy

from hashlib import md5
from base64 import b64encode
from pprint import pprint

from asyncblink import signal, ANY

connections = {}

plugins = []


def plugin_registered_handler(plugin_name):
    plugins.append(plugin_name)


signal("plugin-registered").connect(plugin_registered_handler)


def load_plugins(*plugins):
    for plugin in plugins:
        if plugin not in plugins:
            importlib.import_module(plugin)


def encode_password(password):
    return b64encode(md5(password.encode('utf-8')).digest()).decode()


class LobbyProtocolWrapper:
    """
    Wraps an LobbyProtocol object to allow for automatic reconnection. Only used
    internally.
    """

    def __init__(self, protocol):
        self.protocol = protocol

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return getattr(self.protocol, attr)

    def __attr__(self, attr, val):
        if attr == "protocol":
            self.protocol = val
        else:
            setattr(self.protocol, attr, val)


class LobbyProtocol(asyncio.Protocol):
    """
    Represents a connection to SpringRTS Lobby.
    """

    def connection_made(self, transport):
        self.loop = asyncio.get_event_loop()
        self.work = True
        self.transport = transport
        self.wrapper = None
        self.logger = logging.getLogger(__name__)
        self.last_ping = float('inf')
        self.last_pong = 0
        self.lag = 0
        self.buf = ""
        self.old_nickname = None
        self.bot_username = ""
        self.bot_password = ""
        self.server_supports = collections.defaultdict(lambda *_: None)
        self.queue = []
        self.queue_timer = 1.0  # seconds
        self.caps = set()
        self.registration_complete = False
        self.channels_to_join = []
        self.autoreconnect = True
        self.name = "AsyncSpring 0.1"
        self.flags = "sp u"

        self.signals = dict()

        self.signals["connected"] = signal("connected")
        self.signals["raw"] = signal("raw")
        self.signals["connection-lost"] = signal("connection-lost")
        self.signals["lobby-send"] = signal("lobby-send")
        self.signals["registration-complete"] = signal("registration-complete")
        self.signals["login-complete"] = signal("login-complete")

        self.signals["connected"].send(self)

        self.logger.debug("Connection success.")

        self.process_queue()

    def data_received(self, data):
        if not self.work:
            return

        data = data.decode()

        self.buf += data
        while "\n" in self.buf:
            index = self.buf.index("\n")
            line_received = self.buf[:index].strip()
            self.buf = self.buf[index + 1:]
            self.logger.debug("RECEIVED: {}".format(line_received))
            self.signals["raw"].send(self, text=line_received)

    def connection_lost(self, exc):
        if not self.work:
            return

        self.logger.critical("Connection lost.")
        self.signals["connection-lost"].send(self.wrapper)

    # Core helper functions

    def process_queue(self):
        """
        Pull data from the pending messages queue and send it. Schedule ourself
        to be executed again later.
        """

        if not self.work:
            return

        if len(self.queue) > 0:
            self.logger.debug(f"handle {len(self.queue)} messages")
            # self._writeln(self.queue.pop(0))
            messages = copy("\r\n".join(self.queue))
            self.logger.debug(messages)
            self._write(messages)
            self.queue.clear()

        self.loop.call_later(self.queue_timer, self.process_queue)

    def on(self, event):

        def process(f):
            """
            Register an event with Blinker. Convenience function.
            """
            self.logger.info("Registering function {} for event {}".format(f.__name__,  event))

            signal(event).connect(f, sender=ANY, weak=False)

            return f

        return process

    def _write(self, line):
        """
        Send a raw message to SpringRTS Lobby immediately.
        """

        self.logger.debug(f"SENT: {line}")
        self.transport.write(line)
        self.signals["lobby-send"].send(line)

    def _writeln(self, line):
        """
        Send a raw message with new line to SpringRTS Lobby immediately.
        """
        if not isinstance(line, bytes):
            line = line.encode("utf-8")

        # print(line)

        self.logger.debug("SENT: {}".format(line))
        self.transport.write(line)
        self.signals["lobby-send"].send(line)

    def writeln(self, line):
        """
        Queue a message for sending to the currently connected SpringRTS Lobby server.
        """

        self.queue.append(line)
        return self

    def register(self, username, password, email=None):
        """
        Queue registration with the server. This includes sending nickname,
        ident, realname, and password (if required by the server).
        """

        self.bot_username = username
        self.bot_password = encode_password(password)
        self.email = email

        if self.email:
            self.writeln("REGISTER {} {} {}".format(self.bot_username, self.bot_password, self.email))
        else:
            self.writeln("REGISTER {} {}".format(self.bot_username, self.bot_password))

        self.logger.info("Sent registration information")
        self.signals["registration-complete"].send(self)
        self.nickname = self.bot_username

    def accept(self):
        self.writeln("CONFIRMAGREEMENT")

    # protocol abstractions

    def login(self, username, password, flags=None):
        """
        Queue registration with the server. This includes sending nickname,
        ident, realname, and password (if required by the server).
        """
        self.bot_username = username
        self.bot_password = encode_password(password)

        if flags:
            self.flags = flags

        return self

    def _login(self):
        """
        Send Login message to SpringLobby Server.
        """
        self.writeln("LOGIN {} {} 3200 * {} 0   {}".format(self.bot_username, self.bot_password, self.name, self.flags))
        self.signals["login-complete"].send(self)
        self.logger.debug("Login Complete")

    def bridged_client_from(self, location, external_id, external_username):
        """
        Initialized the bridge
        """

        name = re.sub('[^A-Za-z0-9]+', '', external_username)

        self.writeln("BRIDGECLIENTFROM {} {} {}".format(location, external_id, name))

    def un_bridged_client_from(self, location, external_id):
        """
        Deinitialized the bridge
        """
        self.writeln("UNBRIDGECLIENTFROM {} {}".format(location, external_id))

    def join_from(self, channel, location, external_id):
        """
        Join from remote server.
        """
        self.writeln("JOINFROM {} {} {}".format(channel, location, external_id))

    def leave_from(self, channel, location, external_id):
        """
        Leave from remote server.
        """
        self.writeln("LEAVEFROM {} {} {}".format(channel, location, external_id))

    def say_from(self, user, domain, channel, body):
        """
        Say from remote server.
        """
        message = body.replace("\n", " ").replace("\r", " ")

        while message:
            self.writeln("SAYFROM {} {} {} {}".format(channel, domain, user, message[:200]))
            message = message[400:]

    def join(self, channel):
        """
        Join a channel.
        """
        self.writeln("JOIN {}".format(channel))

        return self

    def leave(self, channel):
        """
        Leave a channel.
        """

        self.writeln("LEAVE {}".format(channel))

    def say(self, channel, message):
        """
        Send a MSG to SpringRTS Lobby room.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", " ").replace("\r", " ")

        while message:
            self.writeln("SAY {} {}".format(channel, message[:400]))
            message = message[400:]

    def say_ex(self, channel, message):
        """
        Send a MSG to SpringRTS Lobby room using emote.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAYEX {} {}".format(channel, message[:400]))
            message = message[400:]

    def say_private(self, username, message):
        """
        Send a private message to SpringRTS Lobby user.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAYPRIVATE {} :{}".format(username, message[:400]))
            message = message[400:]

    def say_private_ex(self, username, message):
        """
        Send a private message to SpringRTS Lobby user in emote.
        Carriage returns and line feeds are stripped to prevent bugs.
        """

        message = message.replace("\n", "").replace("\r", "")

        while message:
            self.writeln("SAYPRIVATEEX {} :{}".format(username, message[:400]))
            message = message[400:]

    def ping(self):
        self.writeln("PING")
