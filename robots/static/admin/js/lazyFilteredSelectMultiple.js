
function _append_spinner(select_el, spinner_url){
    var containerDiv = select_el.parent();
    containerDiv.css('position','relative');
    select_el.css('opacity', '.3');
    var posx = (select_el.position().left + select_el.width()) / 2 - 16;
    var posy = (select_el.position().top + select_el.height()) / 2 - 16;
    containerDiv.append(
        django.jQuery('<img src="'+ spinner_url +'"/>')
        .addClass('spinner')
        .css({
            'left': posx,
            'top': posy,
            'position': 'absolute'})
    );
}

function _add_choices(select_el, items){
    select_el.empty();
    django.jQuery(items).each(function(i, v){
        select_el.append(django.jQuery("<option>", { value: v[0], html: v[1] }));
    });
    select_el.css('opacity', '1');
    select_el.parent().find('img.spinner').remove()
}

function ajax_field_choices(field_name, choices_url, spinner_url){
    var from_el = django.jQuery("#id_"+ field_name +"_from");
    var to_el = django.jQuery("#id_"+ field_name +"_to");
    django.jQuery.ajax({
        url: choices_url,
        beforeSend:function (xhr, settings) {
            _append_spinner(from_el, spinner_url);
            _append_spinner(to_el, spinner_url);
        },
        success:function (data) {
            if (data != ""){
                _add_choices(from_el, data["choices"])
                _add_choices(to_el, data["assigned"])
            }
        },
    });
}
