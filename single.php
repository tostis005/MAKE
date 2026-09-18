<?php
get_header();

if ( have_posts() ) :
    while ( have_posts() ) :
        the_post();
        $categories = get_the_category();
        $kicker = ! empty( $categories ) ? $categories[0]->name : make_t( 'Inspiración', 'Inspiration' );
        $related = make_related_articles( get_the_ID(), 3 );
?>
<article class="article-page">
  <header class="article-header narrow">
    <a class="article-back" href="<?php echo esc_url( make_journal_url() ); ?>">← <?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></a>
    <span class="section-kicker"><?php echo esc_html( $kicker ); ?></span>
    <h1 class="article-title"><?php the_title(); ?></h1>
    <p class="article-deck"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 28 ) ); ?></p>
    <div class="article-meta">
      <span><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span>
    </div>
  </header>

  <?php if ( has_post_thumbnail() ) : ?>
    <div class="article-featured"><?php the_post_thumbnail( 'full', array( 'loading' => 'eager', 'fetchpriority' => 'high', 'decoding' => 'async' ) ); ?></div>
  <?php else : ?>
    <div class="article-featured article-featured--placeholder"><?php echo make_editorial_placeholder_html( get_the_ID() ); ?></div>
  <?php endif; ?>

  <div class="entry-content narrow"><?php the_content(); ?></div>

  <?php if ( ! empty( $related ) ) : ?>
    <section class="article-related narrow" aria-labelledby="related-articles-title">
      <header class="article-related-head">
        <span class="section-kicker"><?php echo esc_html( make_t( 'Sigue leyendo', 'Keep reading' ) ); ?></span>
        <h2 id="related-articles-title"><?php echo esc_html( make_t( 'Artículos relacionados', 'Related articles' ) ); ?></h2>
      </header>
      <div class="article-related-grid">
        <?php foreach ( $related as $related_id ) : setup_postdata( get_post( $related_id ) ); $related_cats = get_the_category( $related_id ); ?>
          <article class="related-card">
            <a href="<?php echo esc_url( get_permalink( $related_id ) ); ?>">
              <div class="related-card-media">
                <?php if ( has_post_thumbnail( $related_id ) ) : ?>
                  <?php echo get_the_post_thumbnail( $related_id, 'make-journal', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); ?>
                <?php else : ?>
                  <?php echo make_editorial_placeholder_html( $related_id ); ?>
                <?php endif; ?>
              </div>
              <div class="related-card-body">
                <span class="section-kicker"><?php echo esc_html( ! empty( $related_cats ) ? $related_cats[0]->name : make_t( 'Artículo', 'Article' ) ); ?></span>
                <h3><?php echo esc_html( get_the_title( $related_id ) ); ?></h3>
                <span class="related-card-meta"><?php echo esc_html( make_reading_time( $related_id ) ); ?></span>
              </div>
            </a>
          </article>
        <?php endforeach; wp_reset_postdata(); ?>
      </div>
    </section>
  <?php endif; ?>

  <footer class="article-footer narrow">
    <div class="article-footer-card">
      <span class="section-kicker"><?php echo esc_html( make_t( 'Sigue creando', 'Keep making' ) ); ?></span>
      <h2><?php echo esc_html( make_t( '¿Te apetece empezar un proyecto?', 'Feel like starting a project?' ) ); ?></h2>
      <p><?php echo esc_html( make_t( 'Explora la tienda y encuentra un patrón para llevar estas ideas a las manos.', 'Explore the shop and find a pattern to put these ideas into practice.' ) ); ?></p>
      <a class="button button-primary" href="<?php echo esc_url( make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Ver patrones', 'View patterns' ) ); ?> →</a>
    </div>
  </footer>
</article>

<?php
    endwhile;
endif;

get_footer();
