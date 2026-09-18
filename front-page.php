<?php
get_header();
$site_name = make_brand_name();
?>

<section class="hero">
  <div class="container">
    <div class="hero-shell">
      <div class="hero-copy">
        <span class="eyebrow"><?php echo esc_html( make_t( 'Patrones digitales para disfrutar haciendo', 'Digital patterns made for the joy of making' ) ); ?></span>
        <h1><?php echo wp_kses_post( make_t( 'Haz algo que <em>merezca quedarse.</em>', 'Make something <em>worth keeping.</em>' ) ); ?></h1>
        <p><?php echo esc_html( make_t( 'Empezamos con punto de cruz: diseños claros, cuidados y fáciles de seguir. La web está preparada para crecer después hacia crochet, bordado y otras técnicas sin cambiar de identidad.', 'We are starting with cross stitch: clear, considered patterns that are easy to follow. The site is already structured to grow into crochet, embroidery and other crafts without changing identity.' ) ); ?></p>
        <div class="hero-actions">
          <a class="button button-primary" href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Explorar la tienda', 'Explore the shop' ) ); ?> →</a>
          <button class="button button-secondary" type="button" data-open-overlay="make-search-overlay"><?php echo esc_html( make_t( 'Buscar un diseño', 'Find a design' ) ); ?></button>
        </div>
        <div class="hero-note">
          <span><i>✓</i><?php echo esc_html( make_t( 'Patrones digitales', 'Digital patterns' ) ); ?></span>
          <span><i>✓</i><?php echo esc_html( make_t( 'Diseños revisados', 'Checked designs' ) ); ?></span>
          <span><i>✓</i><?php echo esc_html( make_t( 'Compra sencilla', 'Simple purchase' ) ); ?></span>
        </div>
      </div>

      <div class="hero-art" aria-hidden="true">
        <div class="hero-art-inner">
          <span class="hero-label"><?php echo esc_html( make_t( 'Un rato para ti ✦', 'A little time for you ✦' ) ); ?></span>
          <img class="hero-cross-stitch" src="<?php echo esc_url( get_template_directory_uri() . '/assets/images/hero-botanical-cross-stitch.svg' ); ?>" alt="" width="760" height="760" fetchpriority="high">
          <div class="hero-caption">
            <span class="hero-caption-flower">✿</span>
            <span><?php echo esc_html( make_t( 'puntada a puntada', 'stitch by stitch' ) ); ?></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section craft-discovery">
  <div class="container">
    <header class="section-head">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Elige cómo quieres crear', 'Choose how you want to make' ) ); ?></span>
        <h2 class="section-title"><?php echo esc_html( make_t( 'Una casa para patrones, no para una sola técnica.', 'A home for patterns, not just one craft.' ) ); ?></h2>
      </div>
      <p class="section-intro"><?php echo esc_html( make_t( 'El punto de cruz es el comienzo. La estructura visual y comercial ya está pensada para incorporar nuevas técnicas cuando tenga sentido.', 'Cross stitch is the beginning. The visual and commerce structure is already designed to welcome new crafts when the time is right.' ) ); ?></p>
    </header>

    <div class="craft-grid">
      <a class="craft-card craft-card--feature" href="<?php echo esc_url( make_cross_stitch_url() ); ?>">
        <small><?php echo esc_html( make_t( 'Disponible ahora', 'Available now' ) ); ?></small>
        <strong><?php echo esc_html( make_t( 'Punto de cruz', 'Cross stitch' ) ); ?></strong>
        <p><?php echo esc_html( make_t( 'Patrones visuales, claros y listos para convertir tiempo tranquilo en una pieza terminada.', 'Visual, clear patterns ready to turn quiet time into a finished piece.' ) ); ?></p>
        <span class="craft-arrow">→</span>
      </a>

      <a class="craft-card" href="<?php echo esc_url( make_pattern_url( make_t( 'flores', 'flowers' ) ) ); ?>">
        <span class="craft-icon">✿</span>
        <small><?php echo esc_html( make_t( 'Explora por estilo', 'Browse by style' ) ); ?></small>
        <strong><?php echo esc_html( make_t( 'Botánicos', 'Botanical' ) ); ?></strong>
        <p><?php echo esc_html( make_t( 'Flores, hojas y motivos orgánicos para enmarcar o regalar.', 'Flowers, leaves and organic motifs to frame or gift.' ) ); ?></p>
      </a>

      <a class="craft-card" href="<?php echo esc_url( make_pattern_url( make_t( 'retratos', 'portraits' ) ) ); ?>">
        <span class="craft-icon">◇</span>
        <small><?php echo esc_html( make_t( 'Explora por estilo', 'Browse by style' ) ); ?></small>
        <strong><?php echo esc_html( make_t( 'Retratos', 'Portraits' ) ); ?></strong>
        <p><?php echo esc_html( make_t( 'Diseños con personalidad para proyectos que se sienten más personales.', 'Characterful designs for projects that feel more personal.' ) ); ?></p>
      </a>

      <div class="craft-card craft-card--future">
        <span class="craft-icon">⌁</span>
        <small><?php echo esc_html( make_t( 'Preparado para crecer', 'Built to grow' ) ); ?></small>
        <strong><?php echo esc_html( make_t( 'Crochet y más', 'Crochet and more' ) ); ?></strong>
        <p><?php echo esc_html( make_t( 'La misma tienda podrá incorporar nuevas técnicas sin rehacer la experiencia.', 'The same shop can add new crafts without rebuilding the experience.' ) ); ?></p>
      </div>
    </div>
  </div>
</section>

<section class="section products-section">
  <div class="container">
    <header class="section-head">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Patrones destacados', 'Featured patterns' ) ); ?></span>
        <h2 class="section-title"><?php echo esc_html( make_t( 'Elige un proyecto y empieza.', 'Choose a project and start.' ) ); ?></h2>
      </div>
      <a class="text-link" href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Ver toda la tienda', 'View the whole shop' ) ); ?> →</a>
    </header>

    <?php if ( class_exists( 'WooCommerce' ) ) : ?>
      <?php
      $products = new WP_Query(
          array(
              'post_type'           => 'product',
              'post_status'         => 'publish',
              'posts_per_page'      => 4,
              'ignore_sticky_posts' => true,
              'meta_query'          => WC()->query->get_meta_query(),
              'tax_query'           => WC()->query->get_tax_query(),
          )
      );
      ?>
      <div class="product-grid">
        <?php if ( $products->have_posts() ) : ?>
          <?php while ( $products->have_posts() ) : $products->the_post(); $product = wc_get_product( get_the_ID() ); ?>
            <article class="product-card">
              <a href="<?php the_permalink(); ?>">
                <div class="product-media">
                  <?php if ( has_post_thumbnail() ) : ?>
                    <?php the_post_thumbnail( 'make-card', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); ?>
                  <?php else : ?>
                    <div class="product-placeholder"><span class="mini-grid"><?php for ( $i = 0; $i < 64; $i++ ) : ?><i></i><?php endfor; ?></span></div>
                  <?php endif; ?>
                  <span class="product-badge"><?php echo esc_html( make_t( 'Patrón digital', 'Digital pattern' ) ); ?></span>
                </div>
                <div class="product-copy">
                  <span class="product-type"><?php echo esc_html( make_t( 'Proyecto creativo', 'Creative project' ) ); ?></span>
                  <h3 class="product-title"><?php the_title(); ?></h3>
                  <?php if ( $product ) : ?><div class="product-price"><?php echo wp_kses_post( $product->get_price_html() ); ?></div><?php endif; ?>
                </div>
              </a>
            </article>
          <?php endwhile; wp_reset_postdata(); ?>
        <?php else : ?>
          <div class="empty-products">
            <span class="empty-products-mark" aria-hidden="true">× × ×</span>
            <strong><?php echo esc_html( make_t( 'La tienda está lista para tus primeros patrones.', 'The shop is ready for your first patterns.' ) ); ?></strong>
            <small><?php echo esc_html( make_t( 'Cuando publiques productos en WooCommerce aparecerán aquí automáticamente.', 'When you publish WooCommerce products they will appear here automatically.' ) ); ?></small>
          </div>
        <?php endif; ?>
      </div>
    <?php else : ?>
      <div class="empty-products">
        <strong><?php echo esc_html( make_t( 'Activa WooCommerce para empezar a vender patrones.', 'Activate WooCommerce to start selling patterns.' ) ); ?></strong>
      </div>
    <?php endif; ?>
  </div>
</section>

<section class="section maker-promise">
  <div class="container">
    <div class="promise-grid">
      <div class="promise-visual" aria-hidden="true"><span class="thread-ball"></span></div>
      <div class="promise-copy">
        <span class="section-kicker"><?php echo esc_html( make_t( 'La experiencia importa', 'The experience matters' ) ); ?></span>
        <h2><?php echo esc_html( make_t( 'Menos ruido. Más ganas de crear.', 'Less noise. More making.' ) ); ?></h2>
        <p><?php echo esc_html( make_t( 'La tienda y los artículos comparten el mismo lenguaje visual: limpio, cálido y centrado en el proyecto. Así la web puede crecer sin parecer una suma de piezas diferentes.', 'The shop and editorial content share the same visual language: clean, warm and centered on the project. That lets the site grow without feeling like a collection of unrelated pieces.' ) ); ?></p>

        <div class="promise-list">
          <div class="promise-item"><strong><?php echo esc_html( make_t( 'Compra clara', 'Clear purchase' ) ); ?></strong><span><?php echo esc_html( make_t( 'Producto, precio y descarga sin distracciones.', 'Product, price and download without distraction.' ) ); ?></span></div>
          <div class="promise-item"><strong><?php echo esc_html( make_t( 'Diseño editorial', 'Editorial design' ) ); ?></strong><span><?php echo esc_html( make_t( 'Artículos legibles y útiles, no una plantilla genérica.', 'Readable, useful articles rather than a generic template.' ) ); ?></span></div>
          <div class="promise-item"><strong><?php echo esc_html( make_t( 'Móvil primero', 'Mobile first' ) ); ?></strong><span><?php echo esc_html( make_t( 'Menú, buscador e idioma a pantalla completa.', 'Full-screen menu, search and language controls.' ) ); ?></span></div>
          <div class="promise-item"><strong><?php echo esc_html( make_t( 'Preparada para crecer', 'Ready to grow' ) ); ?></strong><span><?php echo esc_html( make_t( 'Nuevas técnicas sin cambiar de plataforma ni de estética.', 'New crafts without changing platform or visual identity.' ) ); ?></span></div>
        </div>
      </div>
    </div>
  </div>
</section>

<?php
$journal = new WP_Query(
    array(
        'post_type'           => 'post',
        'post_status'         => 'publish',
        'posts_per_page'      => 3,
        'ignore_sticky_posts' => true,
        'meta_query'          => array(
            array(
                'key'   => '_make_language',
                'value' => make_current_language(),
            ),
        ),
    )
);
?>
<section class="section journal-section">
  <div class="container">
    <header class="section-head">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></span>
        <h2 class="section-title"><?php echo esc_html( make_t( 'Ideas, guías y proyectos para disfrutar más del proceso.', 'Ideas, guides and projects for enjoying the process more.' ) ); ?></h2>
      </div>
      <?php if ( $journal->have_posts() ) : ?><a class="text-link" href="<?php echo esc_url( make_journal_url() ); ?>"><?php echo esc_html( make_t( 'Ver todos', 'See all' ) ); ?> →</a><?php endif; ?>
    </header>

    <?php if ( $journal->have_posts() ) : ?>
      <div class="journal-grid">
        <?php while ( $journal->have_posts() ) : $journal->the_post(); ?>
          <article class="journal-card">
            <a href="<?php the_permalink(); ?>">
              <div class="journal-media"><?php if ( has_post_thumbnail() ) : the_post_thumbnail( 'make-journal', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); else : ?><?php echo make_editorial_placeholder_html( get_the_ID() ); ?><?php endif; ?></div>
              <div class="journal-body">
                <span class="journal-meta"><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span>
                <h3 class="journal-title"><?php the_title(); ?></h3>
                <p class="journal-excerpt"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 18 ) ); ?></p>
              </div>
            </a>
          </article>
        <?php endwhile; wp_reset_postdata(); ?>
      </div>
    <?php else : ?>
      <div class="journal-empty">
        <p><?php echo esc_html( make_t( 'Cuando publiques artículos aparecerán aquí automáticamente.', 'When you publish articles they will appear here automatically.' ) ); ?></p>
      </div>
    <?php endif; ?>
  </div>
</section>

<section class="shop-cta">
  <div class="container">
    <div class="shop-cta-inner">
      <span><?php echo esc_html( $site_name ); ?></span>
      <h2><?php echo esc_html( make_t( 'Encuentra algo que te apetezca empezar hoy.', 'Find something you feel like starting today.' ) ); ?></h2>
      <a class="button button-primary" href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Ir a la tienda', 'Go to the shop' ) ); ?> →</a>
    </div>
  </div>
</section>

<?php get_footer(); ?>
