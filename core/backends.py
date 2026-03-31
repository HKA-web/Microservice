import abc
import logging
import re

from django.conf import settings as djangosettings
from django.db.models import Q, FloatField
from django.db.models.expressions import Value
from django.utils.encoding import force_str

logger = logging.getLogger(__name__)


def regex_from_word(word):
    return r'(\s{word})|(^{word})'.format(
        word=re.escape(word),
    )


RE_POSTGRES_ESCAPE_CHARS = re.compile(r'[&:(|)!><]', re.UNICODE)
RE_SPACE = re.compile(r'[\s]+', re.UNICODE)


def escape_query(text, re_escape_chars):
    text = force_str(text)
    text = RE_SPACE.sub(' ', text)
    text = re_escape_chars.sub(' ', text)
    text = text.strip()
    return text


class SearchBackend(metaclass=abc.ABCMeta):
    def is_installed(self):
        return True

    def do_install(self):
        pass

    def do_uninstall(self):
        pass

    requires_installation = False
    supports_ranking = False
    supports_prefix_matching = False

    def do_search_ranking(self, engine_slug, queryset, search_text):
        return queryset.annotate(search_rank=Value(1.0, output_field=FloatField()))

    @abc.abstractmethod
    def do_search(self, engine_slug, queryset, search_text):
        raise NotImplementedError

    def do_filter_ranking(self, engine_slug, queryset, search_text):
        return queryset.annotate(search_rank=Value(1.0, output_field=FloatField()))

    @abc.abstractmethod
    def do_filter(self, engine_slug, queryset, search_text):
        raise NotImplementedError

    def do_string_cast(self, connection, column_name):
        return connection.ops.quote_name(column_name)


class RegexSearchMixin(metaclass=abc.ABCMeta):
    supports_prefix_matching = True

    def do_search(self, engine_slug, queryset, search_text):
        word_query = Q()
        for word in search_text.split():
            regex = regex_from_word(word)
            word_query &= (Q(title__iregex=regex) | Q(description__iregex=regex) | Q(content__iregex=regex))
        return queryset.filter(
            word_query
        )



class RegexSearchBackend(RegexSearchMixin, SearchBackend):
    pass


class PostgresSearchBackend(SearchBackend):
    search_config = getattr(djangosettings, 'SEARCH_POSTGRES_SEARCH_CONFIG', 'pg_catalog.english')

    def escape_postgres_query(self, text):
        return ' & '.join(
            '$${0}$$:*'.format(word)
            for word
            in escape_query(text, RE_POSTGRES_ESCAPE_CHARS).split()
        )

    requires_installation = True
    supports_ranking = True
    supports_prefix_matching = True

    def do_search(self, engine_slug, queryset, search_text):
        return queryset.extra(
            where=('''search_tsv @@ TO_TSQUERY('{search_config}', %s)'''.format(
                search_config=self.search_config
            ),),
            params=(self.escape_postgres_query(search_text),),
        )


    def do_string_cast(self, connection, column_name):
        return '{column_name}::TEXT'.format(
            column_name=connection.ops.quote_name(column_name),
        )


