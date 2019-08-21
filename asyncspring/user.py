
class User:
    """
    Represents a user on SpringRTS Lobby, with their nickname, username, and hostname.
    """

    def __init__(self, username, password, email):
        self.username = username
        self.password = password
        self.email = email
        # self.hostmask = "{}!{}@{}".format(nick, user, host)
        self._register_wait = 0

    @classmethod
    def from_hostmask(self, hostmask):
        if "!" in hostmask and "@" in hostmask:
            nick, userhost = hostmask.split("!", maxsplit=1)
            user, host = userhost.split("@", maxsplit=1)
            return self(nick, user, host)
        return self(None, None, hostmask)


def get_user(hostmask):
    if "!" not in hostmask or "@" not in hostmask:
        return User(hostmask, hostmask, hostmask)
    return User.from_hostmask(hostmask)

