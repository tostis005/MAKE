<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

get_header();

$filters = make_pdf_library_filter_config();
$active_filters = make_pdf_library_active_filters();
$products = make_pdf_library_products_query();
?>
<section class="shop-hero shop-hero--store drielo-pdf-hero">
  <div class="container">
    <div class="shop-hero-inner shop-hero-inner--stacked">
      <div>
        <span class="section-kicker"><?php echo esc_html( make_t( 'Área privada', 'Private area' ) ); ?></span>
        <h1>PDFs</h1>
      </div>
      <p><?php echo esc_html( make_t( 'Biblioteca de validación de los PDFs descargables de WooCommerce.', 'Validation library for WooCommerce downloadable PDFs.' ) ); ?></p>
    </div>
  </div>
</section>

<section class="shop-main drielo-pdf-main">
  <div class="container">
    <form class="drielo-pdf-filters" method="get" action="<?php echo esc_url( home_url( '/pdfs/' ) ); ?>">
      <div class="drielo-pdf-filter-grid">
        <?php foreach ( $filters as $query_key => $config ) :
            $taxonomy = (string) $config['taxonomy'];
            if ( ! taxonomy_exists( $taxonomy ) ) { continue; }

            $terms = get_terms(
                array(
                    'taxonomy'   => $taxonomy,
                    'hide_empty' => true,
                    'orderby'    => 'name',
                    'order'      => 'ASC',
                )
            );
            if ( is_wp_error( $terms ) || empty( $terms ) ) { continue; }

            $selected = $active_filters[ $query_key ] ?? '';
            ?>
            <label class="drielo-pdf-filter">
              <span><?php echo esc_html( (string) $config['label'] ); ?></span>
              <select name="<?php echo esc_attr( $query_key ); ?>">
                <option value=""><?php echo esc_html( make_t( 'Todos', 'All' ) ); ?></option>
                <?php foreach ( $terms as $term ) :
                    if ( ! $term instanceof WP_Term ) { continue; }
                    ?>
                    <option value="<?php echo esc_attr( $term->slug ); ?>" <?php selected( $selected, $term->slug ); ?>>
                      <?php echo esc_html( make_pdf_library_term_label( $term, $taxonomy ) ); ?>
                    </option>
                <?php endforeach; ?>
              </select>
            </label>
        <?php endforeach; ?>
      </div>

      <div class="drielo-pdf-filter-actions">
        <button type="submit"><?php echo esc_html( make_t( 'Aplicar filtros', 'Apply filters' ) ); ?></button>
        <?php if ( ! empty( $active_filters ) ) : ?>
          <a href="<?php echo esc_url( home_url( '/pdfs/' ) ); ?>"><?php echo esc_html( make_t( 'Limpiar', 'Clear' ) ); ?></a>
        <?php endif; ?>
        <span class="drielo-pdf-count">
          <?php echo esc_html( sprintf( make_t( '%d productos', '%d products' ), (int) $products->found_posts ) ); ?>
        </span>
      </div>
    </form>

    <?php if ( $products->have_posts() ) : ?>
      <div class="drielo-pdf-grid">
        <?php while ( $products->have_posts() ) :
            $products->the_post();

            $product_id = get_the_ID();
            $product = wc_get_product( $product_id );
            if ( ! $product instanceof WC_Product ) { continue; }

            $pdf = make_pdf_library_pdf_record( $product );
            $technique = make_pdf_library_product_technique_label( $product_id );
            $image_id = (int) get_post_thumbnail_id( $product_id );
            $code = function_exists( 'make_product_reference_code' ) ? make_product_reference_code( $product_id ) : '';
            $aria = trim( sprintf( '%s %s', $code, $technique ) );
            ?>

            <?php if ( null !== $pdf ) : ?>
              <a class="drielo-pdf-card" href="<?php echo esc_url( make_pdf_library_download_url( $product_id ) ); ?>" aria-label="<?php echo esc_attr( $aria ); ?>">
            <?php else : ?>
              <article class="drielo-pdf-card drielo-pdf-card--missing" aria-label="<?php echo esc_attr( $aria ); ?>">
            <?php endif; ?>

                <span class="drielo-pdf-card-media">
                  <?php
                  if ( $image_id > 0 && function_exists( 'make_static_attachment_image_html' ) ) {
                      echo wp_kses_post( make_static_attachment_image_html( $image_id, 'make-store-card-context', 'drielo-pdf-card-image' ) );
                  } else {
                      echo '<span class="drielo-pdf-placeholder" aria-hidden="true">×</span>';
                  }
                  ?>
                </span>

                <span class="drielo-pdf-card-meta">
                  <strong><?php echo esc_html( $technique ); ?></strong>
                  <?php if ( null === $pdf ) : ?><small><?php echo esc_html( make_t( 'Sin PDF', 'No PDF' ) ); ?></small><?php endif; ?>
                </span>

            <?php if ( null !== $pdf ) : ?>
              </a>
            <?php else : ?>
              </article>
            <?php endif; ?>

        <?php endwhile; ?>
      </div>

      <?php
      $total_pages = (int) $products->max_num_pages;
      if ( $total_pages > 1 ) :
          $current_page = max( 1, (int) get_query_var( 'paged' ) );
          $pagination = paginate_links(
              array(
                  'base'      => trailingslashit( home_url( '/pdfs/' ) ) . 'page/%#%/',
                  'format'    => '',
                  'current'   => $current_page,
                  'total'     => $total_pages,
                  'type'      => 'list',
                  'prev_text' => '←',
                  'next_text' => '→',
                  'add_args'  => $active_filters,
              )
          );
          if ( $pagination ) :
              ?>
              <nav class="drielo-pdf-pagination" aria-label="<?php echo esc_attr( make_t( 'Paginación de PDFs', 'PDF pagination' ) ); ?>">
                <?php echo wp_kses_post( $pagination ); ?>
              </nav>
              <?php
          endif;
      endif;
      ?>
    <?php else : ?>
      <div class="drielo-pdf-empty">
        <strong><?php echo esc_html( make_t( 'No hay productos con esos filtros.', 'There are no products with those filters.' ) ); ?></strong>
      </div>
    <?php endif; ?>

    <?php wp_reset_postdata(); ?>
  </div>
</section>

<?php get_footer(); ?>
