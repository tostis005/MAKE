<?php
get_header();

if ( function_exists( 'is_product' ) && is_product() ) :
?>
<section class="make-product-page">
  <div class="container">
    <a class="commerce-back" href="<?php echo esc_url( make_shop_url() ); ?>">← <?php echo esc_html( make_t( 'Volver a la tienda', 'Back to shop' ) ); ?></a>
    <?php if ( function_exists( 'make_render_shop_view_switcher' ) ) { make_render_shop_view_switcher(); } ?>
    <div class="woocommerce-shell woocommerce-shell--single">
      <?php woocommerce_content(); ?>
    </div>
  </div>
</section>
<?php
else :
    $title = make_archive_title();
    $is_shop_archive = function_exists( 'is_shop' ) && is_shop();
    $is_collection_view = $is_shop_archive && function_exists( 'make_store_view' ) && 'collections' === make_store_view();

    if ( $is_collection_view ) {
        $title = make_t( 'Colecciones de patrones digitales', 'Digital Pattern Collections' );
    } elseif ( $is_shop_archive ) {
        $title = make_t( 'Patrones PDF de punto de cruz y manualidades', 'Cross Stitch & Craft Pattern PDFs' );
    }

    $intro = function_exists( 'make_store_seo_archive_description' )
        ? make_store_seo_archive_description()
        : make_t(
            'Explora patrones digitales descargables con gráficos claros y detalles prácticos para cada proyecto.',
            'Browse downloadable digital patterns with clear charts and practical details for every project.'
        );
    $hero_kicker = make_t( 'Patrones digitales descargables', 'Downloadable digital patterns' );

    if ( is_tax( 'product_collection' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $name = function_exists( 'make_collection_display_name' ) ? make_collection_display_name( $term ) : (string) $term->name;
            $techniques = function_exists( 'make_store_seo_collection_techniques' ) ? make_store_seo_collection_techniques( $term ) : array();
            $title = 1 === count( $techniques ) && 'cross-stitch' === reset( $techniques )
                ? sprintf( make_t( '%s · Patrones de punto de cruz PDF', '%s Cross Stitch Patterns PDF' ), $name )
                : sprintf( make_t( '%s · Patrones PDF', '%s Pattern PDFs' ), $name );
            if ( function_exists( 'make_collection_stats_label' ) ) {
                $hero_kicker = make_collection_stats_label( $term );
            }
        }
    } elseif ( is_tax( 'pa_technique' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $label = function_exists( 'make_store_technique_label' )
                ? make_store_technique_label( (string) $term->slug, make_current_language() )
                : (string) $term->name;
            $title = 'cross-stitch' === $term->slug
                ? make_t( 'Patrones de Punto de Cruz PDF', 'Cross Stitch Patterns PDF' )
                : sprintf( make_t( 'Patrones PDF de %s', '%s Patterns PDF' ), $label );
            $hero_kicker = make_t( 'Descarga digital · gráficos imprimibles', 'Digital download · printable charts' );
        }
    } elseif ( is_tax( 'product_cat' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $title = sprintf( make_t( '%s · Patrones PDF', '%s Pattern PDFs' ), $term->name );
        }
    }
?>
<section class="shop-hero <?php echo $is_collection_view ? 'shop-hero--collections' : ''; ?> <?php echo $is_shop_archive ? 'shop-hero--store' : ''; ?>">
  <div class="container">
    <div class="shop-hero-inner <?php echo $is_shop_archive ? 'shop-hero-inner--stacked' : ''; ?>">
      <div>
        <span class="section-kicker"><?php echo esc_html( $hero_kicker ); ?></span>
        <h1><?php echo esc_html( $title ); ?></h1>
      </div>
      <p><?php echo esc_html( $intro ); ?></p>
    </div>
  </div>
</section>

<section class="shop-main">
  <div class="container">
    <?php if ( function_exists( 'make_render_shop_view_switcher' ) ) { make_render_shop_view_switcher(); } ?>

    <?php if ( function_exists( 'make_collection_archive_note' ) ) { make_collection_archive_note(); } ?>

    <div class="woocommerce-shell woocommerce-shell--archive <?php echo $is_collection_view ? 'woocommerce-shell--collections' : ''; ?>">
      <?php
      if ( $is_collection_view && function_exists( 'make_render_collection_grid' ) ) {
          make_render_collection_grid();
      } else {
          woocommerce_content();
      }
      ?>
    </div>
  </div>
</section>
<?php
endif;

get_footer();
