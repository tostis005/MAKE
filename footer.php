</main>
<?php $site_name = make_brand_name(); $site_tagline = make_brand_tagline(); ?>
<footer class="site-footer">
  <div class="container footer-main">
    <div class="footer-intro">
      <div class="footer-brand"><?php echo esc_html( $site_name ); ?></div>
      <p class="footer-copy"><?php echo esc_html( make_t( 'Patrones digitales pensados para disfrutar del proceso y hacer cosas que merecen quedarse. Punto de cruz, C2C crochet, tapestry crochet y latch hook conviven en un mismo lenguaje de cuadrícula.', 'Digital patterns made for enjoying the process and creating things worth keeping. Cross stitch, C2C crochet, tapestry crochet and latch hook share one grid-based creative language.' ) ); ?></p>
    </div>

    <div>
      <h3 class="footer-title"><?php echo esc_html( make_t( 'Explora', 'Explore' ) ); ?></h3>
      <ul class="footer-links">
        <li><a href="<?php echo esc_url( make_journal_url() ); ?>"><?php echo esc_html( make_t( 'Aprender por técnica', 'Learn by technique' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Tienda de patrones', 'Pattern shop' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_editorial_craft_url( 'cross-stitch' ) ); ?>"><?php echo esc_html( make_t( 'Punto de cruz', 'Cross Stitch' ) ); ?></a></li>
      </ul>
    </div>

    <div>
      <h3 class="footer-title"><?php echo esc_html( make_t( 'Ayuda y legal', 'Help & legal' ) ); ?></h3>
      <ul class="footer-links">
        <li><a href="<?php echo esc_url( make_contact_url() ); ?>"><?php echo esc_html( make_t( 'Contacto', 'Contact' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_refund_policy_url() ); ?>"><?php echo esc_html( make_t( 'Reembolsos', 'Refunds' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_terms_url() ); ?>"><?php echo esc_html( make_t( 'Términos y condiciones', 'Terms & conditions' ) ); ?></a></li>
        <li><a href="<?php echo esc_url( make_privacy_url() ); ?>"><?php echo esc_html( make_t( 'Política de privacidad', 'Privacy policy' ) ); ?></a></li>
        <?php if ( class_exists( 'WooCommerce' ) ) : ?>
          <li><a href="<?php echo esc_url( make_account_url() ); ?>"><?php echo esc_html( make_t( 'Mi cuenta', 'My account' ) ); ?></a></li>
        <?php endif; ?>
      </ul>
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
