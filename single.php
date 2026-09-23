<?php
get_header();

if ( have_posts() ) :
    while ( have_posts() ) :
        the_post();
        $post_id    = get_the_ID();
        $categories = get_the_category();
        $kicker     = ! empty( $categories ) ? $categories[0]->name : make_t( 'Inspiración', 'Inspiration' );
        $related    = make_related_articles( $post_id, 3 );
        $craft      = function_exists( 'make_article_craft' ) ? make_article_craft( $post_id ) : 'cross-stitch';
        $crafts     = function_exists( 'make_editorial_craft_config' ) ? make_editorial_craft_config() : array();
        $craft_name = isset( $crafts[ $craft ][ make_current_language() ]['label'] )
            ? (string) $crafts[ $craft ][ make_current_language() ]['label']
            : make_t( 'Técnica', 'Technique' );
        $craft_url  = function_exists( 'make_article_craft_url' ) ? make_article_craft_url( $post_id ) : make_journal_url();
?>
<article class="article-page">
  <header class="article-header narrow">
    <?php if ( function_exists( 'make_editorial_breadcrumbs_html' ) ) : ?>
      <?php echo wp_kses_post( make_editorial_breadcrumbs_html( $post_id ) ); ?>
    <?php endif; ?>
    <a class="article-back" href="<?php echo esc_url( $craft_url ); ?>">← <?php echo esc_html( $craft_name ); ?></a>
    <span class="section-kicker"><?php echo esc_html( $craft_name . ' · ' . $kicker ); ?></span>
    <h1 class="article-title"><?php the_title(); ?></h1>
    <p class="article-deck"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 28 ) ); ?></p>
    <div class="article-meta">
      <span><?php echo esc_html( make_reading_time( $post_id ) ); ?></span>
    </div>
  </header>

  <?php if ( has_post_thumbnail() ) : ?>
    <div class="article-featured"><?php the_post_thumbnail( 'full', array( 'loading' => 'eager', 'fetchpriority' => 'high', 'decoding' => 'async' ) ); ?></div>
  <?php else : ?>
    <div class="article-featured article-featured--placeholder"><?php echo make_editorial_placeholder_html( $post_id ); ?></div>
  <?php endif; ?>

  <div class="entry-content narrow"><?php the_content(); ?></div>

  <?php if ( function_exists( 'make_article_commerce_collections_html' ) ) : ?>
    <?php echo wp_kses_post( make_article_commerce_collections_html( $post_id ) ); ?>
  <?php endif; ?>

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
      <h2><?php echo esc_html( sprintf( make_t( 'Encuentra tu próximo proyecto de %s', 'Find your next %s project' ), $craft_name ) ); ?></h2>
      <p><?php echo esc_html( make_t( 'Explora los patrones disponibles y convierte lo que acabas de aprender en un proyecto real.', 'Explore available patterns and turn what you just learned into a real project.' ) ); ?></p>
      <a class="button button-primary" href="<?php echo esc_url( function_exists( 'make_article_shop_url' ) ? make_article_shop_url( $post_id ) : make_shop_url() ); ?>"><?php echo esc_html( make_t( 'Ver patrones', 'View patterns' ) ); ?> →</a>
    </div>
  </footer>
</article>

<?php
    endwhile;
endif;

get_footer();