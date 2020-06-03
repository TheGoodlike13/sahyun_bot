from threading import RLock
from typing import Callable, Optional, List, Union

from requests import HTTPError
from twitch import Helix
from twitch.helix import Follows, User

from sahyun_bot.utils import Closeable, debug_ex, NonelessCache, T
from sahyun_bot.utils_logging import get_logger
from sahyun_bot.utils_session import SessionFactory

LOG = get_logger(__name__)

TWITCH_OAUTH2_API = 'https://id.twitch.tv/oauth2/token?grant_type=client_credentials'
TWITCH_REVOKE_API = 'https://id.twitch.tv/oauth2/revoke'

TWITCH_HOSTS_API = 'https://tmi.twitch.tv/hosts?include_logins=1'


class Twitchy(Closeable):
    def __init__(self, client_id: str, client_secret: str):
        self.__client_id = client_id
        self.__client_secret = client_secret

        self.__sessions = SessionFactory(unsafe=['client_secret'])

        self.__bearer_token = None
        self.__api = None
        self.__prevent_multiple_tokens = RLock()

        self.__user_cache = NonelessCache(maxsize=2 ** 10, ttl=60 * 60)
        self.__user_id_lock = RLock()

    @property
    def api(self) -> Helix:
        """
        This getter is intended to be used internally or with REPL access, thus it does not handle exceptions.

        :returns internal twitch API object
        """
        with self.__prevent_multiple_tokens:
            return self.__api if self.__api else self.__acquire_authorized_api()

    def close(self):
        """
        Revokes token if it was acquired. Intended to be invoked when shutting down the application.
        """
        try:
            self.__revoke_token()
        except Exception as e:
            debug_ex(e, 'revoke token', LOG, silent=True)

    def get_id(self, nick_or_id: Union[str, int]) -> Optional[int]:
        """
        Coerces given nick or twitch id into twitch id, if possible
        """
        try:
            with self.__user_id_lock:
                user = self.__user_cache.get(nick_or_id)
                if not user:
                    user = self.__call(self.__get_user, nick_or_id)
                    self.__user_cache.update({int(user.id): user, user.login: user})

                return int(user.id)
        except Exception as e:
            return debug_ex(e, f'find twitch user id for <{nick_or_id}>', LOG)

    def is_following(self, streamer: Union[str, int], viewer: Union[str, int]) -> bool:
        """
        :param streamer: nick or id of a streamer
        :param viewer: nick or id of a viewer
        :returns true if viewer is following the streamer, false otherwise
        :raises Exception: if call to twitch fails
        """
        s_id = self.get_id(streamer)
        v_id = self.get_id(viewer)
        return s_id and v_id and self.__call(self.__is_following, s_id, v_id)

    def hosts(self, streamer: str) -> List[str]:
        """
        :param streamer: nick or id of a streamer
        :returns list of nicks who are hosting the streamer if possible to determine
        :raises Exception: if call to twitch fails
        """
        s_id = self.get_id(streamer)
        return self.__get_hosts(s_id)

    def __acquire_authorized_api(self) -> Helix:
        self.__bearer_token = self.__acquire_token()
        self.__api = Helix(client_id=self.__client_id,
                           client_secret=self.__client_secret,
                           bearer_token=f'bearer {self.__bearer_token}')
        return self.__api

    def __acquire_token(self) -> str:
        params = {
            'client_id': self.__client_id,
            'client_secret': self.__client_secret,
        }

        with self.__sessions.with_retry() as session:
            result = session.post(TWITCH_OAUTH2_API, params=params)

        return result.json().get('access_token')

    def __revoke_token(self):
        with self.__prevent_multiple_tokens:
            if self.__bearer_token:
                params = {
                    'client_id': self.__client_id,
                    'token': self.__bearer_token,
                }

                with self.__sessions.with_retry() as session:
                    session.post(TWITCH_REVOKE_API, params=params)

    def __call(self, api_call: Callable[..., T], *args, retry_auth: bool = True) -> T:
        api = self.api
        try:
            return api_call(api, *args)
        except HTTPError as e:
            if not retry_auth or not e.response or not e.response.status_code == 401:
                raise

            with self.__prevent_multiple_tokens:
                if self.__api is api:  # ensures that API is not cleared after it is re-built in another thread
                    self.__bearer_token = None
                    self.__api = None

            return self.__call(api_call, *args, retry_auth=False)

    def __get_user(self, api: Helix, nick_or_id: Union[str, int]) -> Optional[User]:
        return api.user(nick_or_id)

    def __is_following(self, api: Helix, streamer: int, viewer: int) -> bool:
        return Follows(api=api.api, follow_type='followers', to_id=streamer, from_id=viewer).total > 0

    def __get_hosts(self, streamer: int) -> List[str]:
        params = {
            'target': streamer,
        }

        with self.__sessions.with_retry() as session:
            result = session.get(TWITCH_HOSTS_API, params=params)

        return [host.get('host_login') for host in result.json().get('hosts')]
