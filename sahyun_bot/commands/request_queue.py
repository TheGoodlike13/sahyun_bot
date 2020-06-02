"""
Commands which control the request queue.
"""

from __future__ import annotations

from abc import ABC
from typing import List, Iterator, Optional, Tuple, FrozenSet, Iterable, Union

from sahyun_bot.commander_settings import Command, ResponseHook, DEFAULT_MAX_SEARCH, DEFAULT_MAX_PICK, DEFAULT_MAX_PRINT
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
    def short(self) -> str:
        return self.exact.short if self.is_exact else self.query

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

    def is_from(self, user: Union[User, str]) -> bool:
        nick = user if isinstance(user, str) else user.nick
        return self.user.nick == nick

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


class BaseRequest(Command, ABC):
    def __init__(self, **beans):
        super().__init__(**beans)
        self._queue: MemoryQueue[Match] = beans.get('rq')

    def min_rank(self) -> UserRank:
        return UserRank.FLWR

    def _enqueue_request(self, user: User, request: Match, respond: ResponseHook) -> bool:
        position = self._queue.add(request) if user.is_admin else self._queue.offer(request, request.by_same_user)
        return self._validate_position(position, request, respond)

    def _validate_position(self, position: int, request: Match, respond: ResponseHook) -> bool:
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


class Request(BaseRequest):
    def __init__(self, **beans):
        super().__init__(**beans)

        self.__max_search = beans.get('max_search', DEFAULT_MAX_SEARCH)
        self.__max_pick = beans.get('max_pick', DEFAULT_MAX_PICK)

    def alias(self) -> Iterator[str]:
        yield from super().alias()
        yield from ['song', 'sr']

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        Adds any matching songs to the request queue. Query is taken as a literal search string. Can be empty.

        If multiple matches are found, you will be able to use !pick to choose the most relevant ones.

        The following rules do NOT apply to ADMIN rank:
        * If you already had a song in the queue, replaces it instead.
        * If the song is already in the queue, does not add it.
        * If the song has been played already, does not add it.
        """
        matches = list(CustomDLC.search(query=args)[:self.__max_search])
        if not matches:
            return respond.to_sender(f'No matches for <{args}>')

        playable = list(filter(lambda match: match.is_playable, matches))
        if not playable:
            unplayable = '; '.join(match.short for match in matches)
            return respond.to_sender(f'Matches for <{args}> not playable: {unplayable}')

        request = Match(user, args, *playable[:self.__max_pick])
        return self._enqueue_request(user, request, respond)


class Random(BaseRequest):
    def __init__(self, **beans):
        super().__init__(**beans)

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        Same as !request, but automatically picks from ALL possible matches. This includes matches that cannot
        be picked with !pick due to lower relevance. Usually best used with artists, e.g. !random acdc
        """
        with self._queue:
            match = CustomDLC.random(args, *self.__exclusions())
            if not match:
                without_exclusions = CustomDLC.random_pool(query=args).count()
                message = f'Everything already played or enqueued' if without_exclusions else f'No matches'
                return respond.to_sender(f'{message} for <{args}>')

            request = Match(user, args, match)
            return self._enqueue_request(user, request, respond)

    def __exclusions(self) -> List[int]:
        all_ids = list(self.__ids(self._queue))
        all_ids.extend(self.__ids(self._queue.memory()))
        return all_ids

    def __ids(self, matches: Iterable[Match]) -> Iterator[int]:
        for match in matches:
            if match.is_exact:
                yield match.exact.id


class Pick(BaseRequest):
    def __init__(self, **beans):
        super().__init__(**beans)

        self.__max_pick = beans.get('max_pick', DEFAULT_MAX_PICK)
        self.__choices = list(map(str, range(1, self.__max_pick + 1)))

    def alias(self) -> Iterator[str]:
        yield from super().alias()
        yield from self.__choices

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        If a previous !request returned more than one match, this command allows to pick an exact match.

        Picking an exact match is subject to the same rules as request.

        Position can be used as a shorthand, e.g. instead of "!pick 1", you can just use "!1".

        You can change your pick as long as it is still in the queue, unless you are ADMIN.
        Instead, ADMIN can !pick for the last !next result, even if it's not theirs.
        Pick for !next can be changed with a follow-up !pick.
        """
        choice = self.__choice(alias, args)
        if not choice:
            return respond.to_sender(f'Try !pick 1-{self.__max_pick}')

        picker = Picker(user)
        with self._queue:
            request = self._queue.find(picker.needs_picking)
            if not request:
                if user.is_admin:
                    return self.__pick_last(choice, respond)

                request = self._queue.find(picker.has_pick_for)
                if not request:
                    return True

            chosen = request.pick(choice)
            if not chosen:
                return respond.to_sender(f'{choice} is not available; max: {len(request)}')

            position = self._queue.offer(chosen, picker.last_pick)
            return self._validate_position(position, chosen, respond)

    def __pick_last(self, choice: int, respond: ResponseHook) -> bool:
        request = self._queue.last()
        if not request:
            return respond.to_sender('Nothing to pick')

        chosen = request.pick(choice)
        if not chosen:
            return respond.to_sender(f'{choice} is not available; max: {len(request)}')

        self._queue.mandela(chosen)
        respond.to_sender(f'Next: <{chosen}>')

    def __choice(self, alias: str, args: str) -> int:
        if alias in self.__choices:
            return int(alias)

        index, space, ignored = args.partition(' ')
        return int(index) if index in self.__choices else 0


class Played(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        """
        Prints all the requests in the request queue memory.
        """
        requests = ', '.join(match.short for match in self.__queue.memory()) or 'none'
        respond.to_sender(f'Requests played: {requests}')


class Next(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        Pop the next song in request queue. After calling this, it is considered played.

        If the request was not exact, ADMIN rank can then call !pick to make it exact.

        Only the picked value will be considered played in that case.
        """
        request = self.__queue.next()
        if not request:
            return respond.to_sender('Request queue is empty')

        if request.is_exact:
            respond.to_sender(f'Next: <{request}> by {request.user}')
        else:
            respond.to_sender(f'Pick for <{request}> by {request.user}: {pick_format(request)}')


class Top(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        Move the latest request by user with given nick to the top of the queue.
        """
        nick, space, ignore = args.partition(' ')
        request = self.__queue.bump(lambda m: m.is_from(nick))
        if not request:
            return respond.to_sender(f'No requests by <{nick}> in queue')

        respond.to_sender(f'Request <{request}> by {request.user} is now in position 1')


class Last(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        Prints the last song that was popped from the queue.
        """
        last = self.__queue.last()
        if not last:
            return respond.to_sender('No requests have been played yet')

        respond.to_sender(f'Last: <{last}> by {last.user}')


class Playlist(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__queue: MemoryQueue[Match] = beans.get('rq')
        self.__max_print = beans.get('max_print', DEFAULT_MAX_PRINT)

    def alias(self) -> Iterator[str]:
        yield from super().alias()
        yield 'list'

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        """
        Prints the request queue. If the queue is big, may choose to print only some top elements.
        """
        copy = self.__queue[:]
        total = len(copy)
        visible = min(self.__max_print, total)
        requests = ', '.join(match.short for match in copy[:visible]) or 'empty'
        respond.to_sender(f'Playlist ({visible}/{total}): {requests}')
