from typing import Self

from ..settings import (
    DDCache,
)
from .client_hints import ClientHints
from .extractors import (
    NameExtractor,
    VersionExtractor,
)
from ..yaml_loader import RegexLoader, app_pretty_names_types_data


def build_version(version_str: str, truncation: int = 1) -> str:
    """
    Extract basic version from strings like 10.0.16299.371

    >>> build_version('10.0.16299.371')
    '10'

    >>> build_version('10')
    '10'
    """
    if truncation == -1:
        return version_str

    retain_segments = truncation + 1

    try:
        segments = version_str.replace('_', '.').split('.')
    except AttributeError:
        return version_str

    if len(segments) == retain_segments:
        return version_str

    return '.'.join(segments[:retain_segments])


class Parser(RegexLoader):
    # Constant used as value for unknown browser / os
    UNKNOWN = 'UNK'
    UNKNOWN_NAME = 'Unknown'

    __slots__ = (
        'user_agent',
        'ua',
        'ua_hash',
        'ua_spaceless',
        'ua_data',
        'app_name',
        'app_name_no_punctuation',
        'matched_regex',
        'app_version',
        'known',
        'secondary_client',
        'client_hints',
        'ch_client_data',
        'os_details',
        'appdetails_data',
    )

    def __init__(
        self,
        ua: str,
        ua_hash: str,
        ua_spaceless: str,
        client_hints: ClientHints | None,
        os_details: dict | None = None,
    ) -> None:
        super().__init__()

        self.user_agent = ua
        self.ua_hash = ua_hash
        self.ua_spaceless = ua_spaceless
        self.ua_data: dict = {}
        self.app_name = ''
        self.app_name_no_punctuation = ''
        self.matched_regex = None
        self.app_version = ''
        self.known = False
        self.secondary_client: dict = {}
        self.client_hints = client_hints
        self.ch_client_data = client_hints.client_data() if client_hints else {}
        self.os_details = os_details or {}
        self.appdetails_data = app_pretty_names_types_data()

    def get_from_cache(self) -> dict:
        try:
            return DDCache['user_agents'][self.ua_hash].get(self.cache_name, None)
        except KeyError:
            DDCache['user_agents'][self.ua_hash] = {}
        return {}

    def add_to_cache(self) -> dict:
        DDCache['user_agents'][self.ua_hash][self.cache_name] = self.ua_data
        return self.ua_data

    def _parse(self) -> None:
        """Override on subclasses if custom parsing is required"""
        user_agent = self.user_agent
        for ua_data in self.regex_list:
            if matched := ua_data['regex'].search(user_agent):
                self.matched_regex = matched
                self.ua_data |= {k: v for k, v in ua_data.items() if k != 'regex'}
                self.known = True
                return

    def parse(self) -> Self:
        """
        Return parsed details of UA String
        """
        details = self.get_from_cache()
        if details:
            return self

        self._parse()
        self.extract_details()

        return self

    def extract_details(self) -> dict:
        """
        Wrap set_details and call add_to_cache
        """
        self.extract_version()
        self.set_details()
        self.add_to_cache()
        return self.ua_data

    def extract_version(self) -> None:
        """
        Extract the version if UA Yaml files specify version regexes.
        See oss.yml for example file structure.
        """

        for version in self.ua_data.pop('versions', []):
            if version['regex'].search(self.user_agent):
                self.ua_data['version'] = version['version']
                return

    def set_details(self) -> None:
        """
        Override this method on subclasses.

        Update fields with interpolated values from regex data
        """
        groups = self.matched_regex and self.matched_regex.groups() or None
        if groups:
            if 'name' in self.ua_data:
                self.ua_data['name'] = NameExtractor(self.ua_data, groups).extract()

            if 'version' in self.ua_data:
                self.ua_data['version'] = VersionExtractor(self.ua_data, groups).extract()

        # no version should be considered valid if the name can't be parsed
        if not self.ua_data.get('name') and self.ua_data.get('version'):
            self.ua_data['version'] = ''

    def name(self) -> str:
        return self.ua_data.get('name', '')

    def version(self) -> str:
        return self.ua_data.get('version', '')

    def secondary_name(self) -> str:
        if self.secondary_client:
            return self.secondary_client['name']
        return ''

    def secondary_version(self) -> str:
        if self.secondary_client:
            return self.secondary_client['version']
        return ''

    def secondary_type(self) -> str:
        if self.secondary_client:
            return self.secondary_client['type']
        return ''

    def is_known(self) -> bool:
        if self.ua_data:
            return True
        return False

    def set_version(self, version: str) -> str:
        # return build_version(version, self.VERSION_TRUNCATION)
        return version

    def __str__(self) -> str:
        return self.name()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.user_agent}, {self.ua_data}, {self.ua_spaceless})'


__all__ = [
    'Parser',
]
