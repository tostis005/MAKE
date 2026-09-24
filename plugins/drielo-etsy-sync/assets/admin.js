(function($){
  'use strict';
  $(function(){
    $('#drielo-select-all').on('change', function(){
      $('.drielo-row-select').prop('checked', this.checked);
    });

    $('#apply-bulk-target').on('click', function(){
      var target = $('#bulk-target').val();
      if (!target) return;
      $('.drielo-row-select:checked').each(function(){
        $(this).closest('tr').find('.drielo-target').val(target);
      });
    });

    $('[data-confirm-overwrite]').on('click', function(e){
      var selected = $('.drielo-row-select:checked').length;
      if (!selected) {
        e.preventDefault();
        window.alert('Selecciona al menos un producto. La sobrescritura nunca se aplica a todo el catálogo automáticamente.');
        return;
      }
      var ok = window.confirm(
        'Vas a sobrescribir en Etsy la información de ' + selected + ' producto(s) seleccionado(s): título, descripción, precio, tags, categoría, imágenes y PDF.\n\nLos cambios manuales hechos directamente en Etsy pueden perderse. ¿Continuar?'
      );
      if (!ok) e.preventDefault();
    });

    $('[data-copy]').on('click', function(){
      var selector = $(this).data('copy');
      var text = $(selector).text();
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
      } else {
        var el = $('<textarea>').val(text).appendTo('body').select();
        document.execCommand('copy');
        el.remove();
      }
      var btn = $(this), old = btn.text();
      btn.text('Copiado');
      setTimeout(function(){ btn.text(old); }, 1200);
    });
  });
})(jQuery);
