<?php
get_header();

if ( have_posts() ) :
    while ( have_posts() ) :
        the_post();
        $categories = get_the_category();
        $kicker = ! empty( $categories ) ? $categories[0]->name : make_t( 'Inspiración', 'Inspiration' );
?>
<article class="article-page">
  <header class="article-header narrow">
    <a class="article-back" href="<?php echo esc_url( make_journal_url() ); ?>">← <?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></a>
    <span class="section-kicker"><?php echo esc_html( $kicker ); ?></span>
    <h1 class="article-title"><?php the_title(); ?></h1>
    <p class="article-deck"><?php echo esc_html( wp_trim_words( get_the_excerpt(), 28 ) ); ?></p>
    <div class="article-meta">
      <span><?php echo esc_html( get_the_date() ); ?></span>
      <span aria-hidden="true">·</span>
      <span><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span>
    </div>
  </header>

  <?php if ( has_post_thumbnail() ) : ?>
    <div class="article-featured"><?php the_post_thumbnail( 'full', array( 'loading' => 'eager', 'fetchpriority' => 'high', 'decoding' => 'async' ) ); ?></div>
  <?php endif; ?>

  <div class="entry-content narrow"><?php the_content(); ?></div>

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
