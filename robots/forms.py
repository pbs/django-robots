from django import forms
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from robots.models import Rule
from robots.widgets import AjaxFilteredSelectMultiple
from robots.settings import ADMIN


def _set_cms_site(request, site):
    if request:
        # used by django cms; designates the current wokring site
        # this should not change anything when cms is not installed
        request.session['cms_admin_site'] = site.pk


class AddRuleAdminForm(forms.ModelForm):
    requires_request = True

    class Meta:
        model = Rule
        fields = ('sites', )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(AddRuleAdminForm, self).__init__(*args, **kwargs)
        self._init_sites()

    def _init_sites(self):
        sites_field = self.fields['sites']
        sites_field.widget.can_add_related = False
        current_site = Site.objects.get_current()
        if (not self.initial.get('sites') and
                sites_field.queryset.filter(id=current_site.id).exists()):
            self.initial['sites'] = current_site

    def clean_sites(self):
        site = self.cleaned_data.get('sites')
        if not site:
            raise forms.ValidationError("Site required.")
        if Rule.objects.filter(sites=site).exists():
            raise forms.ValidationError(
                "Rule for this site already exists. "
                "You can change it from the list view.")
        _set_cms_site(self.request, site)
        return [site]


class RuleAdminForm(forms.ModelForm):
    requires_request = True

    class Meta:
        model = Rule
        widgets = {
            'disallowed': AjaxFilteredSelectMultiple(
                verbose_name='Disallows', is_stacked=False)
        }
        exclude = ()

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(RuleAdminForm, self).__init__(*args, **kwargs)
        _set_cms_site(self.request, self.instance.site)
        self._initialize_disallowed_field()

    def _initialize_disallowed_field(self):
        disallowed_field = self.fields['disallowed']
        disallowed_field.widget.widget.choices_url = reverse(
            'admin:robots_current_site_urls', args=(self.instance.pk, ))
        # this is prepopulated with choices from robots_current_site_urls
        disallowed_field.choices = ()

    def clean_disallowed(self):
        from robots.helpers import get_url
        submitted = list(self.cleaned_data.get('disallowed') or [])
        # set default value
        submitted.append(get_url(ADMIN))
        return submitted
