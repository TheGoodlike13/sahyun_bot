from enum import IntEnum


class UserRank(IntEnum):
    BAN = 0
    VWR = 1
    FLWR = 2
    UNKNW = 3
    SUB = 4
    VIP = 5
    MOD = 6
    ADMIN = 7


class User:
    def __init__(self, nick: str, rank: UserRank = UserRank.UNKNW, user_id: str = None):
        self.nick = nick
        self.rank = rank
        self.user_id = user_id

    def __str__(self):
        return f'{self.rank} {self.nick}'

    def has_right(self, rank: UserRank) -> bool:
        return self.rank >= rank

    @property
    def id(self) -> str:
        return self.user_id if self.user_id else self.nick
