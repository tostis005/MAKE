<?php get_header(); ?>
<section class="search-wrap">
  <div class="container">
    <header class="search-header">
      <span class="section-kicker"><?php echo esc_html( make_t( 'Resultados', 'Results' ) ); ?></span>
      <h1><?php printf( esc_html( make_t( 'Resultados para “%s”', 'Results for “%s”' ) ), esc_html( get_search_query() ) ); ?></h1>
      <p><?php echo esc_html( make_t( 'Mostramos patrones y artículos en tu idioma siempre que estén disponibles.', 'We show patterns and articles in your language whenever available.' ) ); ?></p>
    </header>
    <div class="content-grid search-results-grid">
      <?php if ( have_posts() ) : while ( have_posts() ) : the_post(); $is_product = 'product' === get_post_type(); ?>
        <article class="post-card">
          <a href="<?php the_permalink(); ?>">
            <div class="post-card-media">
              <?php if ( has_post_thumbnail() ) : ?>
                <?php the_post_thumbnail( 'make-journal', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); ?>
              <?php elseif ( ! $is_product ) : ?>
                <?php echo make_editorial_placeholder_html( get_the_ID() ); ?>
              <?php else : ?>
                <span class="product-placeholder" aria-hidden="true"><span class="mini-grid"><?php for ( $i = 0; $i < 36; $i++ ) : ?><i></i><?php endfor; ?></span></span>
              <?php endif; ?>
            </div>
            <div class="post-card-body">
              <span class="section-kicker"><?php echo esc_html( $is_product ? make_t( 'Patrón', 'Pattern' ) : make_t( 'Artículo', 'Article' ) ); ?></span>
              <h2><?php the_title(); ?></h2>
              <p><?php echo esc_html( wp_trim_words( get_the_excerpt(), 20 ) ); ?></p>
              <div class="post-card-meta">
                <span><?php echo esc_html( $is_product ? make_t( 'Patrón digital', 'Digital pattern' ) : make_reading_time( get_the_ID() ) ); ?></span>
                <span class="post-card-arrow" aria-hidden="true">→</span>
              </div>
            </div>
          </a>
        </article>
      <?php endwhile; else : ?>
        <div class="archive-empty">
          <h2><?php echo esc_html( make_t( 'No hemos encontrado nada con esa búsqueda.', 'We could not find anything for that search.' ) ); ?></h2>
          <p><?php echo esc_html( make_t( 'Prueba con un tema, una técnica o un tipo de patrón más general.', 'Try a broader theme, technique or pattern type.' ) ); ?></p>
        </div>
      <?php endif; ?>
    </div>
    <div class="pagination"><?php the_posts_pagination(); ?></div>
  </div>
</section>
<?php get_footer(); ?>
