<?php
$current_language = make_current_language();
$current_flag = 'en' === $current_language ? '🇺🇸' : '🇪🇸';
$home_url = make_home_url();
$nav = array(
    array( 'label' => make_t( 'Punto de cruz', 'Cross stitch' ), 'url' => make_cross_stitch_url() ),
    array( 'label' => make_t( 'Patrones', 'Patterns' ), 'url' => make_shop_url() ),
    array( 'label' => make_t( 'Inspiración', 'Journal' ), 'url' => home_url( '/blog/' ) ),
    array( 'label' => make_t( 'Sobre MAKE', 'About MAKE' ), 'url' => home_url( '/about/' ) ),
);
?><!doctype html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#f7f3ea">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<div class="make-announcement"><?php echo esc_html( make_t( 'Patrones digitales · descarga inmediata · crea a tu ritmo', 'Digital patterns · instant download · make at your pace' ) ); ?></div>
<header class="site-header">
  <div class="container header-main">
    <a class="site-brand" href="<?php echo esc_url( $home_url ); ?>" aria-label="MAKE">
      <span class="brand-mark" aria-hidden="true"><?php for ( $i = 0; $i < 9; $i++ ) : ?><i></i><?php endfor; ?></span>
      <span class="brand-copy"><strong class="brand-word">MAKE.</strong><small class="brand-tagline"><?php echo esc_html( make_t( 'patterns for slow making', 'patterns for slow making' ) ); ?></small></span>
    </a>
    <nav class="primary-nav" aria-label="<?php echo esc_attr( make_t( 'Navegación principal', 'Primary navigation' ) ); ?>">
      <ul><?php foreach ( $nav as $item ) : ?><li><a href="<?php echo esc_url( $item['url'] ); ?>"><?php echo esc_html( $item['label'] ); ?></a></li><?php endforeach; ?></ul>
    </nav>
    <div class="header-actions">
      <button class="icon-button language-trigger" type="button" data-open-overlay="make-language-overlay" aria-label="<?php echo esc_attr( make_t( 'Cambiar idioma', 'Change language' ) ); ?>"><span class="language-flag" aria-hidden="true"><?php echo esc_html( $current_flag ); ?></span></button>
      <button class="icon-button" type="button" data-open-overlay="make-search-overlay" aria-label="<?php echo esc_attr( make_t( 'Buscar', 'Search' ) ); ?>"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="M15.5 15.5 21 21"></path></svg></button>
      <?php if ( class_exists( 'WooCommerce' ) ) : ?><a class="icon-button" href="<?php echo esc_url( make_cart_url() ); ?>" aria-label="<?php echo esc_attr( make_t( 'Carrito', 'Cart' ) ); ?>"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 4h2l2.2 10.2h9.7l2-7.1H6.1"></path><circle cx="9" cy="19" r="1.3"></circle><circle cx="17" cy="19" r="1.3"></circle></svg><?php if ( make_cart_count() ) : ?><span class="cart-count"><?php echo esc_html( (string) make_cart_count() ); ?></span><?php endif; ?></a><?php endif; ?>
      <button class="icon-button menu-trigger" type="button" data-open-overlay="make-mobile-menu" aria-label="<?php echo esc_attr( make_t( 'Abrir menú', 'Open menu' ) ); ?>"><span></span><span></span><span></span></button>
    </div>
  </div>
</header>

<div class="make-overlay" id="make-search-overlay" data-make-overlay role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="make-search-title">
  <div class="overlay-top"><div class="overlay-brand">MAKE.</div><button class="overlay-close" type="button" data-close-overlay aria-label="<?php echo esc_attr( make_t( 'Cerrar buscador', 'Close search' ) ); ?>">×</button></div>
  <div class="overlay-body"><div class="search-panel"><span class="overlay-eyebrow"><?php echo esc_html( make_t( 'Buscar en MAKE', 'Search MAKE' ) ); ?></span><h2 class="overlay-title" id="make-search-title"><?php echo esc_html( make_t( '¿Qué quieres crear?', 'What do you want to make?' ) ); ?></h2><form class="overlay-search-form" role="search" method="get" action="<?php echo esc_url( $home_url ); ?>"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="M15.5 15.5 21 21"></path></svg><input data-overlay-autofocus type="search" name="s" value="<?php echo esc_attr( get_search_query() ); ?>" placeholder="<?php echo esc_attr( make_t( 'Patrones, flores, retratos…', 'Patterns, flowers, portraits…' ) ); ?>"><button type="submit"><?php echo esc_html( make_t( 'Buscar', 'Search' ) ); ?></button></form></div></div>
</div>

<div class="make-overlay" id="make-language-overlay" data-make-overlay role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="make-language-title">
  <div class="overlay-top"><div class="overlay-brand">MAKE.</div><button class="overlay-close" type="button" data-close-overlay aria-label="<?php echo esc_attr( make_t( 'Cerrar idioma', 'Close language' ) ); ?>">×</button></div>
  <div class="overlay-body"><div class="language-panel"><span class="overlay-eyebrow"><?php echo esc_html( make_t( 'Idioma', 'Language' ) ); ?></span><h2 class="overlay-title" id="make-language-title"><?php echo esc_html( make_t( 'Elige tu idioma', 'Choose your language' ) ); ?></h2><div class="language-options"><a class="language-option <?php echo 'es' === $current_language ? 'is-current' : ''; ?>" href="<?php echo esc_url( make_language_switch_url( 'es' ) ); ?>" hreflang="es-ES" lang="es"><span class="language-option-flag">🇪🇸</span><span class="language-option-copy"><strong>Español</strong><small>ES</small></span></a><a class="language-option <?php echo 'en' === $current_language ? 'is-current' : ''; ?>" href="<?php echo esc_url( make_language_switch_url( 'en' ) ); ?>" hreflang="en-US" lang="en"><span class="language-option-flag">🇺🇸</span><span class="language-option-copy"><strong>English</strong><small>EN</small></span></a></div></div></div>
</div>

<div class="make-overlay" id="make-mobile-menu" data-make-overlay role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="make-menu-title">
  <div class="overlay-top"><div class="overlay-brand" id="make-menu-title">MAKE.</div><button class="overlay-close" type="button" data-close-overlay aria-label="<?php echo esc_attr( make_t( 'Cerrar menú', 'Close menu' ) ); ?>">×</button></div>
  <div class="overlay-body"><div class="mobile-menu-panel"><nav class="mobile-menu-nav" aria-label="<?php echo esc_attr( make_t( 'Menú móvil', 'Mobile menu' ) ); ?>"><ul><?php foreach ( $nav as $item ) : ?><li><a href="<?php echo esc_url( $item['url'] ); ?>"><?php echo esc_html( $item['label'] ); ?></a></li><?php endforeach; ?></ul></nav><div class="mobile-menu-actions"><button class="mobile-menu-language" type="button" data-open-overlay="make-language-overlay"><span class="language-flag"><?php echo esc_html( $current_flag ); ?></span><?php echo esc_html( make_t( 'Cambiar idioma', 'Change language' ) ); ?></button></div></div></div>
</div>
<main id="main-content">
