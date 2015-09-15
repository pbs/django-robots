from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from importlib import import_module
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from robots.models import Url, Rule
from robots import settings
from cms.api import create_page
from cms.models import Page
import sys


class TestRules(TestCase):

    def setUp(self):
        self.site = Site.objects.get_current()
        self._create_pages()
        self.user = User.objects.create_superuser(
            'admin', 'admin@robots.com', 'secret')
        self.client.login(username='admin', password='secret')

    def _create_pages(self):
        for i in range(4):
            defaults = ('page%s' % i, 'test.html', 'en')
            pagei = create_page(*defaults, published=True)
            create_page(*defaults, published=True, parent=pagei)

    def test_urls_auto_generate_from_sitemap(self):
        self.assertFalse(Url.objects.exists())
        from robots.helpers import get_available_urls
        urls = sorted(dict(get_available_urls(self.site, 'http')).values())
        pages_urls = sorted([p.get_absolute_url() for p in Page.objects.all()])
        self.assertItemsEqual(urls, pages_urls)

    def test_admin_pattern_available(self):
        self.assertFalse(Url.objects.exists())
        self.assertFalse(Rule.objects.exists())

        data = {'sites': "%s" % self.site.pk}
        self.client.post(reverse('admin:robots_rule_add'), data)
        rule = Rule.objects.all().get()
        allowed_url, admin_disallowed = list(Url.objects.all())
        self.assertTrue(allowed_url.pattern, '/')
        self.assertTrue(admin_disallowed.pattern, reverse('admin:index'))
        # ensure admin is always disallowed
        self.client.post(reverse('admin:robots_rule_change', args=(rule.id,)),
                         {'disallowed': [], 'crawl_delay': 0.5})
        rule = Rule.objects.all().get()
        disallowed_assigned = list(rule.disallowed.all())
        self.assertItemsEqual([admin_disallowed], disallowed_assigned)
        # ensure non sitemap url can be assigned
        test_pattern = Url.objects.create(pattern='/test/')
        self.client.post(reverse('admin:robots_rule_change', args=(rule.id,)),
                         {'disallowed': [test_pattern.pk], 'crawl_delay': 0.5})
        rule = Rule.objects.all().get()
        disallowed_assigned = list(rule.disallowed.all())
        self.assertItemsEqual(
            sorted([admin_disallowed, test_pattern], key=lambda x: x.pattern),
            sorted(disallowed_assigned, key=lambda x: x.pattern))

    def _reload_exclude_patterns(self, items):
        settings.EXCLUDE_URL_NAMES = items
        if 'robots.helpers' in sys.modules:
            reload(sys.modules['robots.helpers'])
        else:
            import_module('robots.helpers')

    @override_settings(ROBOTS_EXCLUDE_URL_NAMES=['cms.views.details'])
    def test_exclude_urls(self):
        self.assertFalse(Url.objects.exists())
        self._reload_exclude_patterns(['cms.views.details'])
        from robots.helpers import get_available_urls
        self.assertEquals(len(get_available_urls(self.site, 'http')), 0)
        self._reload_exclude_patterns([])
