</main>
<?php $site_name = make_brand_name(); $site_tagline = make_brand_tagline(); ?>
<footer class="site-footer">
  <div class="container footer-main">
    <div class="footer-intro">
      <div class="footer-brand"><?php echo esc_html( $site_name ); ?></div>
      <p class="footer-copy"><?php echo esc_html( make_t( 'Patrones digitales pensados para disfrutar del proceso y hacer cosas que merecen quedarse. Empezamos con punto de cruz y la estructura está preparada para crecer hacia nuevas técnicas.', 'Digital patterns made for enjoying the process and creating things worth keeping. We are starting with cross stitch and the structure is ready to grow into more crafts.' ) ); ?></p>
    </div>

    <div>
      <h3 class="footer-title"><?php echo esc_html( make_t( 'Explora', 'Explore' ) ); ?></h3>
      <ul class="footer-links">
        <li><a href="<?php echo esc_url( make_cross_stitch_url() ); ?>"><?php echo esc_html( make_t( 'Punto de cruz', 'Cross stitch' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Tienda de patrones', 'Pattern shop' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_journal_url() ); ?>"><?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></a></li>
      </ul>
    </div>

    <div>
      <h3 class="footer-title"><?php echo esc_html( make_t( 'Información', 'Information' ) ); ?></h3>
      <?php if ( has_nav_menu( 'footer' ) ) : ?>
        <?php wp_nav_menu( array( 'theme_location' => 'footer', 'container' => false, 'menu_class' => 'footer-links', 'fallback_cb' => false ) ); ?>
      <?php else : ?>
        <ul class="footer-links">
          <?php if ( get_privacy_policy_url() ) : ?><li><a href="<?php echo esc_url( get_privacy_policy_url() ); ?>"><?php echo esc_html( make_t( 'Privacidad', 'Privacy' ) ); ?></a></li><?php endif; ?>
          <?php if ( class_exists( 'WooCommerce' ) ) : ?>
            <li><a href="<?php echo esc_url( wc_get_page_permalink( 'myaccount' ) ); ?>"><?php echo esc_html( make_t( 'Mi cuenta', 'My account' ) ); ?></a></li>
            <li><a href="<?php echo esc_url( make_cart_url() ); ?>"><?php echo esc_html( make_t( 'Carrito', 'Cart' ) ); ?></a></li>
          <?php endif; ?>
        </ul>
      <?php endif; ?>
    </div>
  </div>

  <div class="container footer-bottom">
    <span>© <?php echo esc_html( gmdate( 'Y' ) . ' ' . $site_name ); ?></span>
    <span><?php echo esc_html( $site_tagline ); ?></span>
  </div>
</footer>
<?php wp_footer(); ?>
</body>
</html>
