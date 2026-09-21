<?php
get_header();

if ( function_exists( 'is_product' ) && is_product() ) :
?>
<section class="make-product-page">
  <div class="container">
    <a class="commerce-back" href="<?php echo esc_url( make_shop_url() ); ?>">← <?php echo esc_html( make_t( 'Volver a la tienda', 'Back to shop' ) ); ?></a>
    <div class="woocommerce-shell woocommerce-shell--single">
      <?php woocommerce_content(); ?>
    </div>
  </div>
</section>
<?php
else :
    $title = make_archive_title();
    $is_collection_view = function_exists( 'is_shop' ) && is_shop() && function_exists( 'make_store_view' ) && 'collections' === make_store_view();

    if ( $is_collection_view ) {
        $title = make_t( 'Colecciones de patrones', 'Pattern collections' );
    }

    $intro = make_t(
        'Explora cada patrón por separado o descubre colecciones que comparten la misma paleta de colores e hilos.',
        'Browse each pattern individually or discover collections that share the same colour and thread palette.'
    );

    if ( is_tax( 'product_collection' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term && '' !== trim( (string) $term->description ) ) {
            $intro = wp_strip_all_tags( $term->description );
        } else {
            $intro = make_t(
                'Todos los diseños de esta colección reutilizan la misma paleta, para que puedas cambiar de proyecto sin cambiar de hilos.',
                'Every design in this collection reuses the same palette, so you can switch projects without switching threads.'
            );
        }
    }
?>
<section class="shop-hero">
  <div class="container">
    <div class="shop-hero-inner">
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

    <div class="shop-intro-row">
      <div class="shop-trust">
        <span>✓ <?php echo esc_html( make_t( 'PDF descargable', 'Downloadable PDF' ) ); ?></span>
        <span>✓ <?php echo esc_html( make_t( 'USD o EUR', 'USD or EUR' ) ); ?></span>
        <span>✓ <?php echo esc_html( make_t( 'Acceso tras la compra', 'Access after purchase' ) ); ?></span>
      </div>
    </div>

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
