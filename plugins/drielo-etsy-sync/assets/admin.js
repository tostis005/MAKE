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
