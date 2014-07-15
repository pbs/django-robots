from django.contrib import admin
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.utils.text import get_text_list
from django.contrib.sites.models import Site
from robots.settings import ADMIN
from robots import forms as robots_forms
from robots.models import Rule, Url
from robots.helpers import get_url, get_choices
import json


class RuleAdmin(admin.ModelAdmin):
    change_form = robots_forms.RuleAdminForm
    add_form = robots_forms.AddRuleAdminForm
    add_fieldsets = ((None, {'fields': ('sites', )}), )
    change_fieldsets = (
        (None, {'fields': ('site_domain', )}),
        (_('URL patterns'), {
            'fields': ('disallowed',),
        }),
        (_('Advanced options'), {
            'fields': ('crawl_delay', ),
            'classes': ('collapse', ),
        }),
    )
    readonly_in_change_form = ['site_domain', ]
    list_display = ('site_name', 'site_domain',
                    'allowed_urls', 'disallowed_urls')
    list_display_links = ('site_name', 'site_domain')
    search_fields = ('sites__name', 'sites__domain')

    def site_name(self, obj):
        return get_text_list([s.name for s in obj.sites.all()], _('and'))
    site_name.short_description = 'Site Display Name'

    def site_domain(self, obj):
        return get_text_list([s.domain for s in obj.sites.all()], _('and'))
    site_domain.short_description = 'Site Domain'

    def save_model(self, request, obj, form, change):
        super(RuleAdmin, self).save_model(request, obj, form, change)
        all_pattern = get_url('/')
        obj.allowed.add(all_pattern)
        # make sure it will get set for new rules
        admin_url = get_url(ADMIN)
        if not obj.disallowed.filter(id=admin_url.id).exists():
            obj.disallowed.add(admin_url)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            self.readonly_fields = ['site_domain', ]
        else:
            self.readonly_fields = []
        return super(RuleAdmin, self).get_readonly_fields(request, obj)

    def _reset_fields(self, action):
        self.form = getattr(self, "%s_form" % action, self.form)
        self.fieldsets = getattr(self, '%s_fieldsets' % action, ())

    def get_form(self, request, obj=None, **kwargs):
        self._reset_fields('add' if not obj else 'change')
        formCls = super(RuleAdmin, self).get_form(request, obj, **kwargs)

        if getattr(formCls, 'requires_request', False):

            class RequestFormClass(formCls):
                def __new__(cls, *args, **kwargs):
                    kwargs.update({"request": request})
                    return formCls(*args, **kwargs)

            return RequestFormClass
        return formCls

    def _get_allowed_sites(self, request):
        return super(RuleAdmin, self).formfield_for_manytomany(
            self.model._meta.get_field_by_name('sites')[0], request).queryset

    def has_add_permission(self, request):
        can_add = super(RuleAdmin, self).has_add_permission(request)
        # can add rules only for sites that don't have rules attached
        sites_qs = self._get_allowed_sites(request)
        return can_add and sites_qs.filter(rule__isnull=True).exists()

    def get_urls(self):
        urls = super(RuleAdmin, self).get_urls()
        url_patterns = patterns(
            '',
            url(r'^(?P<rule_id>\d+)/site-patterns/$',
                self.admin_site.admin_view(self.site_patterns),
                name='robots_current_site_urls'), )
        url_patterns.extend(urls)
        return url_patterns

    def site_patterns(self, request, rule_id):
        if not request.is_ajax():
            return HttpResponseForbidden()

        rule = get_object_or_404(Rule, id=rule_id)
        choices = get_choices(Site.objects.get_current(),
                              'https' if request.is_secure() else 'http')
        admin_url = get_url(ADMIN)
        # exclude admin url since we're adding it programatically
        initial = list(rule.disallowed.exclude(
            id=admin_url.id).values_list('id', 'pattern').order_by('pattern'))
        initial.insert(0, (admin_url.id, admin_url.pattern))

        data = {'choices': choices, 'assigned': initial}
        return HttpResponse(json.dumps(data), content_type="application/json")


admin.site.register(Url)
admin.site.register(Rule, RuleAdmin)
