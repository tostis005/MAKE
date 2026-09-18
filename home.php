<?php
get_header();

$language = make_current_language();
$total    = (int) $GLOBALS['wp_query']->found_posts;
$sections = make_editorial_sections( $language );
?>
<section class="editorial-hero editorial-hero--journal">
  <div class="container">
    <div class="editorial-hero-inner">
      <span class="section-kicker"><?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></span>
      <h1><?php echo esc_html( make_t( 'Ideas, guías y proyectos para disfrutar más creando.', 'Ideas, guides and projects for enjoying making more.' ) ); ?></h1>
      <p><?php echo esc_html( make_t( 'Guías claras para aprender punto de cruz, elegir mejores patrones y encontrar ideas que de verdad apetezca bordar.', 'Clear guides for learning cross stitch, choosing better patterns and finding projects you genuinely want to stitch.' ) ); ?></p>
      <?php if ( $total > 0 ) : ?>
        <div class="journal-summary"><?php echo esc_html( sprintf( make_t( '%d artículos', '%d articles' ), $total ) ); ?></div>
      <?php endif; ?>
    </div>
  </div>
</section>

<?php if ( ! empty( $sections ) ) : ?>
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
                  <?php the_post_thumbnail( 'make-journal', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); ?>
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

      <?php
      $current_page = max( 1, (int) get_query_var( 'paged' ) );
      if ( '' !== (string) get_option( 'permalink_structure', '' ) ) {
          $page_base = trailingslashit( make_journal_url( $language ) ) . 'page/%#%/';
      } else {
          $page_base = add_query_arg(
              array(
                  'make_journal' => '1',
                  'make_lang'    => $language,
                  'paged'        => '%#%',
              ),
              home_url( '/' )
          );
          $page_base = str_replace( '%25%23%25', '%#%', $page_base );
      }
      $pagination = paginate_links(
          array(
              'base'      => $page_base,
              'format'    => '',
              'current'   => $current_page,
              'total'     => max( 1, (int) $GLOBALS['wp_query']->max_num_pages ),
              'type'      => 'list',
              'prev_text' => make_t( '← Anterior', '← Previous' ),
              'next_text' => make_t( 'Siguiente →', 'Next →' ),
          )
      );
      ?>
      <?php if ( $pagination ) : ?>
        <nav class="pagination journal-pagination" aria-label="<?php echo esc_attr( make_t( 'Paginación de artículos', 'Article pagination' ) ); ?>">
          <?php echo wp_kses_post( $pagination ); ?>
        </nav>
      <?php endif; ?>
    <?php else : ?>
      <div class="archive-empty">
        <span class="archive-empty-mark" aria-hidden="true">× × ×</span>
        <h2><?php echo esc_html( make_t( 'Todavía no hay artículos publicados.', 'No articles have been published yet.' ) ); ?></h2>
        <p><?php echo esc_html( make_t( 'En cuanto publiquemos el siguiente aparecerá aquí automáticamente.', 'The next published article will appear here automatically.' ) ); ?></p>
      </div>
    <?php endif; ?>
  </div>
</section>

<?php get_footer(); ?>
