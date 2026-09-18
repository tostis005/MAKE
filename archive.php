<?php
get_header();
$title = make_archive_title();
$description = get_the_archive_description();
if ( ! $description ) { $description = make_editorial_archive_description(); }
?>
<section class="editorial-hero editorial-hero--compact">
  <div class="container">
    <div class="editorial-hero-inner">
      <span class="section-kicker"><?php echo esc_html( make_t( 'Archivo', 'Archive' ) ); ?></span>
      <h1><?php echo esc_html( $title ); ?></h1>
      <?php if ( $description ) : ?><div class="archive-description"><?php echo wp_kses_post( $description ); ?></div><?php endif; ?>
    </div>
  </div>
</section>

<section class="archive-wrap editorial-archive">
  <div class="container">
    <div class="content-grid">
      <?php if ( have_posts() ) : ?>
        <?php while ( have_posts() ) : the_post(); $cats = get_the_category(); ?>
          <article class="post-card">
            <a href="<?php the_permalink(); ?>">
              <div class="post-card-media">
                <?php if ( has_post_thumbnail() ) : the_post_thumbnail( 'make-journal', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); else : ?><?php echo make_editorial_placeholder_html( get_the_ID() ); ?><?php endif; ?>
              </div>
              <div class="post-card-body">
                <span class="section-kicker"><?php echo esc_html( ! empty( $cats ) ? $cats[0]->name : make_t( 'Artículo', 'Article' ) ); ?></span>
                <h2><?php the_title(); ?></h2>
                <p><?php echo esc_html( wp_trim_words( get_the_excerpt(), 22 ) ); ?></p>
                <div class="post-card-meta"><span><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span></div>
              </div>
            </a>
          </article>
        <?php endwhile; ?>
      <?php else : ?>
        <div class="archive-empty"><h2><?php echo esc_html( make_t( 'No hay contenido aquí todavía.', 'There is no content here yet.' ) ); ?></h2></div>
      <?php endif; ?>
    </div>
    <div class="pagination"><?php the_posts_pagination(); ?></div>
  </div>
</section>
<?php get_footer(); ?>
