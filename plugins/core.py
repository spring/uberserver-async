from asyncblink import signal
from asyncspring.spring import get_user
from asyncspring.parser import LobbyMessage

import asyncio
import time
import logging

log = logging.getLogger(__name__)

ping_clients = []


def _pong(message):
    message.client.writeln("PONG {}".format(message.params[0]))


def _redispatch_message_common(message, mtype):
    user = message.source
    target, text = message.params[0], " ".join(message.params[2:])
    signal(mtype).send(message, user=user, target=target, text=text)


def _redispatch_said(message):
    _redispatch_message_common(message, "said")


def _redispatch_saidex(message):
    _redispatch_message_common(message, "saidex")


def _redispatch_saidprivate(message):
    _redispatch_message_common(message, "said-private")


def _redispatch_saidprivateex(message):
    _redispatch_message_common(message, "saidex-private")


def _redispatch_notice(message):
    _redispatch_message_common(message, "notice")


def _redispatch_joined(message):
    signal("joined").send(message, user=get_user(message.params[1]), channel=message.params[0])


def _redispatch_left(message):
    user = get_user(message.params[1])
    channel, reason = message.params[0], None
    if len(message.params) > 1:
        reason = message.params[1]
    signal("left").send(message, user=user, channel=channel, reason=reason)


def _redispatch_quit(message):
    signal("quit").send(message, user=get_user(message.source), reason=message.params[0])


def _redispatch_kick(message):
    kicker = get_user(message.source)
    channel, kickee, reason = message.params[0], get_user(message.params[1]), message.params[2]
    signal("kick").send(message, kicker=kicker, kickee=kickee, channel=channel, reason=reason)


def _redispatch_nick(message):
    old_user = get_user(message.source)
    new_nick = message.params[0]
    if old_user.nick == message.client.nickname:
        message.client.nickname = new_nick
    signal("nick").send(message, user=old_user, new_nick=new_nick)


def _parse_mode(message):
    # :ChanServ!ChanServ@services. MODE ##fwilson +o fwilson
    if "CHANMODES" in message.client.server_supports:
        argument_modes = "".join(message.client.server_supports["CHANMODES"].split(",")[:-1])
        argument_modes += message.client.server_supports["PREFIX"].split(")")[0][1:]
    else:
        argument_modes = "beIqaohvlk"
    log.info("argument_modes are", argument_modes)
    user = get_user(message.source)
    channel = message.params[0]
    modes = message.params[1]
    args = message.params[2:]
    flag = "+"
    for mode in modes:
        if mode in "+-":
            flag = mode
            continue
        if mode in argument_modes:
            arg = args.pop(0)
        else:
            arg = None
        signal("{}mode".format(flag)).send(message, mode=mode, arg=arg, user=user, channel=channel)
        signal("mode {}{}".format(flag, mode)).send(message, arg=arg, user=user, channel=channel)


def _server_supports(message):
    supports = message.params[1:-1]  # No need for "Are supported by this server" or bot's nickname
    log.info("Server supports {}".format(supports))
    for feature in supports:
        if "=" in feature:
            k, v = feature.split("=")
            message.client.server_supports[k] = v
        else:
            message.client.server_supports[feature] = True


def _nick_in_use(message):
    message.client.old_nickname = message.client.nickname
    s = message.client.nick_in_use_handler()

    def callback():
        message.client.nickname = s
        message.client.writeln("NICK {}".format(s))

    # loop.call_later(5, callback)


def _ping_servers():
    for client in ping_clients:
        if client.last_pong != 0 and time.time() - client.last_pong > 90:
            del ping_clients[:]
            client.connection_lost(Exception())
        client.writeln("PING")
        client.last_ping = time.time()

    asyncio.get_event_loop().call_later(29, _ping_servers)


def _catch_pong(message):
    message.client.last_pong = time.time()
    message.client.lag = message.client.last_pong - message.client.last_ping
    signal("pong").send(message)


def _redispatch_spring(message):
    signal("spring-{}".format(message.verb.lower())).send(message)


def _redispatch_raw(client, text):
    message = LobbyMessage.from_message(text)
    message.client = client
    # log.debug(message)
    signal("spring").send(message)


def _register_client(client):
    log.info("Sending real registration message")
    asyncio.get_event_loop().call_later(1, client._register)


def _login_client(client):
    log.info("Server login")
    asyncio.get_event_loop().call_later(1, client._login)


def _queue_ping(client):
    ping_clients.append(client)
    _ping_servers()


def _connection_registered(message):
    signal("accepted").send(message)

    message.client.registration_complete = True
    _queue_ping(message.client)
    for channel in message.client.channels_to_join:
        log.debug(channel)
        message.client.join(channel)


def _connection_denied(message):
    message.client.registration_complete = False
    signal("denied").send(message)


def _parse_motd(message):
    pass
    # log.info(message)


def _redispatch_clients(message):
    signal("clients").send(message)


def _redispatch_adduser(message):
    signal("adduser").send(message)


def _redispatch_removeuser(message):
    signal("removeuser").send(message)


def _redispatch_agreement(message):
    signal("agreement_end").send(message)


def _redispatch_bridged_client(message):
    log.debug("BRIDGED CLIENT")
    log.debug(message)


def _redispatch_un_bridged_client(message):
    log.debug("UNBRIDGETD CLIENT FROM")
    log.debug(message)


def _redispatch_joined_from(message):
    log.debug("JOINED FROM")
    log.debug(message)


def _redispatch_left_from(message):
    log.debug("LEFT FROM")
    log.debug(message)


def _redispatch_said_from(message):
    log.debug("SAID FROM")
    log.debug(message)


def _redispatch_clients_from(message):
    log.debug("CLIENTS FROM")
    log.debug(message)


def _redispatch_logininfoend(message):
    signal("logininfoend").send(message)


signal("raw").connect(_redispatch_raw)
signal("spring").connect(_redispatch_spring)

signal("connected").connect(_login_client)

signal("spring-ping").connect(_pong)
signal("spring-pong").connect(_catch_pong)

signal("spring-said").connect(_redispatch_said)
signal("spring-saidex").connect(_redispatch_saidex)
signal("spring-saidprivate").connect(_redispatch_saidprivate)
signal("spring-saidprivateex").connect(_redispatch_saidprivateex)

signal("spring-notice").connect(_redispatch_notice)
signal("spring-joined").connect(_redispatch_joined)
signal("spring-left").connect(_redispatch_left)
signal("spring-adduser").connect(_redispatch_adduser)
signal("spring-removeuser").connect(_redispatch_removeuser)
signal("spring-quit").connect(_redispatch_quit)
signal("spring-kick").connect(_redispatch_kick)
signal("spring-nick").connect(_redispatch_nick)
signal("spring-mode").connect(_parse_mode)
signal("spring-005").connect(_server_supports)
signal("spring-accepted").connect(_connection_registered)
signal("spring-denied").connect(_connection_denied)
signal("spring-agreementend").connect(_redispatch_agreement)

signal("spring-motd").connect(_parse_motd)
signal("spring-logininfoend").connect(_redispatch_logininfoend)
signal("spring-clients").connect(_redispatch_clients)

signal("spring-bridgedclientfrom").connect(_redispatch_bridged_client)
signal("spring-unbridgedclientfrom").connect(_redispatch_un_bridged_client)

signal("spring-joinedfrom").connect(_redispatch_joined_from)
signal("spring-leftfrom").connect(_redispatch_left_from)

signal("spring-saidfrom").connect(_redispatch_said_from)
signal("spring-clientsfrom").connect(_redispatch_clients_from)
