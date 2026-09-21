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
        'Explora cada patrón por separado o descubre colecciones que comparten una misma paleta de color.',
        'Browse each pattern individually or discover collections that share the same colour palette.'
    );

    if ( is_tax( 'product_collection' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            if ( function_exists( 'make_collection_display_name' ) ) {
                $title = make_collection_display_name( $term );
            }
            if ( function_exists( 'make_collection_display_description' ) ) {
                $localized_intro = make_collection_display_description( $term );
                if ( '' !== $localized_intro ) { $intro = $localized_intro; }
            }
        }

        if ( '' === trim( (string) $intro ) ) {
            $intro = make_t(
                'Diseños que comparten una misma paleta de color para que puedas combinarlos dentro de la colección.',
                'Designs that share one colour palette so you can combine them within the collection.'
            );
        }
    }
?>
<section class="shop-hero <?php echo $is_collection_view ? 'shop-hero--collections' : ''; ?> <?php echo $is_shop_archive ? 'shop-hero--store' : ''; ?>">
  <div class="container">
    <div class="shop-hero-inner <?php echo $is_shop_archive ? 'shop-hero-inner--stacked' : ''; ?>">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Patrones digitales', 'Digital patterns' ) ); ?></span>
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
