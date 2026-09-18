<?php
get_header();
?>
<section class="editorial-hero">
  <div class="container">
    <div class="editorial-hero-inner">
      <span class="section-kicker"><?php echo esc_html( make_t( 'Últimos artículos', 'Latest articles' ) ); ?></span>
      <h1><?php echo esc_html( make_t( 'Ideas, guías y proyectos para disfrutar más creando.', 'Ideas, guides and projects for enjoying making more.' ) ); ?></h1>
      <p><?php echo esc_html( make_t( 'Contenido práctico y visual alrededor de los patrones, las técnicas y el placer de hacer algo con tus propias manos.', 'Practical, visual content around patterns, techniques and the pleasure of making something with your own hands.' ) ); ?></p>
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
                <?php if ( has_post_thumbnail() ) : the_post_thumbnail( 'make-journal', array( 'loading' => 'lazy', 'decoding' => 'async' ) ); else : ?><span class="post-placeholder" aria-hidden="true">✦</span><?php endif; ?>
              </div>
              <div class="post-card-body">
                <span class="section-kicker"><?php echo esc_html( ! empty( $cats ) ? $cats[0]->name : make_t( 'Artículo', 'Article' ) ); ?></span>
                <h2><?php the_title(); ?></h2>
                <p><?php echo esc_html( wp_trim_words( get_the_excerpt(), 22 ) ); ?></p>
                <div class="post-card-meta"><span><?php echo esc_html( get_the_date() ); ?></span><span><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span></div>
              </div>
            </a>
          </article>
        <?php endwhile; ?>
      <?php else : ?>
        <div class="archive-empty">
          <h2><?php echo esc_html( make_t( 'Todavía no hay artículos publicados.', 'No articles have been published yet.' ) ); ?></h2>
          <p><?php echo esc_html( make_t( 'En cuanto publiques el primero aparecerá aquí automáticamente.', 'As soon as you publish the first one it will appear here automatically.' ) ); ?></p>
        </div>
      <?php endif; ?>
    </div>
    <div class="pagination"><?php the_posts_pagination(); ?></div>
  </div>
</section>
<?php get_footer(); ?>
