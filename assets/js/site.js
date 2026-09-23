(function(){
  'use strict';
  var active=null,lastFocused=null;
  function focusables(el){return Array.prototype.slice.call(el.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')).filter(function(node){return node.offsetParent!==null;});}
  function close(overlay,restore){if(!overlay)return;overlay.classList.remove('is-open');overlay.setAttribute('aria-hidden','true');document.body.classList.remove('make-overlay-open');active=null;if(restore!==false&&lastFocused&&lastFocused.focus)lastFocused.focus();}
  function open(id,trigger){var overlay=document.getElementById(id);if(!overlay)return;if(active&&active!==overlay)close(active,false);lastFocused=trigger||document.activeElement;active=overlay;overlay.classList.add('is-open');overlay.setAttribute('aria-hidden','false');document.body.classList.add('make-overlay-open');window.requestAnimationFrame(function(){var auto=overlay.querySelector('[data-overlay-autofocus]');var list=focusables(overlay);if(auto&&auto.focus)auto.focus();else if(list.length)list[0].focus();});}
  document.addEventListener('click',function(e){var opener=e.target.closest('[data-open-overlay]');if(opener){e.preventDefault();open(opener.getAttribute('data-open-overlay'),opener);return;}var closer=e.target.closest('[data-close-overlay]');if(closer){e.preventDefault();close(closer.closest('[data-make-overlay]'));return;}var menuLink=e.target.closest('.mobile-menu-nav a');if(menuLink&&active&&active.id==='make-mobile-menu')close(active,false);});
  document.addEventListener('keydown',function(e){if(!active)return;if(e.key==='Escape'){e.preventDefault();close(active);return;}if(e.key!=='Tab')return;var list=focusables(active);if(!list.length)return;var first=list[0],last=list[list.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});
})();


(function(){
  'use strict';

  function cookie(name){
    var prefix=name+'=';
    var parts=document.cookie ? document.cookie.split(';') : [];
    for(var i=0;i<parts.length;i++){
      var part=parts[i].trim();
      if(part.indexOf(prefix)===0)return decodeURIComponent(part.slice(prefix.length));
    }
    return '';
  }

  function pageCurrency(){
    if(document.body.classList.contains('make-currency-eur'))return 'EUR';
    return 'USD';
  }

  function parseAmount(text){
    var cleaned=(text||'').replace(/\u00a0/g,' ').replace(/[^0-9,.-]/g,'').trim();
    if(!cleaned)return NaN;
    var lastComma=cleaned.lastIndexOf(',');
    var lastDot=cleaned.lastIndexOf('.');
    if(lastComma>-1&&lastDot>-1){
      if(lastComma>lastDot)cleaned=cleaned.replace(/\./g,'').replace(',','.');
      else cleaned=cleaned.replace(/,/g,'');
    }else if(lastComma>-1){
      cleaned=cleaned.replace(',','.');
    }
    return parseFloat(cleaned);
  }

  function renderAmount(node,value,currency){
    if(!isFinite(value))return;
    var lang=(document.documentElement.lang||'es').toLowerCase();
    var locale=lang.indexOf('en')===0?'en-US':'es-ES';
    var number=new Intl.NumberFormat(locale,{minimumFractionDigits:2,maximumFractionDigits:2}).format(value);
    var bdi=document.createElement('bdi');
    var symbol=document.createElement('span');
    symbol.className='woocommerce-Price-currencySymbol';
    symbol.textContent=currency==='EUR'?'€':'$';
    bdi.appendChild(symbol);
    bdi.appendChild(document.createTextNode(number));
    while(node.firstChild)node.removeChild(node.firstChild);
    node.appendChild(bdi);
  }

  function syncCurrencyPrices(){
    if(!document.body)return;
    var target=(cookie('drielo_currency')||'USD').toUpperCase();
    if(target!=='EUR'&&target!=='USD')target='USD';

    var source=pageCurrency();
    var rate=parseFloat(cookie('drielo_usd_eur_rate'));
    if(!isFinite(rate)||rate<=0)rate=0.87032;

    var amounts=document.querySelectorAll('.woocommerce-Price-amount');
    for(var i=0;i<amounts.length;i++){
      var value=parseAmount(amounts[i].textContent);
      if(!isFinite(value))continue;
      if(source==='USD'&&target==='EUR')value=value*rate;
      else if(source==='EUR'&&target==='USD')value=value/rate;
      renderAmount(amounts[i],value,target);
    }

    document.body.classList.remove('make-currency-usd','make-currency-eur');
    document.body.classList.add('make-currency-'+target.toLowerCase());
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',syncCurrencyPrices);
  else syncCurrencyPrices();

  if(window.jQuery){
    window.jQuery(document.body).on('updated_cart_totals updated_checkout wc_fragments_refreshed added_to_cart',syncCurrencyPrices);
  }
})();


(function(){
  'use strict';

  function collectionColumns(count){
    if(count<=0)return 5;
    return Math.max(4,Math.min(12,Math.ceil(Math.sqrt(count*1.25))));
  }

  function initDrieloCollectionTechniqueCards(){
    var cards=document.querySelectorAll('[data-collection-card]');
    for(var i=0;i<cards.length;i++){
      (function(card){
        var buttons=Array.prototype.slice.call(card.querySelectorAll('[data-collection-technique]'));
        var thumbs=Array.prototype.slice.call(card.querySelectorAll('[data-collection-thumb]'));
        var grid=card.querySelector('.drielo-collection-thumbs--interactive');
        if(!buttons.length||!thumbs.length||!grid)return;

        function applyTechnique(slug){
          var visible=0;
          for(var j=0;j<thumbs.length;j++){
            var show=!slug||thumbs[j].getAttribute('data-technique')===slug;
            thumbs[j].hidden=!show;
            if(show)visible++;
          }
          grid.style.setProperty('--collection-cols',String(collectionColumns(visible)));

          for(var k=0;k<buttons.length;k++){
            var active=!!slug&&buttons[k].getAttribute('data-collection-technique')===slug;
            buttons[k].classList.toggle('is-active',active);
            buttons[k].setAttribute('aria-pressed',active?'true':'false');
          }
        }

        for(var b=0;b<buttons.length;b++){
          buttons[b].addEventListener('click',function(){
            if(this.disabled)return;
            var slug=this.getAttribute('data-collection-technique')||'';
            var isActive=this.getAttribute('aria-pressed')==='true';
            applyTechnique(isActive?'':slug);
          });
        }
      })(cards[i]);
    }
  }

  function simplifyDrieloTechniqueHub(){
    var hub=document.querySelector('.drielo-technique-hub');
    if(!hub)return;

    var links=Array.prototype.slice.call(hub.querySelectorAll('a'));
    for(var i=0;i<links.length;i++){
      var text=(links[i].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
      if(text.indexOf('todos los patrones')!==-1||text.indexOf('todos los productos')!==-1||text.indexOf('all patterns')!==-1||text.indexOf('all products')!==-1){
        var card=links[i];
        while(card.parentElement&&card.parentElement!==hub)card=card.parentElement;
        if(card&&card!==hub)card.remove();
      }
    }

    var descriptions=hub.querySelectorAll('p,[class*="description"]');
    for(var d=0;d<descriptions.length;d++)descriptions[d].remove();
  }

  function initDrieloStorePresentation(){
    simplifyDrieloTechniqueHub();
    initDrieloCollectionTechniqueCards();
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initDrieloStorePresentation);
  else initDrieloStorePresentation();
})();
