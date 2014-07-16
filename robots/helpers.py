import urlparse
import re

from django.db import router
from django.core import urlresolvers
from django.core.exceptions import ViewDoesNotExist
from django.utils.encoding import force_unicode

from robots.models import Url
from robots.settings import EXCLUDE_URL_NAMES, SITEMAP_VIEWS


def get_url(pattern):
    manager = Url.objects.db_manager(router.db_for_write(Url))
    try:
        return manager.get_or_create(pattern=pattern)[0]
    except Url.MultipleObjectsReturned:
        return manager.filter(pattern=pattern)[0]


def get_view_urlpattern_data(view_name):
    resolver = urlresolvers.get_resolver(None)
    lookup_dict = resolver.reverse_dict
    try:
        view_data = (lookup_dict.get(view_name) or
                     lookup_dict.get(urlresolvers.get_callable(view_name)))
    except ViewDoesNotExist:
        view_data = None
    # see django/core/urlresolvers: RegexURLResolver._populate
    #   view_data: bits, pattern, default_args
    return view_data


def get_sitemaps_from_views():
    """
    Fetches sitemaps provided as default arguments to the sitemap view.
    """
    sitemaps = []
    for view_name in SITEMAP_VIEWS:
        view_data = get_view_urlpattern_data(view_name)
        if not view_data:
            continue
        bits, pattern, default_args = view_data
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


def head2unicode((head, tail)):
    return [force_unicode(head), tail]


exclude_patterns = []


def get_choices(site, protocol='http'):
    """
        Returns a list of choices(id, pattern pairs) for Url objects
    that have patterns generated from sitemaps.
    """
    if EXCLUDE_URL_NAMES and not exclude_patterns:
        exclude_patterns = map(lambda view: get_view_urlpattern_data(view)[1],
                               EXCLUDE_URL_NAMES)

    def should_exclude(url):
        """
        Checks to see if a url matches any of the patterns from views
        specified by EXCLUDE_URL_NAMES.
        """
        return any((re.search(patt, url)
                    for patt in exclude_patterns)) is True

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
    manager = Url.objects.db_manager(router.db_for_write(Url))

    existing_urls_qs = manager.filter(pattern__in=site_urls)\
        .values_list('pk', 'pattern')

    existing_patterns = set(map(lambda (_, pattern): pattern,
                                existing_urls_qs))
    # generate url objects
    manager.bulk_create([Url(pattern=url)
                         for url in site_urls
                         if url not in existing_patterns])
    # re-evaluate queryset to fetch latest data
    return map(head2unicode, existing_urls_qs.order_by('pattern'))
