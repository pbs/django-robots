from django.conf import settings
from robots.models import Url
from cms.sitemaps import CMSSitemap
from robots.settings import ADMIN
from django.db.models import Q
from itertools import chain
from itertools import ifilterfalse, imap, izip

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
    urls = CMSSitemap().get_urls(site=site, protocol=protocol)
    all_sitemap_patterns = map(lambda item: get_slug(item), urls)
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
