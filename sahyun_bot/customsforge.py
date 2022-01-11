import html
import pickle
import re
from datetime import date, datetime, timezone
from itertools import takewhile
from threading import RLock
from typing import Iterator, Optional, Callable, IO, Any, List

from requests import Response
from requests.cookies import RequestsCookieJar

from sahyun_bot.customsforge_settings import *
from sahyun_bot.utils import T, NON_EXISTENT, identity, debug_ex, clean_link
from sahyun_bot.utils_logging import get_logger
from sahyun_bot.utils_session import SessionFactory
from sahyun_bot.utils_settings import parse_bool, parse_list

LOG = get_logger(__name__)

LOGIN_PAGE = 'https://customsforge.com/index.php?/login/'
LOGIN_REDIRECT = 'https://customsforge.com/?&_fromLogin=1'

LOGIN_FORM_CSRF = 'csrfKey'
LOGIN_FORM_EMAIL = 'auth'
LOGIN_FORM_PASSWORD = 'password'

CDLC_PAGE = 'https://ignition4.customsforge.com/cdlc/{}'
CDLC_API = 'https://ignition4.customsforge.com/'
DOWNLOAD_API = 'https://customsforge.com/process.php?id={}'

EONS_AGO = date.fromisoformat('2010-01-01')  # this should pre-date even the oldest CDLC

AJAX_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

CDLC_API_PARAMS_BASE = {
    'draw': '1',
    'columns[0][data]': 'addBtn',
    'columns[0][searchable]': 'false',
    'columns[0][orderable]': 'false',
    'columns[1][data]': 'artistName',
    'columns[2][data]': 'titleName',
    'columns[3][data]': 'albumName',
    'columns[4][data]': 'year',
    'columns[5][data]': 'duration',
    'columns[5][orderable]': 'false',
    'columns[6][data]': 'tunings',
    'columns[6][searchable]': 'false',
    'columns[6][orderable]': 'false',
    'columns[7][data]': 'version',
    'columns[7][searchable]': 'false',
    'columns[7][orderable]': 'false',
    'columns[8][data]': 'author.name',
    'columns[9][data]': 'created_at',
    'columns[9][searchable]': 'false',
    'columns[10][data]': 'updated_at',
    'columns[10][searchable]': 'false',
    'columns[11][data]': 'downloads',
    'columns[11][searchable]': 'false',
    'columns[12][data]': 'parts',
    'columns[12][orderable]': 'false',
    'columns[13][data]': 'platforms',
    'columns[14][data]': 'file_pc_link',
    'columns[14][searchable]': 'false',
    'columns[15][data]': 'file_mac_link',
    'columns[15][searchable]': 'false',
    'columns[16][data]': 'artist.name',
    'columns[17][data]': 'title',
    'columns[18][data]': 'album',
    'order[0][column]': '10',
    'order[0][dir]': 'desc',
    'search[value]': '',
}


class CustomsforgeClient:
    """
    Implements customsforge API for CDLCs. (Should be) thread-safe.

    To access the API, logging in is required. This is attempted exactly once for every API call that returns
    a redirect indicating lack of (or invalid) credentials. Cookies resulting from login can be stored to avoid
    this process in subsequent executions.
    """
    def __init__(self,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 timeout: int = DEFAULT_TIMEOUT,
                 cookie_jar_file: Optional[str] = DEFAULT_COOKIE_FILE,
                 email: str = None,
                 password: str = None,
                 get_today: Callable[[], date] = date.today):
        self.__batch_size = batch_size if Verify.batch_size(batch_size) else DEFAULT_BATCH_SIZE
        self.__timeout = max(0, timeout) or DEFAULT_TIMEOUT
        self.__cookie_jar_file = cookie_jar_file

        self.__email = email
        self.__password = password
        self.__login_rejected = False
        self.__prevent_multiple_login_lock = RLock()

        self.__sessions = SessionFactory(unsafe=[LOGIN_FORM_PASSWORD])
        self.__cookies = RequestsCookieJar()
        self.__with_cookie_jar('rb', lambda f: self.__cookies.update(pickle.load(f)))
        # no error, since cookie file probably doesn't exist; we'll try to write it later and log any error then

        self.__get_today = get_today

    def login(self, email: str = None, password: str = None) -> bool:
        """
        Tries to log in using given credentials. They are stored for future use (e.g. automatic re-log).

        If no credentials are passed into the method, tries to use already stored credentials, if any.

        In some cases it is possible to determine that login failed due to invalid credentials. In such cases
        this method will avoid logging in until new credentials are passed into it.

        :returns true if login succeeded, false otherwise
        """
        with self.__prevent_multiple_login_lock:
            if not self.__has_credentials(email, password):
                return False

            with self.__sessions.with_retry() as session:
                csrf = self.__call('get csrf', session.get, LOGIN_PAGE, cookies=None, try_login=False)
                if not csrf:  # this indicates an error - repeated attempts may still succeed
                    return False

                match = re.search(r'<input[^>]+name="csrfKey" value="(\w+)">', csrf.text)
                if not match:
                    LOG.error('Login failed. Cannot retrieve CSRF key.')
                    self.__login_rejected = True
                    return False

                form = {
                    LOGIN_FORM_CSRF: match.group(1),
                    LOGIN_FORM_EMAIL: self.__email,
                    LOGIN_FORM_PASSWORD: self.__password,
                    'remember_me': '1',
                    '_processLogin': 'usernamepassword',
                }

                r = self.__call('login', session.post, LOGIN_PAGE, cookies=csrf.cookies, data=form, try_login=False)

            if not r:  # this indicates an error - repeated attempts may still succeed
                return False

            if not r.is_redirect or not r.headers.get('Location', '') == LOGIN_REDIRECT:
                LOG.error('Login failed. Please check your credentials.')
                self.__login_rejected = True
                return False

            self.__with_cookie_jar('wb', lambda f: pickle.dump(r.cookies, f), trying_to='update cookie jar')
            self.__cookies = r.cookies
            return True

    def ping(self) -> bool:
        """
        :returns true if a simple call to customsforge succeeded (including login), false otherwise
        """
        with self.__sessions.with_retry() as session:
            return self.__call('ping', session.get, CDLC_API) is not None

    def cdlcs(self, since: date = EONS_AGO) -> Iterator[dict]:
        import time
        epoch_millis = int(time.time() * 1000)

        params = dict(CDLC_API_PARAMS_BASE)
        params['_'] = epoch_millis

        with self.__sessions.with_retry() as session:
            lazy_cdlcs = self.__lazy_all(trying_to='find CDLCs',
                                         call=session.get,
                                         url=CDLC_API,
                                         params=params,
                                         headers=AJAX_HEADERS,
                                         convert=To.cdlcs)

        since_timestamp = int(datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        return reversed(list(takewhile(lambda c: c['snapshot_timestamp'] >= since_timestamp, lazy_cdlcs)))

    def __has_credentials(self, email: str, password: str) -> bool:
        if email and password:
            self.__email = email
            self.__password = password
            self.__login_rejected = False

        if self.__login_rejected:
            LOG.debug('Login rejected. Please provide new credentials to try again.')
            return False

        if not self.__email and not self.__password:
            LOG.error('No credentials have been provided.')
            self.__login_rejected = True
            return False

        return True

    def __call(self,
               trying_to: str,
               call: Callable[..., Response],
               url: str,
               try_login: bool = True,
               **kwargs) -> Optional[Response]:
        kwargs.setdefault('cookies', self.__cookies)

        try:
            r = call(url=url, timeout=self.__timeout, allow_redirects=False, **kwargs)
        except Exception as e:
            return debug_ex(e, trying_to, LOG)

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            LOG.debug('Cannot %s: automatic login to customsforge failed.', trying_to)
            return None

        kwargs.pop('cookies', None)
        return self.__call(trying_to, call, url, try_login=False, **kwargs)

    def __lazy_all(self,
                   convert: Callable[[Any], Iterator[T]],
                   skip: int = 0,
                   batch: int = None,
                   **call_params) -> Iterator[T]:
        batch = batch if Verify.batch_size(batch) else self.__batch_size

        while True:
            params = call_params.setdefault('params', {})
            params['start'] = skip
            params['length'] = batch

            r = self.__call(**call_params)
            if not r or not r.text:
                break

            try:
                it = convert(r.json())
                first = next(it, NON_EXISTENT)
                if first is NON_EXISTENT:
                    break

                yield first
                yield from it
            except Exception as e:
                trying_to = call_params['trying_to']
                return debug_ex(e, f'parse response of <{trying_to}> as JSON', LOG)

            skip += batch

    def __with_cookie_jar(self,
                          options: str,
                          on_file: Callable[[IO], T] = identity,
                          trying_to: str = None) -> T:
        if self.__cookie_jar_file:
            try:
                f = open(self.__cookie_jar_file, options)
            except Exception as e:
                if trying_to:
                    debug_ex(e, trying_to, LOG)
            else:
                with f:
                    return on_file(f)


class Verify:
    @staticmethod
    def batch_size(batch_size: int) -> bool:
        return batch_size and 0 < batch_size <= DEFAULT_BATCH_SIZE


class To:
    @staticmethod
    def cdlcs(cdlcs) -> Iterator[dict]:
        if not cdlcs:
            return

        for c in cdlcs['data']:
            yield To.cdlc(c)

    @staticmethod
    def cdlc(c: dict) -> dict:
        cdlc_id = c['id']
        return {
            'id': cdlc_id,
            'artist': read(c['artist'], 'name'),
            'title': read(c, 'title'),
            'album': read(c, 'album'),
            'tuning': read_tuning(c),
            'instrument_info': read_instruments(c),
            'parts': read_parts(c),
            'platforms': read_platforms(c),
            'has_dynamic_difficulty': read_dynamic_difficulty(c),
            'is_official': read_bool(c, 'is_official'),

            'author': read(c['author'], 'name'),
            'version': read(c, 'version'),

            'direct_download': read(c, 'file_pc_link'),
            'download': DOWNLOAD_API.format(cdlc_id),  # no longer works, can be deleted
            'info': CDLC_PAGE.format(cdlc_id),
            'video': read_link(c, 'music_video_url'),
            'art': read_link(c, 'album_art_url'),

            'snapshot_timestamp': read_last_update(c),
        }


def read_tuning(cdlc: dict):
    for tuning in ['lead', 'rhythm', 'bass', 'alt_lead', 'alt_rhythm', 'alt_bass']:
        value = read(cdlc, tuning)
        if value and not value.isspace() and not value == '0':
            return value

    return None


def read_instruments(cdlc: dict):
    instruments = []
    read_from_bool(cdlc, 'require_capo_lead', 'ii_capolead', instruments)
    read_from_bool(cdlc, 'require_capo_rhythm', 'ii_caporhythm', instruments)
    read_from_bool(cdlc, 'require_slide_lead', 'ii_slidelead', instruments)
    read_from_bool(cdlc, 'require_slide_rhythm', 'ii_sliderhythm', instruments)
    read_from_bool(cdlc, 'require_five_bass', 'ii_5stringbass', instruments)
    read_from_bool(cdlc, 'require_six_bass', 'ii_6stringbass', instruments)
    read_from_bool(cdlc, 'require_seven_guitar', 'ii_7stringguitar', instruments)
    read_from_bool(cdlc, 'require_twelve_guitar', 'ii_12stringguitar', instruments)
    read_from_bool(cdlc, 'require_heavy_gauge', 'ii_heavystrings', instruments)
    read_from_bool(cdlc, 'require_whammy_bar', 'ii_tremolo', instruments)
    return instruments


def read_parts(cdlc: dict):
    parts = []
    for tuning in ['lead', 'rhythm', 'bass', 'alt_lead', 'alt_rhythm', 'alt_bass']:
        value = read(cdlc, tuning)
        if value and not value.isspace() and not value == '0':
            parts.append(tuning.rpartition('alt_')[2])

    read_from_bool(cdlc, 'has_lyrics', 'vocals', parts)

    return parts


def read_platforms(cdlc: dict):
    platforms = []
    for platform in ['pc', 'mac']:  # no mapping for xbox360 and ps3
        value = read_link(cdlc, f'file_{platform}_link')
        if value and not value.isspace():
            platforms.append(platform)

    return platforms


def read_dynamic_difficulty(cdlc: dict):
    return False  # could not find mapping


def read_last_update(cdlc: dict):
    value = read(cdlc, 'updated_at')
    update = datetime.strptime(value, '%m/%d/%Y')
    return int(update.replace(tzinfo=timezone.utc).timestamp())


def read_from_bool(data: dict, key: str, value: str, l: List[str]):
    if read_bool(data, key):
        l.append(value)


def read(data: dict, key: str) -> str:
    value = '' if data[key] is None else str(data[key])
    return html.unescape(value.strip())


def read_all(data: dict, key: str) -> List[str]:
    return parse_list(read(data, key))


def read_bool(data: dict, key: str) -> bool:
    return parse_bool(read(data, key))


def read_link(data: dict, key: str) -> str:
    return clean_link(read(data, key))
