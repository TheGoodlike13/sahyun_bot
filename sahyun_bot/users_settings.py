from enum import IntEnum


class UserRank(IntEnum):
    """
    Ranks given to users. The numbers represent comparable values for the ranks. Greater ranks implies more rights.

    Never assign 0 to a rank, because this will cause Python to treat this rank as False, which may result in that
    rank being broken. These numbers are not used internally outside comparison, so they can be freely adjusted in
    any other way.
    """
    BAN = 1
    VWR = 2
    FLWR = 3
    UNKNW = 4
    SUB = 5
    VIP = 6
    MOD = 7
    ADMIN = 8


class User:
    def __init__(self, nick: str, rank: UserRank = UserRank.UNKNW, user_id: str = None):
        self.nick = nick
        self.rank = rank
        self.user_id = user_id

    def __str__(self):
        return f'{self.rank.name} {self.nick}'

    def has_right(self, rank: UserRank) -> bool:
        """
        :returns true if user has rights of the rank, false otherwise; ranks have rights of all ranks below them
        """
        return self.rank >= rank

    @property
    def is_limited(self) -> bool:
        """
        :returns true if user cannot perform unlimited commands under any circumstances, false if they can
        """
        return not self.has_right(UserRank.VIP)

    @property
    def id(self) -> str:
        """
        :returns identifier of the user, preferring id over nick
        """
        return self.user_id if self.user_id else self.nick
