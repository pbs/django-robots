from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('robots.views',
    url(r'^robots\.txt$', 'rules_list', name='robots_rule_list'),
)
