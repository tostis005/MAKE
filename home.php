<?php
get_header();

$language      = make_current_language();
$craft_id      = function_exists( 'make_current_editorial_craft' ) ? make_current_editorial_craft() : '';
$craft_section = function_exists( 'make_current_editorial_craft_section' ) ? make_current_editorial_craft_section() : '';
$craft_config  = function_exists( 'make_editorial_craft_config' ) ? make_editorial_craft_config() : array();
$craft_data    = $craft_id && isset( $craft_config[ $craft_id ][ $language ] ) ? $craft_config[ $craft_id ][ $language ] : null;
$theme_id      = make_current_stitch_theme();
$theme_config  = make_stitch_theme_config();
$theme_data    = $theme_id && isset( $theme_config[ $theme_id ] ) ? $theme_config[ $theme_id ][ $language ] : null;
$total         = (int) $GLOBALS['wp_query']->found_posts;
$crafts        = function_exists( 'make_editorial_craft_cards' ) ? make_editorial_craft_cards( $language, true ) : array();
$sections      = $craft_id && function_exists( 'make_editorial_sections_for_craft' )
    ? make_editorial_sections_for_craft( $craft_id, $language )
    : make_editorial_sections( $language );
$themes        = ( 'cross-stitch' === $craft_id || '' !== $theme_id ) ? make_stitch_theme_cards( $language ) : array();
$section_cfg   = make_editorial_section_config();
$section_data  = $craft_section && isset( $section_cfg[ $craft_section ][ $language ] ) ? $section_cfg[ $craft_section ][ $language ] : null;
?>
<section class="editorial-hero editorial-hero--journal">
  <div class="container">
    <?php if ( function_exists( 'make_editorial_breadcrumbs_html' ) ) : ?>
      <?php echo wp_kses_post( make_editorial_breadcrumbs_html() ); ?>
    <?php endif; ?>

    <div class="editorial-hero-inner">
      <?php if ( $theme_data ) : ?>
        <a class="journal-back-link" href="<?php echo esc_url( make_editorial_craft_url( 'cross-stitch', $language ) ); ?>">← <?php echo esc_html( make_t( 'Punto de cruz', 'Cross Stitch' ) ); ?></a>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Punto de cruz · temática', 'Cross Stitch · theme' ) ); ?></span>
        <h1><?php echo esc_html( $theme_data['label'] ); ?></h1>
        <p><?php echo esc_html( $theme_data['description'] ); ?></p>
      <?php elseif ( $craft_data ) : ?>
        <a class="journal-back-link" href="<?php echo esc_url( make_journal_url( $language ) ); ?>">← <?php echo esc_html( make_t( 'Todas las técnicas', 'All techniques' ) ); ?></a>
        <span class="section-kicker"><?php echo esc_html( $section_data ? $section_data['label'] : make_t( 'Aprende por técnica', 'Learn by technique' ) ); ?></span>
        <h1><?php echo esc_html( $section_data ? $craft_data['label'] . ' · ' . $section_data['label'] : $craft_data['label'] ); ?></h1>
        <p><?php echo esc_html( $section_data ? $section_data['description'] : $craft_data['description'] ); ?></p>
      <?php else : ?>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Aprender y crear', 'Learn & make' ) ); ?></span>
        <h1><?php echo esc_html( make_t( 'Guías para convertir una cuadrícula en algo hecho a mano.', 'Guides for turning a grid into something handmade.' ) ); ?></h1>
        <p><?php echo esc_html( make_t( 'Explora punto de cruz, C2C crochet, tapestry crochet y latch hook. Aprende la técnica, resuelve dudas y encuentra patrones para llevarla a la práctica.', 'Explore cross stitch, C2C crochet, tapestry crochet and latch hook. Learn the technique, solve problems and find patterns to put it into practice.' ) ); ?></p>
      <?php endif; ?>

      <?php if ( $total > 0 ) : ?>
        <div class="journal-summary"><?php echo esc_html( sprintf( make_t( '%d artículos', '%d articles' ), $total ) ); ?></div>
      <?php endif; ?>
    </div>
  </div>
</section>

<?php if ( ! $craft_id && ! $theme_id && ! empty( $crafts ) ) : ?>
<section class="journal-crafts" aria-label="<?php echo esc_attr( make_t( 'Explorar por técnica', 'Browse by technique' ) ); ?>">
  <div class="container">
    <header class="journal-crafts-head">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Elige una técnica', 'Choose a technique' ) ); ?></span>
        <h2><?php echo esc_html( make_t( 'Un mismo lenguaje de cuadrícula, distintas formas de crear.', 'One grid language, different ways to make.' ) ); ?></h2>
      </div>
      <p><?php echo esc_html( make_t( 'Cada técnica tiene sus propias guías, materiales, problemas frecuentes y patrones relacionados.', 'Each technique has its own guides, materials, common problems and related patterns.' ) ); ?></p>
    </header>

    <div class="journal-craft-grid">
      <?php foreach ( $crafts as $craft ) : ?>
        <?php if ( $craft['has_content'] ) : ?>
          <a class="journal-craft-card journal-craft-card--<?php echo esc_attr( $craft['id'] ); ?>" href="<?php echo esc_url( $craft['url'] ); ?>">
        <?php else : ?>
          <div class="journal-craft-card journal-craft-card--<?php echo esc_attr( $craft['id'] ); ?> is-coming-soon">
        <?php endif; ?>
            <span class="journal-craft-art"><?php echo make_editorial_craft_art_html( $craft['id'] ); ?></span>
            <span class="journal-craft-copy">
              <strong><?php echo esc_html( $craft['label'] ); ?></strong>
              <small><?php echo esc_html( $craft['description'] ); ?></small>
              <?php if ( $craft['has_content'] ) : ?>
                <i aria-hidden="true">→</i>
              <?php else : ?>
                <em><?php echo esc_html( make_t( 'Contenido en preparación', 'Content in preparation' ) ); ?></em>
              <?php endif; ?>
            </span>
        <?php echo $craft['has_content'] ? '</a>' : '</div>'; ?>
      <?php endforeach; ?>
    </div>
  </div>
</section>
<?php endif; ?>

<?php if ( $craft_id && ! $theme_id && ! empty( $crafts ) ) : ?>
<section class="journal-craft-tabs">
  <div class="container">
    <div class="journal-craft-tabs-inner" aria-label="<?php echo esc_attr( make_t( 'Cambiar técnica', 'Change technique' ) ); ?>">
      <?php foreach ( $crafts as $craft ) : ?>
        <?php if ( $craft['has_content'] ) : ?>
          <a class="<?php echo $craft_id === $craft['id'] ? 'is-active' : ''; ?>" href="<?php echo esc_url( $craft['url'] ); ?>"><?php echo esc_html( $craft['label'] ); ?></a>
        <?php else : ?>
          <span class="is-disabled"><?php echo esc_html( $craft['label'] ); ?></span>
        <?php endif; ?>
      <?php endforeach; ?>
    </div>
  </div>
</section>
<?php endif; ?>

<?php if ( ! empty( $themes ) && ! $craft_section ) : ?>
<section class="journal-themes" aria-label="<?php echo esc_attr( make_t( 'Artículos de punto de cruz por temática', 'Cross stitch articles by theme' ) ); ?>">
  <div class="container">
    <header class="journal-themes-head">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Punto de cruz por temática', 'Cross Stitch by theme' ) ); ?></span>
        <h2><?php echo esc_html( make_t( 'Encuentra ideas por lo que te apetece bordar.', 'Find ideas by what you feel like stitching.' ) ); ?></h2>
      </div>
      <p><?php echo esc_html( make_t( 'Flores, animales, pop art, diseños retro y más, siempre dentro de punto de cruz.', 'Florals, animals, pop art, retro designs and more, always within Cross Stitch.' ) ); ?></p>
    </header>

    <div class="journal-theme-grid">
      <?php foreach ( $themes as $theme ) : ?>
        <a class="journal-theme-card <?php echo $theme_id === $theme['id'] ? 'is-active' : ''; ?>" href="<?php echo esc_url( $theme['url'] ); ?>">
          <span class="journal-theme-media"><?php echo make_stitch_theme_art_html( $theme['id'], 'journal-theme-art' ); ?></span>
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

<?php if ( $craft_id && ! $theme_id && ! $craft_section && ! empty( $sections ) ) : ?>
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

      <?php $pagination = make_journal_pagination_html( $GLOBALS['wp_query'], $language, $theme_id, $craft_id, $craft_section ); ?>
      <?php if ( $pagination ) : ?>
        <nav class="pagination journal-pagination" aria-label="<?php echo esc_attr( make_t( 'Paginación de artículos', 'Article pagination' ) ); ?>">
          <?php echo wp_kses_post( $pagination ); ?>
        </nav>
      <?php endif; ?>
    <?php else : ?>
      <div class="archive-empty">
        <span class="archive-empty-mark" aria-hidden="true">× × ×</span>
        <h2><?php echo esc_html( make_t( 'Todavía no hay artículos publicados aquí.', 'There are no published articles here yet.' ) ); ?></h2>
        <p><?php echo esc_html( make_t( 'Vuelve a la portada de artículos para seguir explorando técnicas y guías.', 'Return to the articles hub to explore other techniques and guides.' ) ); ?></p>
        <a class="button button-secondary" href="<?php echo esc_url( make_journal_url( $language ) ); ?>"><?php echo esc_html( make_t( 'Ver todos los artículos', 'View all articles' ) ); ?></a>
      </div>
    <?php endif; ?>
  </div>
</section>

<?php get_footer(); ?>