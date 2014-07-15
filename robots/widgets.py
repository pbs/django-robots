from django.forms import Select
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.admin.templatetags.admin_static import static
from django.utils.safestring import mark_safe
from django.template import loader, Context
from django.conf import settings


class FilteredSelect(Select):

    class Media:
        js = (static("admin/js/SelectBox.js"), )


    def render(self, name, value, attrs=None, choices=()):
        output = super(FilteredSelect, self).render(
            name, value, attrs=attrs, choices=choices)

        template = loader.get_template("robots/filtered_select_widget.html")
        context = Context({
            'select_widget_output' : output,
            'STATIC_URL': settings.STATIC_URL,
            'field_name': name
        })
        return mark_safe(template.render(context))


class AjaxFilteredSelectMultiple(FilteredSelectMultiple):

    class Media:
        js = (static("admin/js/lazyFilteredSelectMultiple.js"), )

    init_field_script = (
        "<script type='text/javascript'>"
        "addEvent(window, 'load', function(e) {"
        "ajax_field_choices('%s', '%s', '%s');"
        "});"
        "</script>")

    def __init__(self, *args, **kwargs):
        self.choices_url = kwargs.pop('choices_url', '')
        super(AjaxFilteredSelectMultiple, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=()):
        widget_html = super(AjaxFilteredSelectMultiple, self).render(
            name, value, attrs=attrs, choices=choices)
        if not self.choices_url:
            return widget_html
        output = "%s%s" % (
            widget_html, self.init_field_script % (
                name, self.choices_url, static("admin/img/ajax-loader.gif")))
        return mark_safe(output)
