from __future__ import annotations

from random import random
from typing import Optional, Union, List

from elasticsearch_dsl import Text, Keyword, Boolean, Long, token_filter, analyzer, Index, Search
from elasticsearch_dsl.aggs import Max, Min
from elasticsearch_dsl.analysis import Analyzer, TokenFilter
from elasticsearch_dsl.query import Match, Query, Terms, FunctionScore

from sahyun_bot import elastic_settings
from sahyun_bot.elastic_settings import BaseDoc, EpochSecond
from sahyun_bot.users_settings import UserRank
from sahyun_bot.utils_logging import get_logger

elastic_settings.ready_or_die()

LOG = get_logger(__name__)

NOT_LETTER_DIGIT_OR_WHITESPACE = r'[^\p{L}\d\s]'

remove_empty = token_filter('remove_empty', type='length', min=1)
keep_letters_and_digits_only = token_filter(
    'keep_letters_digits_only',
    type='pattern_replace',
    pattern=NOT_LETTER_DIGIT_OR_WHITESPACE,
    replacement='',
)
the_worderer = token_filter(
    'the_worderer',
    type='shingle',
    min_shingle_size=2,
    max_shingle_size=elastic_settings.e_shingle,
    token_separator='_',
    output_unigrams=True,
)


def with_common_filters(*filters: Union[TokenFilter, str]) -> List[TokenFilter]:
    all_filters = ['lowercase']
    all_filters.extend(filters)
    all_filters.extend([
        keep_letters_and_digits_only,
        'kstem',
        'remove_duplicates',
        remove_empty,
    ])
    return all_filters


def shingle_only(n: int) -> TokenFilter:
    return token_filter(
        f'shingle_{n}_only',
        type='shingle',
        min_shingle_size=n,
        max_shingle_size=n,
        token_separator='_',
        output_unigrams=False,
    )


def shingle_merge(n: int) -> Analyzer:
    return analyzer(f'shingle_merge_{n}', tokenizer='standard', filter=with_common_filters(shingle_only(n)))


grammar_comrade = analyzer('grammar_comrade', tokenizer='whitespace', filter=with_common_filters())
shingle_city = analyzer('shingle_city', tokenizer='standard', filter=with_common_filters(the_worderer))
shingle_mergers = [shingle_merge(n) for n in range(2, elastic_settings.e_shingle)]

cdlcs = Index(elastic_settings.e_cf_index)
cdlcs.settings(number_of_shards=1, number_of_replicas=0)
[cdlcs.analyzer(merger) for merger in shingle_mergers]


# noinspection PyTypeChecker
@cdlcs.document
class CustomDLC(BaseDoc):
    id = Long(required=True)
    artist = Keyword(required=True, copy_to=['full_title_grammar_comrade', 'full_title_shingle_city'])
    title = Keyword(required=True, copy_to=['full_title_grammar_comrade', 'full_title_shingle_city'])
    album = Keyword(required=True)
    tuning = Keyword(multi=True, required=True)
    instrument_info = Keyword(multi=True)
    parts = Keyword(multi=True, required=True)
    platforms = Keyword(multi=True, required=True)
    is_official = Boolean(required=True)

    author = Keyword(required=True)
    version = Keyword(required=True)

    direct_download = Keyword()
    info = Keyword(required=True)
    video = Keyword()
    art = Keyword()

    snapshot_timestamp = Long(required=True, fields={'as_date': EpochSecond()})

    from_auto_index = Boolean()

    # combined artist & title fields for analysis & search - see #fuzzy_match for explanation
    full_title_grammar_comrade = Text(analyzer=grammar_comrade, term_vector='yes')
    full_title_shingle_city = Text(analyzer=shingle_city, term_vector='yes')

    # legacy fields (no longer mapped or replaced)
    has_dynamic_difficulty = Boolean()

    @classmethod
    def search(cls, query: str = None, **kwargs) -> Search:
        """
        Provides search API for CustomDLC objects.

        Filters CDLCs by given query.
        """
        s = super().search(**kwargs)
        if query and not query.isspace():
            s = s.query(search_query(query))

        return s

    @classmethod
    def playable(cls, query: str = None, **kwargs) -> Search:
        """
        Provides search API for CustomDLC objects.

        Filters CDLCs by given query. Also filters out not playable CDLCs.
        """
        return cls.search(query, **kwargs).query(playable_query())

    @classmethod
    def random_pool(cls, query: str = None, *exclude: int, **kwargs) -> Search:
        """
        Provides search API for CustomDLC objects.

        Filters CDLCs by given query. Also filters out not playable CDLCs. Excludes official CDLCs if configured so.

        Finally, excludes arbitrary ids.
        """
        playable = cls.playable(query, **kwargs).exclude('terms', id=exclude)
        return playable if elastic_settings.e_allow_official else playable.query('term', is_official=False)

    @classmethod
    def random(cls, query: str = None, *exclude: int, **kwargs) -> Optional[CustomDLC]:
        """
        Returns random CustomDLC from #random_pool, if any match exists.
        """
        total = cls.random_pool(query, *exclude, **kwargs).count()
        if not total:
            return None

        for hit in cls.random_pool(query, *exclude, **kwargs).sort(elastic_settings.RANDOM_SORT)[:1]:
            return hit

    def __str__(self) -> str:
        official_str = '(OFFICIAL)' if self.is_official else ''

        part_indicators = ''.join([part[0].upper() for part in self.parts])
        parts_str = f'({part_indicators})'

        return ' '.join(filter(None, [official_str, parts_str, self.short]))

    @property
    def short(self) -> str:
        return f'{self.full_title} ({self.author})'

    @property
    def full_title(self) -> str:
        return f'{self.artist} - {self.title}'

    @property
    def link(self) -> str:
        return self.direct_download

    @property
    def is_playable(self) -> bool:
        playable_platforms = any(platform in self.platforms for platform in elastic_settings.e_platforms)
        playable_parts = any(part in self.parts for part in elastic_settings.e_parts)
        return playable_platforms and playable_parts

    @classmethod
    def earliest_not_auto(cls) -> Optional[int]:
        s = cls.search().exclude('term', from_auto_index=True)
        s.aggs.metric('earliest_not_auto', Min(field='snapshot_timestamp'))
        response = s[0:0].execute()
        return response.aggs.earliest_not_auto.value

    @classmethod
    def latest_auto_time(cls) -> Optional[int]:
        """
        When indexing, it is imperative that any automatic process sets the 'from_auto_index' flag. This way the process
        can know which CDLCs came from it. We can use this knowledge to find the timestamp stored with the CDLC to
        continue the process from where it finished last time.

        :returns timestamp which can be used to resume automatic indexing
        """
        ceiling = cls.earliest_not_auto()

        s = cls.search().filter('term', from_auto_index=True)
        if ceiling:
            s = s.filter('range', snapshot_timestamp={'lte': ceiling})

        s.aggs.metric('latest_auto_time', Max(field='snapshot_timestamp'))
        response = s[0:0].execute()
        return response.aggs.latest_auto_time.value


def random_query(field: str) -> Query:
    """
    This query is not used because it seems that it only adds to the score. Perhaps there is a way to make use of it,
    but why not just do it by hand...
    """
    return FunctionScore(random_score={'field': field, 'seed': str(random())})


def playable_query() -> Query:
    return Terms(platforms=elastic_settings.e_platforms) & Terms(parts=elastic_settings.e_parts)


def search_query(query: str) -> Query:
    q = fuzzy_match('full_title_grammar_comrade', query) | fuzzy_match('full_title_shingle_city', query)
    for merger in shingle_mergers:
        q |= fuzzy_match('full_title_shingle_city', query, merger)

    return q


def fuzzy_match(field: str, match: str, explicit_analyzer: Union[Analyzer, str] = None) -> Query:
    """
    This matching is optimized for the kind of searching that is expected when making requests.
    The user knows what they are looking for, so we match their query 100%.

    The query should be matched against a field which is combined from all the fields where the query is relevant.
    MultiMatch approach is not acceptable:
    1. If we use cross_fields, we lose the ability to perform fuzzy matching. This causes misspellings to almost
       always return nothing.
    2. If we do not use cross_fields, the minimum_should_match will apply per field.
      a. If we lower minimum_should_match, we will get a lot of false positives with any level of fuzziness.
         This can be particularly bad when the amount of terms is low, such as 2, causing it to round down to 1.
      b. If we keep minimum_should_match at 100%, we will only match documents which have all search terms in all
         fields, and since not many artists put their name in every song they make, this is not ideal.

    The query is performed with and without fuzziness to ensure fuzzy matches do not score higher than exact ones
    due to TF/IDF algorithms. This can happen when an exact match is one of many words, whereas the fuzzy match
    is the only word in the field. Multiple queries are likely preferable to simply turning those algorithms off.

    Finally, explicit analyzers are configurable for the query. This is necessary to perform matches against
    shingle-merge'd fields. These fields were shingle'd first, which combined all the words into pairs or multiples
    in the order they appear. Then the space between them was eliminated to create a sort-of a "combo" word.

    Here is an example where it can be useful: AC/DC can sometimes be indexed as ACDC or even AC DC.
    Similarly, the person requesting may enter any of these values, but expect the same results.

    The issue with shingle-merge'd fields is that their analyzer turns any shingles into synonyms. I am not sure
    if this is due to the way the functionality is used, or intended; however, the end result is that queries
    will fail to match documents in certain scenarios. I've made a spreadsheet which shows what happens (more or less):
    https://docs.google.com/spreadsheets/d/1TRuqbO_YCHIwHdmzFzEEXsD5Ke2rGzdkABdwVWBcmFg

    :returns query which finds match in given field, with some fuzziness allowed
    """
    options = {'query': match, 'minimum_should_match': '100%'}
    if explicit_analyzer:
        options['analyzer'] = explicit_analyzer

    fuzzy_options = options.copy()
    fuzzy_options['fuzziness'] = elastic_settings.e_fuzzy

    q1 = Match(**{field: options})
    q2 = Match(**{field: fuzzy_options})
    return q1 | q2


class ManualUserRank(BaseDoc):
    rank_name = Keyword(required=True)

    class Index:
        name = elastic_settings.e_rank_index
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    def set_rank(self, rank: UserRank, **kwargs):
        return self.set_rank_no_op(rank).save(**kwargs)

    def set_rank_no_op(self, rank: UserRank) -> ManualUserRank:
        self.rank_name = rank.name
        return self

    @property
    def rank(self) -> Optional[UserRank]:
        return UserRank[self.rank_name] if self.rank_name else None
