import urlparse
import re
from collections import namedtuple

from django.db import router
from django.core.exceptions import ViewDoesNotExist
from django.core import urlresolvers

from robots.models import Url
from robots import settings


def get_url_manager():
    return Url.objects.db_manager(router.db_for_write(Url))


def get_url(pattern):
    manager = get_url_manager()
    try:
        return manager.get_or_create(pattern=pattern)[0]
    except Url.MultipleObjectsReturned:
        return manager.filter(pattern=pattern)[0]


def get_view_urlpattern_data(view_name):
    resolver = urlresolvers.get_resolver(None)
    lookup_dict = resolver.reverse_dict
    # see django/core/urlresolvlers: RegexURLResolver._populate
    view = namedtuple('view', 'bits pattern default_args')
    try:
        view_data = (lookup_dict.get(view_name) or
                     lookup_dict.get(urlresolvers.get_callable(view_name)))
    except ViewDoesNotExist:
        view_data = None

    if not view_data:
        return view(*((None, ) * 3))
    return view(*view_data)


def get_sitemaps_from_views():
    """
    Fetches sitemaps provided as default arguments to the sitemap view.
    """
    sitemaps = []
    for view_name in settings.SITEMAP_VIEWS:
        default_args = get_view_urlpattern_data(view_name).default_args or {}
        sitemaps += (default_args.get('sitemaps') or {}).values()
    return sitemaps


def get_paths_from_sitemaps(site, protocol):
    """
    Returns a list of paths fetched from all sitemaps items location.
    """
    urls = []
    for sitemap in get_sitemaps_from_views():
        try:
            if callable(sitemap):
                sitemap = sitemap()
            urls.extend(sitemap.get_urls(site=site, protocol=protocol))
        except:
            pass
    return map(lambda item: urlparse.urlparse(item['location']).path, urls)


_EXCLUDE_PATTERNS = filter(
    None, map(lambda view: get_view_urlpattern_data(view).pattern,
              settings.EXCLUDE_URL_NAMES))


def get_available_urls(site, protocol='http'):
    """
        Returns a list of choices(id, pattern pairs) for Url objects
    that have patterns generated from sitemaps.
    """

    def should_exclude(url):
        """
        Checks to see if a url matches any of the patterns from views
        specified by EXCLUDE_URL_NAMES.
        """
        return any((re.search(patt, url)
                    for patt in _EXCLUDE_PATTERNS)) is True

    def fetch_urls():
        """
        Returns a set of url paths fetched from sitemaps.
        """
        return set(
            url
            for url in get_paths_from_sitemaps(site, protocol)
            if not should_exclude(url)
        )

    site_urls = fetch_urls()
    manager = get_url_manager()

    existing_urls_qs = manager.filter(pattern__in=site_urls)\
        .values_list('pk', 'pattern')

    existing_patterns = set(map(lambda (_, pattern): pattern,
                                existing_urls_qs))
    # We can afford using bulk_create since we don't have any signals for
    #   url save operation
    manager.bulk_create([Url(pattern=url)
                         for url in site_urls
                         if url not in existing_patterns])

    return existing_urls_qs.order_by('pattern')
