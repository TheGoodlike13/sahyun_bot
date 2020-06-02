"""
Commands which control the request queue.
"""

from __future__ import annotations

from typing import List, Iterator, Optional, Tuple, FrozenSet

from sahyun_bot.commander_settings import Command, ResponseHook, DEFAULT_MAX_SEARCH, DEFAULT_MAX_PICK
from sahyun_bot.elastic import CustomDLC
from sahyun_bot.users_settings import User, UserRank
from sahyun_bot.utils_queue import MemoryQueue


def pick_format(request: Match) -> str:
    """
    :returns string enumerating the choices from a request
    """
    return '; '.join(f'!{pos} {match.short}' for pos, match in request.all())


class Match:
    def __init__(self, user: User, query: str, *matches: CustomDLC, original: Match = None):
        self.user = user
        self.query = query
        self.matches: List[CustomDLC] = matches
        self.original = original or self

    def __len__(self):
        return len(self.matches)

    def __str__(self) -> str:
        return str(self.exact or self.query)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Match):
            raise NotImplemented

        return self.ids() == o.ids()

    @property
    def is_exact(self) -> bool:
        return len(self) == 1

    @property
    def exact(self) -> Optional[CustomDLC]:
        return self.matches[0] if self.is_exact else None

    def all(self) -> Iterator[Tuple[int, CustomDLC]]:
        pos = 0
        for match in self.matches:
            pos += 1
            yield pos, match

    def pick(self, choice: int) -> Optional[Match]:
        if self.original != self:
            return self.original.pick(choice)

        index = choice - 1
        return None if choice > len(self) else Match(self.user, self.query, self.matches[index], original=self)

    def by_same_user(self, other: Match) -> bool:
        return self.is_from(other.user)

    def is_from(self, user: User) -> bool:
        return self.user.nick == user.nick

    def needs_picking(self, user: User) -> bool:
        return not self.is_exact and self.is_from(user)

    def has_pick_for(self, user: User) -> bool:
        return self.original.needs_picking(user)

    def has_pick(self) -> bool:
        return self.original != self and not self.original.is_exact

    def ids(self) -> FrozenSet[int]:
        return frozenset([match.id for match in self.matches])


class Picker:
    def __init__(self, user: User):
        self.user = user
        self.pick_needs = True

    def needs_picking(self, match: Match) -> bool:
        self.pick_needs = True
        return match.needs_picking(self.user)

    def has_pick_for(self, match: Match) -> bool:
        self.pick_needs = False
        return match.has_pick_for(self.user)

    def last_pick(self, match: Match) -> bool:
        return match.needs_picking(self.user) if self.pick_needs else match.has_pick_for(self.user)


class Request(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')
        self.__max_search = beans.get('max_search', DEFAULT_MAX_SEARCH)
        self.__max_pick = beans.get('max_pick', DEFAULT_MAX_PICK)

    def alias(self) -> Iterator[str]:
        yield from super().alias()
        yield from ['song', 'sr']

    def min_rank(self) -> UserRank:
        return UserRank.FLWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        matches = list(CustomDLC.search(query=args)[:self.__max_search])
        if not matches:
            return respond.to_sender(f'No matches for <{args}>')

        playable = list(filter(lambda match: match.is_playable, matches))
        if not playable:
            unplayable = '; '.join(match.short for match in matches)
            return respond.to_sender(f'Matches for <{args}> not playable: {unplayable}')

        request = Match(user, args, *playable[:self.__max_pick])
        position = self.__queue.add(request) if user.is_admin else self.__queue.offer(request, request.by_same_user)
        if not position:
            return respond.to_sender(f'Already played <{request}>')

        if position < 0:
            return respond.to_sender(f'Request <{request}> already in queue position {-position}')

        respond.to_sender(f'Your request for <{request}> is now in position {position}')
        if request.is_exact:
            if request.exact.is_official:
                return respond.to_sender('WARNING! This song is official, so it may not be playable. Ask or try again!')
        else:
            respond.to_sender(f'To pick exact: {pick_format(request)}')


class Pick(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')
        self.__max_pick = beans.get('max_pick', DEFAULT_MAX_PICK)
        self.__choices = list(map(str, range(1, self.__max_pick + 1)))

    def alias(self) -> Iterator[str]:
        yield from super().alias()
        yield from self.__choices

    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        choice = self.__choice(alias, args)
        if not choice:
            return respond.to_sender(f'Try !pick 1-{self.__max_pick}')

        picker = Picker(user)
        with self.__queue:
            request = self.__queue.find(picker.needs_picking)
            if not request:
                if user.is_admin:
                    return self.__pick_last(choice, respond)

                request = self.__queue.find(picker.has_pick_for)
                if not request:
                    return True

            chosen = request.pick(choice)
            if not chosen:
                return respond.to_sender(f'{choice} is not available; max: {len(request)}')

            position = self.__queue.offer(chosen, picker.last_pick)
            respond.to_sender(f'Your request for <{chosen}> is now in position {position}')

    def __pick_last(self, choice: int, respond: ResponseHook) -> bool:
        request = self.__queue.last()
        if not request:
            return respond.to_sender('Nothing to pick')

        chosen = request.pick(choice)
        if not chosen:
            return respond.to_sender(f'{choice} is not available; max: {len(request)}')

        self.__queue.mandela(chosen)
        respond.to_sender(f'Next: <{chosen}>')

    def __choice(self, alias: str, args: str) -> int:
        if alias in self.__choices:
            return int(alias)

        index, space, ignored = args.partition(' ')
        return int(index) if index in self.__choices else 0


class Next(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        request = self.__queue.next()
        if not request:
            return respond.to_sender('Request queue is empty')

        if request.is_exact:
            respond.to_sender(f'Next: <{request}> by {request.user}')
        else:
            respond.to_sender(f'Pick for <{request}> by {request.user}: {pick_format(request)}')
