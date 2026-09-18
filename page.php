<?php get_header(); if ( have_posts() ) : while ( have_posts() ) : the_post(); ?>
<section class="page-wrap"><div class="narrow"><h1 class="page-title"><?php the_title(); ?></h1><div class="entry-content"><?php the_content(); ?></div></div></section>
<?php endwhile; endif; get_footer(); ?>
