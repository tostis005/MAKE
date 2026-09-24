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
        $title = make_t( 'Colecciones de patrones', 'Pattern collections' );
    }

    $intro = make_t(
        'Explora cada patrón por separado o descubre colecciones temáticas creadas para reunir diseños relacionados.',
        'Browse each pattern individually or explore themed collections built around related designs.'
    );
    $hero_kicker = make_t( 'Patrones digitales', 'Digital patterns' );

    if ( is_tax( 'product_collection' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            if ( function_exists( 'make_collection_display_name' ) ) {
                $title = make_collection_display_name( $term );
            }
            if ( function_exists( 'make_collection_stats_label' ) ) {
                $hero_kicker = make_collection_stats_label( $term );
            }
            if ( function_exists( 'make_collection_stats_description' ) ) {
                $intro = make_collection_stats_description( $term );
            }
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
