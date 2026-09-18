<?php
get_header();

$language     = make_current_language();
$theme_id     = make_current_stitch_theme();
$theme_config = make_stitch_theme_config();
$theme_data   = $theme_id && isset( $theme_config[ $theme_id ] ) ? $theme_config[ $theme_id ][ $language ] : null;
$total        = (int) $GLOBALS['wp_query']->found_posts;
$sections     = make_editorial_sections( $language );
$themes       = make_stitch_theme_cards( $language );
?>
<section class="editorial-hero editorial-hero--journal">
  <div class="container">
    <div class="editorial-hero-inner">
      <?php if ( $theme_data ) : ?>
        <a class="journal-back-link" href="<?php echo esc_url( make_journal_url( $language ) ); ?>">← <?php echo esc_html( make_t( 'Todos los artículos', 'All articles' ) ); ?></a>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Explorar por temática', 'Browse by theme' ) ); ?></span>
        <h1><?php echo esc_html( $theme_data['label'] ); ?></h1>
        <p><?php echo esc_html( $theme_data['description'] ); ?></p>
      <?php else : ?>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></span>
        <h1><?php echo esc_html( make_t( 'Ideas, guías y proyectos para disfrutar más creando.', 'Ideas, guides and projects for enjoying making more.' ) ); ?></h1>
        <p><?php echo esc_html( make_t( 'Guías claras para aprender punto de cruz, elegir mejores patrones y encontrar ideas que de verdad apetezca bordar.', 'Clear guides for learning cross stitch, choosing better patterns and finding projects you genuinely want to stitch.' ) ); ?></p>
      <?php endif; ?>
      <?php if ( $total > 0 ) : ?>
        <div class="journal-summary"><?php echo esc_html( sprintf( make_t( '%d artículos', '%d articles' ), $total ) ); ?></div>
      <?php endif; ?>
    </div>
  </div>
</section>

<?php if ( ! empty( $themes ) ) : ?>
<section class="journal-themes" aria-label="<?php echo esc_attr( make_t( 'Artículos por temática', 'Articles by theme' ) ); ?>">
  <div class="container">
    <header class="journal-themes-head">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Por temática', 'By theme' ) ); ?></span>
        <h2><?php echo esc_html( make_t( 'Encuentra ideas por lo que te apetece bordar.', 'Find ideas by what you feel like stitching.' ) ); ?></h2>
      </div>
      <p><?php echo esc_html( make_t( 'Cada temática tiene su propio universo visual inspirado en la cuadrícula y las puntadas del punto de cruz.', 'Each theme has its own visual world inspired by cross-stitch grids and stitches.' ) ); ?></p>
    </header>

    <div class="journal-theme-grid">
      <?php foreach ( $themes as $theme ) : ?>
        <a class="journal-theme-card <?php echo $theme_id === $theme['id'] ? 'is-active' : ''; ?>" href="<?php echo esc_url( $theme['url'] ); ?>">
          <span class="journal-theme-media">
            <?php echo make_stitch_theme_art_html( $theme['id'], 'journal-theme-art' ); ?>
          </span>
          <span class="journal-theme-copy">
            <strong><?php echo esc_html( $theme['label'] ); ?></strong>
            <small><?php echo esc_html( $theme['description'] ); ?></small>
            <i aria-hidden="true">→</i>
          </span>
        </a>
      <?php endforeach; ?>
    </div>
  </div>
</section>
<?php endif; ?>

<?php if ( ! $theme_id && ! empty( $sections ) ) : ?>
<section class="journal-paths" aria-label="<?php echo esc_attr( make_t( 'Explorar artículos', 'Explore articles' ) ); ?>">
  <div class="container">
    <div class="journal-paths-grid">
      <?php foreach ( $sections as $section ) : ?>
        <a class="journal-path-card journal-path-card--<?php echo esc_attr( $section['id'] ); ?>" href="<?php echo esc_url( $section['url'] ); ?>">
          <span class="section-kicker"><?php echo esc_html( $section['label'] ); ?></span>
          <strong><?php echo esc_html( sprintf( make_t( '%d artículos', '%d articles' ), $section['count'] ) ); ?></strong>
          <p><?php echo esc_html( $section['description'] ); ?></p>
          <span class="journal-path-arrow" aria-hidden="true">→</span>
        </a>
      <?php endforeach; ?>
    </div>
  </div>
</section>
<?php endif; ?>

<section class="archive-wrap editorial-archive editorial-archive--journal">
  <div class="container">
    <?php if ( have_posts() ) : ?>
      <div class="content-grid journal-archive-grid">
        <?php while ( have_posts() ) : the_post(); $cats = get_the_category(); ?>
          <article class="post-card">
            <a href="<?php the_permalink(); ?>">
              <div class="post-card-media">
                <?php if ( has_post_thumbnail() ) : ?>
                  <?php the_post_thumbnail( 'make-journal', array( 'loading'=>'lazy', 'decoding'=>'async' ) ); ?>
                <?php else : ?>
                  <?php echo make_editorial_placeholder_html( get_the_ID() ); ?>
                <?php endif; ?>
              </div>
              <div class="post-card-body">
                <span class="section-kicker"><?php echo esc_html( ! empty( $cats ) ? $cats[0]->name : make_t( 'Artículo', 'Article' ) ); ?></span>
                <h2><?php the_title(); ?></h2>
                <p><?php echo esc_html( wp_trim_words( get_the_excerpt(), 24 ) ); ?></p>
                <div class="post-card-meta">
                  <span><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span>
                  <span class="post-card-arrow" aria-hidden="true">→</span>
                </div>
              </div>
            </a>
          </article>
        <?php endwhile; ?>
      </div>

      <?php $pagination = make_journal_pagination_html( $GLOBALS['wp_query'], $language, $theme_id ); ?>
      <?php if ( $pagination ) : ?>
        <nav class="pagination journal-pagination" aria-label="<?php echo esc_attr( make_t( 'Paginación de artículos', 'Article pagination' ) ); ?>">
          <?php echo wp_kses_post( $pagination ); ?>
        </nav>
      <?php endif; ?>
    <?php else : ?>
      <div class="archive-empty">
        <span class="archive-empty-mark" aria-hidden="true">× × ×</span>
        <h2><?php echo esc_html( make_t( 'Todavía no hay artículos publicados en esta temática.', 'There are no published articles in this theme yet.' ) ); ?></h2>
        <p><?php echo esc_html( make_t( 'Puedes volver al Journal para seguir explorando.', 'You can return to the Journal to keep exploring.' ) ); ?></p>
        <a class="button button-secondary" href="<?php echo esc_url( make_journal_url( $language ) ); ?>"><?php echo esc_html( make_t( 'Ver todos los artículos', 'View all articles' ) ); ?></a>
      </div>
    <?php endif; ?>
  </div>
</section>

<?php get_footer(); ?>
