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

    var syncPollTimer = null;

    function scheduleSyncPoll(){
      if (syncPollTimer) {
        window.clearTimeout(syncPollTimer);
        syncPollTimer = null;
      }
      var panel = $('#drielo-sync-run');
      if (!panel.length || panel.attr('data-active') !== '1' || typeof DrieloEtsySync === 'undefined') return;
      syncPollTimer = window.setTimeout(refreshSyncRun, parseInt(DrieloEtsySync.pollMs || 4000, 10));
    }

    function refreshSyncRun(){
      if (typeof DrieloEtsySync === 'undefined') return;
      $.post(DrieloEtsySync.ajaxUrl, {
        action: 'drielo_etsy_sync_status',
        nonce: DrieloEtsySync.nonce
      }).done(function(response){
        if (response && response.success && response.data && response.data.html) {
          $('#drielo-sync-run').replaceWith(response.data.html);
        }
      }).always(function(){
        scheduleSyncPoll();
      });
    }

    scheduleSyncPoll();

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
