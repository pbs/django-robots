from itertools import chain
from itertools import ifilterfalse, imap, izip
from contextlib import contextmanager
import urlparse

from django.conf import settings
from django.db.models import Q
from django.utils.functional import memoize, partition
from django.utils.importlib import import_module
from django.utils.encoding import force_unicode
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse, resolve

from robots.models import Url
from robots.settings import EXCLUDE_URL_NAMES


def get_url(pattern):
    try:
        return Url.objects.get_or_create(pattern=pattern)[0]
    except Url.MultipleObjectsReturned:
        return Url.objects.filter(pattern=pattern)[0]


def get_sitemap_from_urlpatterns(root=None):
    """
    Performs a breadth-first search through the url patterns defined in ROOT_URLCONF
    to find sitemap.xml slug
    """
    if not root:
        mod = import_module(settings.ROOT_URLCONF)
        url_patterns = mod.urlpatterns
    else:
        url_patterns = getattr(root, 'url_patterns', [])

    for urlpattern in url_patterns:
        if 'sitemap.xml' in urlpattern.regex.pattern:
            return urlpattern.default_args

    for urlpattern in url_patterns:
        res = get_sitemap_from_urlpatterns(urlpattern)
        if res:
            return res
    return {}


def get_sitemap(site, protocol):
    urlpatterns = get_sitemap_from_urlpatterns()
    sitemaps = urlpatterns.get('sitemaps', {})
    urls = []
    for sitemap in sitemaps.values():
        try:
            if callable(sitemap):
                sitemap = sitemap()
            urls.extend(sitemap.get_urls(site=site, protocol=protocol))
        except:
            pass
    locations = map(
        lambda item: urlparse.urlparse(item['location']).path,
        urls
    )
    return locations


def head2unicode((head,tail)):
    return [force_unicode(head), tail]


def get_choices(site, protocol='http'):
    """
    Returns a list with the urls patterns for the site parameter
    The list will be in this format required by the disallowed field widget:
    [['1', '/pattern1/'], ['2', '/pattern2/'], ['disallowed_3', '/pattern4/'], ...]

    The patterns are taken from the sitemap for the site param.
    Some of the ids are real db ids, and others (like disallowed_3) are fake ones
    (generated here).
    """
    admin_url = reverse('admin:index')

    def fetch_urls():
        urls = [
            url
            for url in get_sitemap(site, protocol)
            if resolve(url).url_name not in EXCLUDE_URL_NAMES
        ]
        return urls

    with patch(settings, fetch_urls, SITE_ID=site.pk) as result:
        sitemap_urls = result
    site_urls = [admin_url] + sitemap_urls
    in_site_urls = Q(pattern__in=set(site_urls))
    existing_url_pairs = Url.objects.filter(in_site_urls).values_list('pk', 'pattern')
    url_patterns = set(map(lambda (_, url): url, existing_url_pairs))
    non_existing, existings = partition(
        lambda url: url in url_patterns,
        set(site_urls)
    )
    non_existing_options = map(
        lambda (number, url): ['disallowed_' + str(number), url],
        enumerate(non_existing)
    )
    existing_options = map(head2unicode, existing_url_pairs)
    options = sorted(
        existing_options + non_existing_options,
        key=lambda (_, pattern): pattern
    )
    return options



@contextmanager
def patch(instance, fn, **kwargs):
    def save():
        return {
            key: getattr(instance.__class__, key, None)
            for key, _ in kwargs.items()
        }

    def set_state(state):
        for key, value in state.items():
            setattr(instance.__class__, key, value)

    original = save()
    set_state(kwargs)
    yield fn()
    set_state(original)
