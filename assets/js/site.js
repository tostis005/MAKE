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
          var matching=[];
          for(var j=0;j<thumbs.length;j++){
            if(!slug||thumbs[j].getAttribute('data-technique')===slug)matching.push(thumbs[j]);
          }

          var previewSlots=24;
          var thumbLimit=matching.length>previewSlots?previewSlots-1:previewSlots;
          var shown=0;

          for(var x=0;x<thumbs.length;x++){
            var match=matching.indexOf(thumbs[x])!==-1;
            var show=match&&shown<thumbLimit;
            thumbs[x].hidden=!show;
            if(show)shown++;
          }

          var more=card.querySelector('[data-collection-more]');
          var moreCount=card.querySelector('[data-collection-more-count]');
          var remaining=Math.max(0,matching.length-shown);
          if(more){
            more.hidden=remaining<1;
            if(moreCount)moreCount.textContent='+'+remaining;
          }

          grid.style.setProperty('--collection-cols','6');

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
        applyTechnique('');
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
        var parent=card.parentElement;
        while(parent&&parent!==hub){
          if(parent.parentElement===hub)break;
          card=parent;
          parent=parent.parentElement;
        }
        if(card&&card!==hub)card.remove();
      }
    }

    var descriptions=hub.querySelectorAll('p,small,[class*="description"]');
    for(var d=0;d<descriptions.length;d++)descriptions[d].remove();

    var language=(document.documentElement.lang||'es').toLowerCase().indexOf('en')===0?'en':'es';
    var techniques=[
      {
        key:'cross-stitch',
        match:['punto de cruz','cross stitch'],
        es:'Punto de cruz',en:'Cross Stitch',
        icon:'<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="15"></circle><path d="M14 9h20"></path><path d="M18 17l12 14M30 17L18 31"></path></svg>'
      },
      {
        key:'c2c-crochet',
        match:['c2c crochet','corner to corner'],
        es:'C2C Crochet',en:'C2C Crochet',
        icon:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M11 33c7-1 11-5 14-11l7-13"></path><path d="M30 9h6c2 0 3 2 2 4l-2 3"></path><rect x="10" y="29" width="7" height="7" rx="1"></rect><rect x="18" y="21" width="7" height="7" rx="1"></rect><rect x="26" y="29" width="7" height="7" rx="1"></rect></svg>'
      },
      {
        key:'tapestry-crochet',
        match:['tapestry crochet','crochet tapestry'],
        es:'Tapestry Crochet',en:'Tapestry Crochet',
        icon:'<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="10" y="10" width="21" height="28" rx="2"></rect><path d="M14 16h13M14 22h13M14 28h13M14 34h13"></path><path d="M34 10c4 5 4 10 0 15l-5 6"></path><path d="M31 32l5-6"></path></svg>'
      },
      {
        key:'latch-hook',
        match:['latch hook','rug'],
        es:'Latch Hook',en:'Latch Hook',
        icon:'<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="10" y="12" width="24" height="25" rx="2"></rect><path d="M14 17h16M14 23h16M14 29h16M18 12v25M26 12v25"></path><path d="M36 9l-8 13"></path><path d="M27 22l5 1 2-5"></path></svg>'
      }
    ];

    var techniqueLinks=Array.prototype.slice.call(hub.querySelectorAll('a'));
    for(var t=0;t<techniqueLinks.length;t++){
      var raw=(techniqueLinks[t].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
      var spec=null;
      for(var x=0;x<techniques.length&&!spec;x++){
        for(var y=0;y<techniques[x].match.length;y++){
          if(raw.indexOf(techniques[x].match[y])!==-1){spec=techniques[x];break;}
        }
      }
      if(!spec)continue;

      var top=techniqueLinks[t];
      while(top.parentElement&&top.parentElement!==hub)top=top.parentElement;
      if(top&&top!==hub){
        top.classList.add('drielo-technique-card--compact','drielo-technique-card--'+spec.key);
      }

      techniqueLinks[t].classList.add('drielo-technique-link--compact');
      techniqueLinks[t].setAttribute('data-drielo-technique',spec.key);
      techniqueLinks[t].innerHTML='<span class="drielo-technique-compact-icon">'+spec.icon+'</span><strong class="drielo-technique-compact-title">'+(language==='en'?spec.en:spec.es)+'</strong>';
    }
  }

  function initDrieloStorePresentation(){
    simplifyDrieloTechniqueHub();
    initDrieloCollectionTechniqueCards();
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initDrieloStorePresentation);
  else initDrieloStorePresentation();
})();


(function(){
  'use strict';

  function initDrieloProductGalleryLightbox(){
    var galleries=Array.prototype.slice.call(document.querySelectorAll('.woocommerce-product-gallery'));
    if(!galleries.length)return;

    var overlay=document.querySelector('[data-drielo-gallery-lightbox]');
    if(!overlay){
      overlay=document.createElement('div');
      overlay.className='drielo-gallery-lightbox';
      overlay.setAttribute('data-drielo-gallery-lightbox','');
      overlay.setAttribute('aria-hidden','true');
      overlay.innerHTML='<div class="drielo-gallery-lightbox__backdrop" data-drielo-gallery-close></div><div class="drielo-gallery-lightbox__dialog" role="dialog" aria-modal="true" aria-label="Product image"><button type="button" class="drielo-gallery-lightbox__close" data-drielo-gallery-close aria-label="Close">×</button><img class="drielo-gallery-lightbox__image" alt=""></div>';
      document.body.appendChild(overlay);
    }

    var largeImage=overlay.querySelector('.drielo-gallery-lightbox__image');
    var lastFocused=null;

    function closeLightbox(){
      overlay.classList.remove('is-open');
      overlay.setAttribute('aria-hidden','true');
      document.body.classList.remove('drielo-gallery-lightbox-open');
      if(largeImage){largeImage.removeAttribute('src');largeImage.alt='';}
      if(lastFocused&&lastFocused.focus)lastFocused.focus();
    }

    function openLightbox(img){
      if(!img||!largeImage)return;
      var src=img.currentSrc||img.getAttribute('src')||'';
      if(!src)return;
      lastFocused=document.activeElement;
      largeImage.src=src;
      largeImage.alt=img.getAttribute('alt')||'';
      overlay.classList.add('is-open');
      overlay.setAttribute('aria-hidden','false');
      document.body.classList.add('drielo-gallery-lightbox-open');
      var closeButton=overlay.querySelector('.drielo-gallery-lightbox__close');
      if(closeButton&&closeButton.focus)closeButton.focus();
    }

    function gallerySlides(gallery){
      return Array.prototype.slice.call(gallery.querySelectorAll('.woocommerce-product-gallery__wrapper > .woocommerce-product-gallery__image'));
    }

    function captureGallerySources(gallery){
      var slides=gallerySlides(gallery);
      var sources=[];
      for(var i=0;i<slides.length;i++){
        var img=slides[i].querySelector('img');
        sources.push(img ? {
          src:img.currentSrc||img.getAttribute('src')||'',
          alt:img.getAttribute('alt')||'',
          width:img.getAttribute('width')||'',
          height:img.getAttribute('height')||''
        } : null);
      }
      gallery._drieloGallerySources=sources;
      return sources;
    }

    function selectGalleryImage(gallery,index){
      var slides=gallerySlides(gallery);
      if(index<0||index>=slides.length)return;

      var sources=gallery._drieloGallerySources||captureGallerySources(gallery);
      var source=sources[index];
      var primary=slides[0]&&slides[0].querySelector('img');
      if(!source||!source.src||!primary)return;

      gallery.classList.add('drielo-gallery-direct');
      gallery.classList.remove('drielo-gallery-fallback');

      primary.src=source.src;
      primary.removeAttribute('srcset');
      primary.removeAttribute('sizes');
      primary.alt=source.alt||'';
      if(source.width)primary.setAttribute('width',source.width);
      if(source.height)primary.setAttribute('height',source.height);

      var thumbs=Array.prototype.slice.call(gallery.querySelectorAll('.flex-control-thumbs img'));
      for(var t=0;t<thumbs.length;t++){
        thumbs[t].classList.toggle('flex-active',t===index);
        thumbs[t].setAttribute('aria-current',t===index?'true':'false');
      }
    }

    for(var g=0;g<galleries.length;g++){
      captureGallerySources(galleries[g]);
      var images=galleries[g].querySelectorAll('.woocommerce-product-gallery__image img');
      for(var x=0;x<images.length;x++){
        images[x].setAttribute('tabindex','0');
        images[x].setAttribute('role','button');
        images[x].setAttribute('aria-label',(document.documentElement.lang||'es').toLowerCase().indexOf('en')===0?'View image larger':'Ver imagen ampliada');
      }
    }

    document.addEventListener('click',function(e){
      var closeTarget=e.target.closest('[data-drielo-gallery-close]');
      if(closeTarget&&overlay.contains(closeTarget)){
        e.preventDefault();
        closeLightbox();
        return;
      }

      var thumb=e.target.closest('.flex-control-thumbs img');
      if(thumb){
        var gallery=thumb.closest('.woocommerce-product-gallery');
        if(gallery){
          var thumbs=Array.prototype.slice.call(gallery.querySelectorAll('.flex-control-thumbs img'));
          var index=thumbs.indexOf(thumb);
          if(index>=0){
            e.preventDefault();
            e.stopPropagation();
            selectGalleryImage(gallery,index);
          }
        }
        return;
      }

      var main=e.target.closest('.woocommerce-product-gallery__image img');
      if(main){
        e.preventDefault();
        openLightbox(main);
      }
    });

    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&overlay.classList.contains('is-open')){
        e.preventDefault();
        closeLightbox();
        return;
      }
      if((e.key==='Enter'||e.key===' ')&&e.target&&e.target.matches('.woocommerce-product-gallery__image img')){
        e.preventDefault();
        openLightbox(e.target);
      }
    });
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initDrieloProductGalleryLightbox);
  else initDrieloProductGalleryLightbox();
})();
