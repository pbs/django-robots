from django.conf import settings
from robots.models import Url
from robots.settings import ADMIN
from django.db.models import Q
from itertools import chain
from itertools import ifilterfalse, imap, izip
from django.utils.functional import memoize
from django.utils.importlib import import_module


ID_PREFIX = 'disallowed'


def get_site_id(data, instance, sites_field):
    if instance and instance.id:
        id = instance.sites.all()[0].id
    else:
        id = sites_field.choices.queryset[0].id
    return data.get('sites', id)


def get_url(pattern):
    try:
        return Url.objects.get_or_create(pattern=pattern)[0]
    except Url.MultipleObjectsReturned:
        return Url.objects.filter(pattern=pattern)[0]


def get_choices(site, protocol):
    """
    Returns a list with the urls patterns for the site parameter
    The list will be in this format required by the disallowed field widget:
    [['1', '/pattern1/'], ['2', '/pattern2/'], ['disallowed_3', '/pattern4/'], ...]

    The patterns are taken from the sitemap for the site param.
    Some of the ids are real db ids, and others (like disallowed_3) are fake ones
    (generated here).
    """
    def get_slug(url):
        return url['location'].replace("%s://%s" % (protocol, site.domain), '')

    # Make sure that the '/admin/' pattern is allways present
    #  in the choice list
    get_url(ADMIN)

    #generate patterns from the sitemap
    saved_site = settings.__class__.SITE_ID.value
    settings.__class__.SITE_ID.value = site.id
    urls = get_sitemap(site=site, protocol=protocol)
    all_sitemap_patterns = map(get_slug, urls)
    settings.__class__.SITE_ID.value = saved_site

    #Some patterns are already present in the db and I need their real ids
    #This processing step could have been avoided, but I need the sitemap
    #    patterns to be displayed first in the left side box.
    f = Q(pattern__in=all_sitemap_patterns)
    db_sitemap_urls = Url.objects.filter(f).values_list('id', 'pattern').distinct()
    db_sitemap_patterns = map(lambda url:url[1], db_sitemap_urls)

    # Generate some fake ids for the patterns that were not
    #  previously saved in the db
    remaining_sitemap_patterns = ifilterfalse(lambda x: x in db_sitemap_patterns, all_sitemap_patterns)
    fake_ids = imap(lambda x: '%s_%d' % (ID_PREFIX, x), range(len(urls)))

    db_remaining_urls = Url.objects.exclude(f).values_list('id', 'pattern').distinct()

    #returns a list of ['id', 'pattern'] pairs
    return imap(lambda x: list(x),
               chain(db_sitemap_urls,
                     izip(fake_ids, remaining_sitemap_patterns),
                     db_remaining_urls))


def get_sitemap_xml(root=None):
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
        res = get_sitemap_xml(urlpattern)
        if res:
            return res
    return {}


_resolver_cache = {}
get_sitemap_xml = memoize(get_sitemap_xml, _resolver_cache, 1)


def get_sitemap(site, protocol):
    sitemaps = get_sitemap_xml().get('sitemaps', {})
    urls = []
    for sitemap in sitemaps.values():
        try:
            if callable(sitemap):
                sitemap = sitemap()
            # page is 1 by default for get_urls method
            page = 1
            # iterate through cms pages and set homepage when found in order
            #   to not execute expensive queries just to re-fetch it for
            #   each root page
            homepage_pk = None
            site_pages = sitemap.paginator.page(page).object_list
            for page in site_pages:
                if not homepage_pk:
                    if page.is_home():
                        homepage_pk = page.pk
                else:
                    page.home_pk_cache = homepage_pk
            urls.extend(sitemap.get_urls(site=site, protocol=protocol))
        except:
            pass

    return urls
