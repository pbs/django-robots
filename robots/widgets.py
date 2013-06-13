from django.forms import Select
from django.utils.safestring import mark_safe
from django.template import loader, Context
from django.conf import settings
from robots.models import Url
from django.core.urlresolvers import reverse


class CustomSitesSelector(Select):

    def value_from_datadict(self, data, files, name):
        # the sites filed expects a list of values, while this widget returns
        # one by default
        return (super(CustomSitesSelector, self).value_from_datadict(data, files, name), )

    def render(self, name, value, attrs=None, choices=()):
        output = super(CustomSitesSelector, self).render(name, value, attrs=attrs, choices=choices)
        t = loader.get_template("robots/reload_disallowed.js")
        c = Context({
            'STATIC_URL': settings.STATIC_URL,
            'site_patterns_url': reverse('site_patterns')
        })
        return output + mark_safe(t.render(c))