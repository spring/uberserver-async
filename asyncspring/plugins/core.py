import asyncio
import time
import logging

from asyncblink import signal
from asyncspring.user import get_user
from asyncspring.parser import LobbyMessage

log = logging.getLogger(__name__)

ping_client = None
ping_timer = None


def _redispatch_message_common(message, mtype):
    user = message.source
    target, text = message.params[0], " ".join(message.params[2:])
    # log.debug("{} {}".format(mtype, text))

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
    user = get_user(message.params[1])
    channel = message.params[0]
    signal("joined").send(message, user=user, channel=channel)


def _redispatch_joinfailed(message):
    log.debug("JOINFAILED")
    log.debug(message)


def _redispatch_left(message):
    user = get_user(message.params[1])
    channel = message.params[0]
    signal("left").send(message, user=user, channel=channel)


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


def _ping_server():
    global ping_timer
    if ping_client.last_pong != 0 and time.time() - ping_client.last_pong > 90:
        ping_client.connection_lost(Exception())

    else:
        ping_client.writeln("PING")
        ping_client.last_ping = time.time()

        ping_timer = asyncio.get_event_loop().call_later(29, _ping_server)


def _stop_ping(message):
    if ping_timer:
        ping_timer.cancel()


def _catch_pong(message):
    message.client.last_pong = time.time()
    message.client.lag = message.client.last_pong - message.client.last_ping
    signal("pong").send(message)


def _redispatch_spring(message):
    signal("spring-{}".format(message.verb.lower())).send(message)


def _redispatch_raw(client, text):
    log.debug(f"RAW : {client} {text}")
    message = LobbyMessage.from_message(text)
    message.client = client
    # log.debug(message)
    signal("spring").send(message)


def _register_client(client):
    log.info("Sending registration info")
    asyncio.get_event_loop().call_later(1, client._register)


def _login_client(client):
    log.info("Server login")
    asyncio.get_event_loop().call_later(1, client._login)


def _queue_ping(client):
    global ping_client

    ping_client = client
    _ping_server()


def _connection_registered(message):
    log.debug("Connection registered!")
    signal("accepted").send(message)

    message.client.registration_complete = True
    _queue_ping(message.client)
    for channel in message.client.channels_to_join:
        # log.debug(channel)
        message.client.join(channel)


def _connection_denied(message):
    message.client.registration_complete = False
    signal("denied").send(message)


def _parse_motd(message):
    log.info(message)


def _redispatch_tasserver(message):
    signal("tasserver").send(message)


def _redispatch_clients(message):
    signal("clients").send(message)


def _redispatch_adduser(message):
    signal("adduser").send(message)


def _redispatch_removeuser(message):
    signal("removeuser").send(message)


def _redispatch_agreement(message):
    signal("agreement").send(message)


def _redispatch_agreementend(message):
    signal("agreement_end").send(message)


def _redispatch_joined_from(message):
    log.debug("JOINED FROM")
    log.debug(message)


def _redispatch_left_from(message):
    log.debug("LEFT FROM")
    log.debug(message)


def _redispatch_said_from(message):
    log.debug("SAID FROM")
    log.debug(message)


def _redispatch_failed(message):
    log.debug(f"FAILED MESSAGE: {message}")
    signal("failed").send(message)


signal("raw").connect(_redispatch_raw)
signal("spring").connect(_redispatch_spring)

signal("connected").connect(_login_client)
signal("connection-lost").connect(_stop_ping)

signal("spring-tasserver").connect(_redispatch_tasserver)

signal("spring-pong").connect(_catch_pong)

signal("spring-said").connect(_redispatch_said)
signal("spring-saidex").connect(_redispatch_saidex)
signal("spring-saidprivate").connect(_redispatch_saidprivate)
signal("spring-saidprivateex").connect(_redispatch_saidprivateex)

signal("spring-notice").connect(_redispatch_notice)
signal("spring-joined").connect(_redispatch_joined)
signal("spring-joinfailed").connect(_redispatch_joinfailed)

signal("spring-left").connect(_redispatch_left)
signal("spring-adduser").connect(_redispatch_adduser)
signal("spring-removeuser").connect(_redispatch_removeuser)
signal("spring-quit").connect(_redispatch_quit)
signal("spring-kick").connect(_redispatch_kick)
signal("spring-nick").connect(_redispatch_nick)
signal("spring-accepted").connect(_connection_registered)
signal("spring-denied").connect(_connection_denied)
signal("spring-agreement").connect(_redispatch_agreement)
signal("spring-agreementend").connect(_redispatch_agreementend)

signal("spring-motd").connect(_parse_motd)
signal("spring-clients").connect(_redispatch_clients)

signal("spring-joinedfrom").connect(_redispatch_joined_from)
signal("spring-leftfrom").connect(_redispatch_left_from)

signal("spring-failed").connect(_redispatch_failed)
