<?php get_header(); if ( have_posts() ) : while ( have_posts() ) : the_post(); ?>
<article><header class="article-header narrow"><span class="section-kicker"><?php echo esc_html( make_reading_time( get_the_ID() ) ); ?></span><h1 class="article-title"><?php the_title(); ?></h1><div class="article-meta"><?php echo esc_html( get_the_date() ); ?></div></header><?php if ( has_post_thumbnail() ) : ?><div class="article-featured"><?php the_post_thumbnail( 'full' ); ?></div><?php endif; ?><div class="entry-content narrow"><?php the_content(); ?></div></article>
<?php endwhile; endif; get_footer(); ?>
