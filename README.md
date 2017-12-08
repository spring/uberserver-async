# asyncspring 

**Asyncspring** is an asyncio-based SpringRTS framework for Python.

## Installation

```
pip install pip install "git+https://github.com/TurBoss/asyncspring.git"
```

And you're done!

You can also use `setup.py` to manually install from a git version.

## Connecting

```python
from asyncspring import spring

bot = spring.connect("lobby.springrts.com", 8200, use_ssl=False)
bot.register("username", password="pass")
```

## Subscribing to events

```python
@bot.on("message")
def incoming_message(parsed, user, target, text):
    # parsed is an RFC1459Message object
    # user is a User object with nick, user, and host attributes
    # target is a string representing nick/channel the message was sent to
    # text is the text of the message
    bot.say(target, "{}: you said {}".format(user.nick, text))
```

## Using plugins

```python
import asyncspring.plugins.tracking # channel/user state tracking
import asyncspring.plugins.addressed # events that fire when the bot is addressed
import asyncspring.plugins.nickserv # events that fire on nickserv authentication responses
```

## Writing code without a reference to the LobbyProtocol object

Asyncspring uses the excellent [Blinker](https://pythonhosted.org/blinker/) library.
That means that you can just run `from blinker import signal` and hook into
asyncspring's events without needing a reference to the LobbyPRotocol object. This is
especially useful in writing plugins; take a look at plugin code for examples.
