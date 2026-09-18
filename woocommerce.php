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
?>
<section class="shop-hero">
  <div class="container">
    <div class="shop-hero-inner">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Patrones digitales', 'Digital patterns' ) ); ?></span>
        <h1><?php echo esc_html( $title ); ?></h1>
      </div>
      <p><?php echo esc_html( make_t( 'Encuentra un proyecto que te apetezca empezar. Hoy el catálogo se centra en punto de cruz y está preparado para incorporar nuevas técnicas después.', 'Find a project you feel like starting. The catalogue focuses on cross stitch today and is ready to welcome more crafts later.' ) ); ?></p>
    </div>
  </div>
</section>

<section class="shop-main">
  <div class="container">
    <div class="shop-intro-row">
      <div class="shop-trust">
        <span>✓ <?php echo esc_html( make_t( 'Formato digital', 'Digital format' ) ); ?></span>
        <span>✓ <?php echo esc_html( make_t( 'Acceso tras la compra', 'Access after purchase' ) ); ?></span>
        <span>✓ <?php echo esc_html( make_t( 'Diseños revisados', 'Checked designs' ) ); ?></span>
      </div>
    </div>
    <div class="woocommerce-shell woocommerce-shell--archive">
      <?php woocommerce_content(); ?>
    </div>
  </div>
</section>
<?php
endif;

get_footer();
