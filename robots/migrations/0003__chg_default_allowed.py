# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from robots.models import Rule, Url
from django.db import router


def get_url(pattern, manager):
    try:
        return manager.get_or_create(pattern=pattern)[0]
    except Url.MultipleObjectsReturned:
        return manager.filter(pattern=pattern)[0]


class Migration(SchemaMigration):

    no_dry_run = True

    def forwards(self, orm):

        rules_manager = orm.models.get("robots.rule").objects\
                        .db_manager(router.db_for_write(Rule))
        url_manager = orm.models.get("robots.url").objects\
                        .db_manager(router.db_for_write(Url))

        allow_new = get_url('/', url_manager)
        allow_old = get_url('/*', url_manager)
        for r in rules_manager.all().exclude(allowed__in=[allow_new]):
            r.allowed.remove(allow_old)
            r.allowed.add(allow_new)

    def backwards(self, orm):
        pass

    models = {
        'robots.rule': {
            'Meta': {'object_name': 'Rule'},
            'allowed': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'allowed'", 'blank': 'True', 'to': "orm['robots.Url']"}),
            'crawl_delay': ('django.db.models.fields.DecimalField', [], {'default': '5.0', 'max_digits': '3', 'decimal_places': '1'}),
            'disallowed': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'disallowed'", 'blank': 'True', 'to': "orm['robots.Url']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'robot': ('django.db.models.fields.CharField', [], {'default': "'*'", 'max_length': '255'}),
            'sites': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sites.Site']", 'symmetrical': 'False'})
        },
        'robots.url': {
            'Meta': {'object_name': 'Url'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pattern': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['robots']