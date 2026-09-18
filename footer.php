</main>
<footer class="site-footer">
  <div class="container footer-main">
    <div><div class="footer-brand">MAKE.</div><p class="footer-copy"><?php echo esc_html( make_t( 'Patrones digitales pensados para disfrutar del proceso y hacer cosas que merecen quedarse. Hoy, punto de cruz. Mañana, todo lo que nos apetezca crear.', 'Digital patterns made for enjoying the process and creating things worth keeping. Cross stitch today; more crafts tomorrow.' ) ); ?></p></div>
    <div><h3 class="footer-title"><?php echo esc_html( make_t( 'Explora', 'Explore' ) ); ?></h3><ul class="footer-links"><li><a href="<?php echo esc_url( make_cross_stitch_url() ); ?>"><?php echo esc_html( make_t( 'Punto de cruz', 'Cross stitch' ) ); ?></a></li><li><a href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Todos los patrones', 'All patterns' ) ); ?></a></li><li><a href="<?php echo esc_url( home_url( '/blog/' ) ); ?>"><?php echo esc_html( make_t( 'Inspiración', 'Journal' ) ); ?></a></li></ul></div>
    <div><h3 class="footer-title"><?php echo esc_html( make_t( 'MAKE', 'MAKE' ) ); ?></h3><ul class="footer-links"><li><a href="<?php echo esc_url( home_url( '/about/' ) ); ?>"><?php echo esc_html( make_t( 'Sobre nosotros', 'About us' ) ); ?></a></li><li><a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>"><?php echo esc_html( make_t( 'Contacto', 'Contact' ) ); ?></a></li><li><a href="<?php echo esc_url( home_url( '/faq/' ) ); ?>">FAQ</a></li></ul></div>
  </div>
  <div class="container footer-bottom"><span>© <?php echo esc_html( gmdate( 'Y' ) ); ?> MAKE.</span><span><?php echo esc_html( make_t( 'Hecho despacio. Diseñado para durar.', 'Made slowly. Designed to last.' ) ); ?></span></div>
</footer>
<?php wp_footer(); ?>
</body></html>
