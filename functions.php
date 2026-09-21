<?php
/** Drielo theme functions. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

require_once get_template_directory() . '/inc/sitemap.php';
require_once get_template_directory() . '/inc/category-art.php';
require_once get_template_directory() . '/inc/store.php';

function make_theme_setup(): void {
    load_theme_textdomain( 'make', get_template_directory() . '/languages' );
    add_theme_support( 'title-tag' );
    add_theme_support( 'post-thumbnails' );
    add_theme_support( 'automatic-feed-links' );
    add_theme_support( 'responsive-embeds' );
    add_theme_support( 'align-wide' );
    add_theme_support( 'html5', array( 'search-form','comment-form','comment-list','gallery','caption','style','script' ) );
    add_theme_support( 'woocommerce' );
    add_theme_support( 'wc-product-gallery-zoom' );
    add_theme_support( 'wc-product-gallery-lightbox' );
    add_theme_support( 'wc-product-gallery-slider' );
    add_image_size( 'make-card', 760, 950, true );
    add_image_size( 'make-product-card', 700, 700, true );
    add_image_size( 'make-journal', 900, 560, true );
    register_nav_menus( array( 'primary' => __( 'Primary menu', 'make' ), 'footer' => __( 'Footer menu', 'make' ) ) );
}
add_action( 'after_setup_theme', 'make_theme_setup' );

// Use the high-resolution theme card image in WooCommerce archives.
// The storefront displays four products per row, so this avoids stretching
// WooCommerce's default 300px thumbnail while keeping the visual cards compact.
add_filter( 'single_product_archive_thumbnail_size', static function (): string {
    return 'make-product-card';
}, 20 );



/**
 * Editorial dimensions are deliberately independent from the current craft.
 * Cross stitch is the only active craft today, but the same data model can
 * later hold crochet, embroidery, woodworking or other maker disciplines
 * without changing article templates or the import pipeline.
 */
function make_register_editorial_taxonomies(): void {
    $taxonomies = array(
        'make_craft' => array(
            'single' => 'Craft',
            'plural' => 'Crafts',
            'hierarchical' => true,
        ),
        'make_topic' => array(
            'single' => 'Topic',
            'plural' => 'Topics',
            'hierarchical' => true,
        ),
        'make_style' => array(
            'single' => 'Style',
            'plural' => 'Styles',
            'hierarchical' => true,
        ),
        'make_skill' => array(
            'single' => 'Skill level',
            'plural' => 'Skill levels',
            'hierarchical' => false,
        ),
        'make_project_type' => array(
            'single' => 'Project type',
            'plural' => 'Project types',
            'hierarchical' => true,
        ),
        'make_article_type' => array(
            'single' => 'Article type',
            'plural' => 'Article types',
            'hierarchical' => false,
        ),
    );

    foreach ( $taxonomies as $taxonomy => $config ) {
        register_taxonomy(
            $taxonomy,
            array( 'post' ),
            array(
                'labels' => array(
                    'name' => $config['plural'],
                    'singular_name' => $config['single'],
                ),
                'public' => false,
                'show_ui' => true,
                'show_admin_column' => true,
                'show_in_rest' => true,
                'hierarchical' => (bool) $config['hierarchical'],
                'rewrite' => false,
                'query_var' => false,
            )
        );
    }
}
add_action( 'init', 'make_register_editorial_taxonomies', 5 );

function make_assets(): void {
    $version = wp_get_theme()->get( 'Version' ) ?: '1.0.0';
    $css = get_stylesheet_directory() . '/style.css';
    wp_enqueue_style( 'make-style', get_stylesheet_uri(), array(), is_file( $css ) ? (string) filemtime( $css ) : $version );
    $js = get_template_directory() . '/assets/js/site.js';
    wp_enqueue_script( 'make-site', get_template_directory_uri() . '/assets/js/site.js', array(), is_file( $js ) ? (string) filemtime( $js ) : $version, true );
}
add_action( 'wp_enqueue_scripts', 'make_assets' );

function make_request_path(): string {
    $uri = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
    $path = (string) wp_parse_url( $uri, PHP_URL_PATH );
    return '/' . trim( $path, '/' );
}

function make_current_language(): string {
    $query = (string) get_query_var( 'make_lang' );
    if ( in_array( $query, array( 'es', 'en' ), true ) ) { return $query; }
    $path = make_request_path();
    if ( '/en' === $path || str_starts_with( $path, '/en/' ) ) { return 'en'; }
    if ( function_exists( 'pll_current_language' ) ) {
        $pll = pll_current_language( 'slug' );
        if ( in_array( $pll, array( 'es', 'en' ), true ) ) { return $pll; }
    }
    if ( function_exists( 'is_singular' ) && is_singular( 'post' ) ) {
        $post_language = (string) get_post_meta( get_queried_object_id(), '_make_language', true );
        if ( in_array( $post_language, array( 'es', 'en' ), true ) ) { return $post_language; }
    }
    return 'es';
}

function make_is_english(): bool { return 'en' === make_current_language(); }
function make_t( string $es, string $en ): string { return make_is_english() ? $en : $es; }

function make_home_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    if ( function_exists( 'pll_home_url' ) ) {
        $url = pll_home_url( $language );
        if ( $url ) { return $url; }
    }
    if ( 'en' === $language ) {
        if ( '' !== (string) get_option( 'permalink_structure', '' ) ) {
            return home_url( '/en/' );
        }
        return add_query_arg( 'make_lang', 'en', home_url( '/' ) );
    }
    return home_url( '/' );
}

function make_language_switch_url( string $language ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : 'es';
    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $page  = max( 1, (int) get_query_var( 'paged' ) );
        $theme = function_exists( 'make_current_stitch_theme' ) ? make_current_stitch_theme() : '';
        return '' !== $theme ? make_stitch_theme_url( $theme, $language, $page ) : make_journal_page_url( $page, $language );
    }
    if ( is_singular() && function_exists( 'pll_get_post' ) ) {
        $translated = (int) pll_get_post( get_queried_object_id(), $language );
        if ( $translated ) { return get_permalink( $translated ); }
    }
    if ( is_singular( 'post' ) ) {
        $group = (string) get_post_meta( get_queried_object_id(), '_make_translation_group', true );
        if ( '' !== $group ) {
            $matches = get_posts(
                array(
                    'post_type'      => 'post',
                    'post_status'    => 'publish',
                    'posts_per_page' => 1,
                    'fields'         => 'ids',
                    'meta_query'     => array(
                        'relation' => 'AND',
                        array( 'key' => '_make_translation_group', 'value' => $group ),
                        array( 'key' => '_make_language', 'value' => $language ),
                    ),
                )
            );
            if ( ! empty( $matches ) ) { return get_permalink( (int) $matches[0] ); }
        }
    }
    if ( is_search() ) {
        return add_query_arg(
            array( 's' => get_search_query(), 'make_lang' => $language ),
            home_url( '/' )
        );
    }
    return make_home_url( $language );
}

function make_rewrite_rules(): void {
    add_rewrite_rule( '^en/?$', 'index.php?make_lang=en', 'top' );

    add_rewrite_rule( '^journal/?$', 'index.php?make_journal=1&make_lang=es', 'top' );
    add_rewrite_rule( '^journal/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^categoria/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=es&make_theme=$matches[1]', 'top' );
    add_rewrite_rule( '^categoria/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&make_theme=$matches[1]&paged=$matches[2]', 'top' );

    add_rewrite_rule( '^en/journal/?$', 'index.php?make_journal=1&make_lang=en', 'top' );
    add_rewrite_rule( '^en/journal/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^en/category/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=en&make_theme=$matches[1]', 'top' );
    add_rewrite_rule( '^en/category/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&make_theme=$matches[1]&paged=$matches[2]', 'top' );
}
add_action( 'init', 'make_rewrite_rules' );

function make_maybe_flush_editorial_rewrites(): void {
    $schema_version = '2';
    if ( $schema_version === (string) get_option( 'drielo_editorial_rewrite_schema', '' ) ) { return; }

    flush_rewrite_rules( false );
    update_option( 'drielo_editorial_rewrite_schema', $schema_version, false );
}
add_action( 'init', 'make_maybe_flush_editorial_rewrites', 100 );

function make_query_vars( array $vars ): array {
    $vars[] = 'make_lang';
    $vars[] = 'make_journal';
    return $vars;
}
add_filter( 'query_vars', 'make_query_vars' );

function make_template_router( string $template ): string {
    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $journal = locate_template( 'home.php' );
        if ( $journal ) { return $journal; }
    }
    if ( ( '/en' === make_request_path() || ( '/' === make_request_path() && 'en' === (string) get_query_var( 'make_lang' ) ) ) ) {
        $front = locate_template( 'front-page.php' );
        if ( $front ) { return $front; }
    }
    return $template;
}
add_filter( 'template_include', 'make_template_router', 99 );

function make_journal_main_query( WP_Query $query ): void {
    if ( is_admin() || ! $query->is_main_query() || (int) get_query_var( 'make_journal' ) !== 1 ) {
        return;
    }

    $query->set( 'post_type', 'post' );
    $query->set( 'post_status', 'publish' );
    $query->set( 'posts_per_page', 12 );
    $query->set( 'ignore_sticky_posts', true );
    $query->set(
        'meta_query',
        array(
            array(
                'key'   => '_make_language',
                'value' => make_current_language(),
            ),
        )
    );

    $query->is_home     = true;
    $query->is_page     = false;
    $query->is_singular = false;
}
add_action( 'pre_get_posts', 'make_journal_main_query', 20 );

function make_language_attributes( string $output ): string {
    $lang = make_is_english() ? 'en-US' : 'es-ES';
    if ( preg_match( '/lang=("|\')[^"\']+("|\')/i', $output ) ) {
        return (string) preg_replace( '/lang=("|\')[^"\']+("|\')/i', 'lang="' . esc_attr( $lang ) . '"', $output, 1 );
    }
    return trim( $output . ' lang="' . esc_attr( $lang ) . '"' );
}
add_filter( 'language_attributes', 'make_language_attributes', 20 );

function make_body_classes( array $classes ): array { $classes[] = 'make-lang-' . make_current_language(); return $classes; }
add_filter( 'body_class', 'make_body_classes' );

function make_brand_name(): string {
    return 'Drielo';
}

function make_brand_tagline(): string {
    $tagline = trim( (string) get_bloginfo( 'description' ) );
    return $tagline !== '' ? $tagline : make_t( 'patrones digitales para crear despacio', 'digital patterns for slow making' );
}

function make_journal_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();

    if ( '' !== (string) get_option( 'permalink_structure', '' ) ) {
        return home_url( 'en' === $language ? '/en/journal/' : '/journal/' );
    }

    return add_query_arg(
        array(
            'make_journal' => '1',
            'make_lang'    => $language,
        ),
        home_url( '/' )
    );
}

function make_journal_page_url( int $page = 1, string $language = '' ): string {
    $page = max( 1, $page );
    $base = make_journal_url( $language );
    if ( 1 === $page ) { return $base; }

    if ( '' !== (string) get_option( 'permalink_structure', '' ) ) {
        return trailingslashit( $base ) . 'page/' . $page . '/';
    }

    return add_query_arg( 'paged', $page, $base );
}

function make_cart_count(): int {
    return function_exists( 'WC' ) && WC()->cart ? (int) WC()->cart->get_cart_contents_count() : 0;
}

function make_cart_url(): string {
    return function_exists( 'wc_get_cart_url' ) ? wc_get_cart_url() : home_url( '/cart/' );
}

function make_shop_url(): string {
    if ( function_exists( 'wc_get_page_permalink' ) ) {
        $url = wc_get_page_permalink( 'shop' );
        if ( $url ) { return $url; }
    }
    return add_query_arg( 'post_type', 'product', make_home_url() );
}

function make_cross_stitch_url(): string {
    if ( taxonomy_exists( 'product_cat' ) ) {
        foreach ( array( 'cross-stitch', 'punto-de-cruz', 'cross-stitch-patterns' ) as $slug ) {
            $term = get_term_by( 'slug', $slug, 'product_cat' );
            if ( $term instanceof WP_Term ) {
                $url = get_term_link( $term );
                if ( ! is_wp_error( $url ) ) { return $url; }
            }
        }
    }
    return add_query_arg( 's', make_t( 'punto de cruz', 'cross stitch' ), make_home_url() );
}

function make_pattern_url( string $query ): string { return add_query_arg( 's', $query, make_home_url() ); }

function make_reading_time( int $post_id ): string {
    $words = str_word_count( wp_strip_all_tags( (string) get_post_field( 'post_content', $post_id ) ) );
    $minutes = max( 1, (int) ceil( $words / 220 ) );
    return sprintf( make_t( '%d min de lectura', '%d min read' ), $minutes );
}

add_filter( 'excerpt_length', static fn(): int => 22, 999 );
add_filter( 'excerpt_more', static fn(): string => '…' );


/**
 * First-run conveniences: the theme remains self-contained and does not rely on
 * a commercial parent theme. We only create the posts index if the site does not
 * already have one, so activating the theme immediately gives the editorial area
 * a stable URL without overwriting existing content.
 */
function make_after_switch_theme(): void {
    if ( ! get_option( 'page_for_posts' ) ) {
        $existing = get_page_by_path( 'journal' );
        $page_id  = $existing instanceof WP_Post ? $existing->ID : wp_insert_post(
            array(
                'post_title'  => 'Journal',
                'post_name'   => 'journal',
                'post_status' => 'publish',
                'post_type'   => 'page',
            ),
            true
        );
        if ( ! is_wp_error( $page_id ) && $page_id ) {
            update_option( 'page_for_posts', (int) $page_id );
        }
    }
    flush_rewrite_rules();
}
add_action( 'after_switch_theme', 'make_after_switch_theme' );

function make_archive_title(): string {
    if ( function_exists( 'is_shop' ) && is_shop() ) {
        return make_t( 'Tienda de patrones', 'Pattern shop' );
    }
    if ( is_category() || is_tag() || is_tax() ) {
        return single_term_title( '', false );
    }
    if ( is_post_type_archive() ) {
        return post_type_archive_title( '', false );
    }
    return make_t( 'Últimos artículos', 'Latest articles' );
}

/* WooCommerce presentation layer. */
function make_woocommerce_setup_hooks(): void {
    if ( ! class_exists( 'WooCommerce' ) ) { return; }

    remove_action( 'woocommerce_before_main_content', 'woocommerce_output_content_wrapper', 10 );
    remove_action( 'woocommerce_after_main_content', 'woocommerce_output_content_wrapper_end', 10 );
    remove_action( 'woocommerce_sidebar', 'woocommerce_get_sidebar', 10 );

    remove_action( 'woocommerce_before_main_content', 'woocommerce_breadcrumb', 20 );
    remove_action( 'woocommerce_after_shop_loop_item', 'woocommerce_template_loop_add_to_cart', 10 );
    add_action( 'woocommerce_after_shop_loop_item', 'make_product_card_link', 12 );

    add_action( 'woocommerce_single_product_summary', 'make_single_product_reassurance', 25 );
}
add_action( 'wp', 'make_woocommerce_setup_hooks' );

function make_product_card_link(): void {
    global $product;
    if ( ! $product instanceof WC_Product ) { return; }
    echo '<a class="make-product-view" href="' . esc_url( get_permalink( $product->get_id() ) ) . '">' .
        esc_html( make_t( 'Ver patrón', 'View pattern' ) ) . ' <span aria-hidden="true">→</span></a>';
}

function make_single_product_reassurance(): void {
    echo '<div class="make-product-reassurance">';
    echo '<span><i aria-hidden="true">↓</i><strong>' . esc_html( make_t( 'Descarga digital', 'Digital download' ) ) . '</strong><small>' . esc_html( make_t( 'Acceso tras la compra', 'Access after purchase' ) ) . '</small></span>';
    echo '<span><i aria-hidden="true">✓</i><strong>' . esc_html( make_t( 'Archivo preparado', 'Prepared file' ) ) . '</strong><small>' . esc_html( make_t( 'Pensado para imprimir', 'Made for printing' ) ) . '</small></span>';
    echo '<span><i aria-hidden="true">♡</i><strong>' . esc_html( make_t( 'Hecho con cuidado', 'Made with care' ) ) . '</strong><small>' . esc_html( make_t( 'Diseño revisado', 'Checked design' ) ) . '</small></span>';
    echo '</div>';
}

add_filter( 'loop_shop_columns', static fn(): int => 4, 20 );
add_filter( 'loop_shop_per_page', static fn(): int => 16, 20 );

function make_loop_product_classes( array $classes, $product ): array {
    if ( is_a( $product, 'WC_Product' ) ) { $classes[] = 'make-pattern-card'; }
    return $classes;
}
add_filter( 'woocommerce_post_class', 'make_loop_product_classes', 20, 2 );

function make_sale_flash( string $html ): string {
    return '<span class="onsale">' . esc_html( make_t( 'Oferta', 'Sale' ) ) . '</span>';
}
add_filter( 'woocommerce_sale_flash', 'make_sale_flash' );

function make_product_tabs( array $tabs ): array {
    if ( isset( $tabs['description'] ) ) {
        $tabs['description']['title'] = make_t( 'Sobre este patrón', 'About this pattern' );
    }
    if ( isset( $tabs['additional_information'] ) ) {
        $tabs['additional_information']['title'] = make_t( 'Detalles', 'Details' );
    }
    return $tabs;
}
add_filter( 'woocommerce_product_tabs', 'make_product_tabs', 20 );

function make_shop_body_class( array $classes ): array {
    if ( function_exists( 'is_woocommerce' ) && is_woocommerce() ) { $classes[] = 'make-commerce'; }
    if ( function_exists( 'is_product' ) && is_product() ) { $classes[] = 'make-single-product'; }
    return $classes;
}
add_filter( 'body_class', 'make_shop_body_class', 30 );


add_filter( 'woocommerce_show_page_title', '__return_false' );

function make_cart_count_fragment( array $fragments ): array {
    $count = make_cart_count();
    $html  = $count ? '<span class="cart-count">' . esc_html( (string) $count ) . '</span>' : '<span class="cart-count" hidden></span>';
    $fragments['.cart-count'] = $html;
    return $fragments;
}
add_filter( 'woocommerce_add_to_cart_fragments', 'make_cart_count_fragment' );


/**
 * Keep the Drielo stitched-D mark as the canonical site icon.
 * This also replaces any older WordPress Site Icon URL without touching content.
 */
function make_drielo_site_icon_url( string $url, int $size = 512, int $blog_id = 0 ): string {
    return get_template_directory_uri() . '/assets/images/brand-mark.png?v=3';
}
add_filter( 'get_site_icon_url', 'make_drielo_site_icon_url', 20, 3 );

function make_fallback_favicon(): void {
    if ( function_exists( 'has_site_icon' ) && has_site_icon() ) { return; }
    $icon = get_template_directory_uri() . '/assets/images/brand-mark.svg';
    echo '<link rel="icon" href="' . esc_url( $icon ) . '" type="image/png">' . "\n";
}
add_action( 'wp_head', 'make_fallback_favicon', 2 );


/* ========================================================================
   Editorial discovery, internal linking and SEO fallbacks
   ======================================================================== */

function make_editorial_section_config(): array {
    return array(
        'learn' => array(
            'es' => array(
                'slug' => 'aprender',
                'label' => 'Aprender',
                'description' => 'Técnicas, materiales y respuestas claras para bordar con más seguridad.',
            ),
            'en' => array(
                'slug' => 'learn',
                'label' => 'Learn',
                'description' => 'Techniques, materials and clear answers for stitching with more confidence.',
            ),
        ),
        'ideas' => array(
            'es' => array(
                'slug' => 'ideas',
                'label' => 'Ideas e inspiración',
                'description' => 'Temas, estilos y proyectos para encontrar algo que de verdad apetezca bordar.',
            ),
            'en' => array(
                'slug' => 'inspiration',
                'label' => 'Ideas & inspiration',
                'description' => 'Themes, styles and projects for finding something you genuinely want to stitch.',
            ),
        ),
        'buying-guides' => array(
            'es' => array(
                'slug' => 'guias-de-compra',
                'label' => 'Guías de compra',
                'description' => 'Comparativas y criterios prácticos para elegir patrones, materiales y herramientas.',
            ),
            'en' => array(
                'slug' => 'buying-guides',
                'label' => 'Buying guides',
                'description' => 'Practical comparisons for choosing patterns, materials and tools.',
            ),
        ),
    );
}

function make_editorial_sections( string $language = '' ): array {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $sections = array();

    foreach ( make_editorial_section_config() as $id => $localized ) {
        $cfg = $localized[ $language ];
        $term = get_category_by_slug( $cfg['slug'] );
        if ( ! $term instanceof WP_Term || (int) $term->count < 1 ) { continue; }

        $url = get_category_link( $term );
        if ( is_wp_error( $url ) ) { continue; }

        $sections[] = array(
            'id'          => $id,
            'label'       => $cfg['label'],
            'description' => $cfg['description'],
            'count'       => (int) $term->count,
            'url'         => $url,
        );
    }

    return $sections;
}

function make_editorial_archive_description(): string {
    if ( ! is_category() ) { return ''; }
    $term = get_queried_object();
    if ( ! $term instanceof WP_Term ) { return ''; }

    $section_id = (string) get_term_meta( $term->term_id, '_make_section_id', true );
    $config = make_editorial_section_config();
    $language = (string) get_term_meta( $term->term_id, '_make_language', true );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();

    return isset( $config[ $section_id ][ $language ]['description'] )
        ? (string) $config[ $section_id ][ $language ]['description']
        : '';
}

function make_editorial_placeholder_html( int $post_id = 0 ): string {
    $post_id = $post_id ?: get_the_ID();
    return make_stitch_theme_art_html( make_article_stitch_theme( $post_id ), 'make-editorial-art' );
}

function make_related_articles( int $post_id, int $limit = 3 ): array {
    $language = (string) get_post_meta( $post_id, '_make_language', true );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $weighted_taxonomies = array(
        'make_topic'        => 5,
        'make_style'        => 3,
        'make_project_type' => 2,
        'make_article_type' => 1,
    );
    $source_terms = array();
    $tax_query = array( 'relation' => 'OR' );

    foreach ( $weighted_taxonomies as $taxonomy => $weight ) {
        $terms = get_the_terms( $post_id, $taxonomy );
        if ( is_wp_error( $terms ) || empty( $terms ) ) { continue; }
        $ids = array_map( 'intval', wp_list_pluck( $terms, 'term_id' ) );
        if ( empty( $ids ) ) { continue; }
        $source_terms[ $taxonomy ] = $ids;
        $tax_query[] = array(
            'taxonomy' => $taxonomy,
            'field'    => 'term_id',
            'terms'    => $ids,
        );
    }

    $candidate_ids = array();
    if ( count( $tax_query ) > 1 ) {
        $candidate_query = new WP_Query(
            array(
                'post_type'           => 'post',
                'post_status'         => 'publish',
                'posts_per_page'      => 30,
                'fields'              => 'ids',
                'post__not_in'        => array( $post_id ),
                'ignore_sticky_posts' => true,
                'meta_query'          => array(
                    array(
                        'key'   => '_make_language',
                        'value' => $language,
                    ),
                ),
                'tax_query'            => $tax_query,
            )
        );
        $candidate_ids = array_map( 'intval', $candidate_query->posts );
    }

    $scores = array();
    foreach ( $candidate_ids as $candidate_id ) {
        $score = 0;
        foreach ( $source_terms as $taxonomy => $source_ids ) {
            $candidate_terms = get_the_terms( $candidate_id, $taxonomy );
            if ( is_wp_error( $candidate_terms ) || empty( $candidate_terms ) ) { continue; }
            $candidate_term_ids = array_map( 'intval', wp_list_pluck( $candidate_terms, 'term_id' ) );
            $shared = count( array_intersect( $source_ids, $candidate_term_ids ) );
            $score += $shared * $weighted_taxonomies[ $taxonomy ];
        }
        $scores[ $candidate_id ] = $score;
    }

    arsort( $scores, SORT_NUMERIC );
    $related = array_slice( array_keys( $scores ), 0, $limit );

    if ( count( $related ) < $limit ) {
        $fallback = get_posts(
            array(
                'post_type'           => 'post',
                'post_status'         => 'publish',
                'posts_per_page'      => $limit - count( $related ),
                'fields'              => 'ids',
                'post__not_in'        => array_merge( array( $post_id ), $related ),
                'ignore_sticky_posts' => true,
                'meta_query'          => array(
                    array(
                        'key'   => '_make_language',
                        'value' => $language,
                    ),
                ),
            )
        );
        $related = array_merge( $related, array_map( 'intval', $fallback ) );
    }

    return array_slice( $related, 0, $limit );
}

function make_search_main_query( WP_Query $query ): void {
    if ( is_admin() || ! $query->is_main_query() || ! $query->is_search() ) { return; }

    $query->set( 'post_type', array( 'post', 'product' ) );
    $query->set( 'posts_per_page', 12 );
    $query->set( 'ignore_sticky_posts', true );
    $query->set(
        'meta_query',
        array(
            'relation' => 'OR',
            array(
                'key'   => '_make_language',
                'value' => make_current_language(),
            ),
            array(
                'key'     => '_make_language',
                'compare' => 'NOT EXISTS',
            ),
        )
    );
}
add_action( 'pre_get_posts', 'make_search_main_query', 25 );

function make_has_seo_plugin(): bool {
    return defined( 'WPSEO_VERSION' )
        || defined( 'RANK_MATH_VERSION' )
        || defined( 'AIOSEO_VERSION' )
        || class_exists( 'WPSEO_Frontend' )
        || class_exists( 'RankMath' );
}

function make_editorial_document_title( string $title ): string {
    if ( make_has_seo_plugin() ) { return $title; }

    if ( is_singular( 'post' ) ) {
        $seo_title = trim( (string) get_post_meta( get_queried_object_id(), '_make_seo_title', true ) );
        if ( '' !== $seo_title ) { return $seo_title . ' | ' . make_brand_name(); }
    }

    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $theme = function_exists( 'make_current_stitch_theme' ) ? make_current_stitch_theme() : '';
        $config = function_exists( 'make_stitch_theme_config' ) ? make_stitch_theme_config() : array();
        if ( '' !== $theme && isset( $config[ $theme ][ make_current_language() ]['label'] ) ) {
            return $config[ $theme ][ make_current_language() ]['label'] . ' · ' . make_t( 'Punto de cruz', 'Cross stitch' ) . ' | ' . make_brand_name();
        }
        return make_t( 'Guías e ideas de punto de cruz', 'Cross stitch guides and ideas' ) . ' | ' . make_brand_name();
    }

    return $title;
}
add_filter( 'pre_get_document_title', 'make_editorial_document_title', 20 );

function make_editorial_head_meta(): void {
    $description = '';
    $canonical = '';

    if ( is_singular( 'post' ) ) {
        $post_id = get_queried_object_id();
        $description = trim( (string) get_post_meta( $post_id, '_make_meta_description', true ) );

        if ( ! make_has_seo_plugin() ) {
            $schema = array(
                '@context' => 'https://schema.org',
                '@type' => 'Article',
                'headline' => get_the_title( $post_id ),
                'description' => $description,
                'inLanguage' => make_is_english() ? 'en-US' : 'es-ES',
                'mainEntityOfPage' => get_permalink( $post_id ),
                'datePublished' => get_post_time( DATE_W3C, true, $post_id ),
                'dateModified' => get_post_modified_time( DATE_W3C, true, $post_id ),
                'author' => array(
                    '@type' => 'Organization',
                    'name' => make_brand_name(),
                ),
                'publisher' => array(
                    '@type' => 'Organization',
                    'name' => make_brand_name(),
                ),
            );
            if ( has_post_thumbnail( $post_id ) ) {
                $image = wp_get_attachment_image_url( get_post_thumbnail_id( $post_id ), 'full' );
                if ( $image ) { $schema['image'] = array( $image ); }
            }
            echo '<script type="application/ld+json">' . wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) . '</script>' . "\n";
        }

        if ( ! function_exists( 'pll_current_language' ) ) {
            $group = (string) get_post_meta( $post_id, '_make_translation_group', true );
            if ( '' !== $group ) {
                foreach ( array( 'es' => 'es-ES', 'en' => 'en-US' ) as $lang => $hreflang ) {
                    $matches = get_posts(
                        array(
                            'post_type' => 'post',
                            'post_status' => 'publish',
                            'posts_per_page' => 1,
                            'fields' => 'ids',
                            'meta_query' => array(
                                'relation' => 'AND',
                                array( 'key' => '_make_translation_group', 'value' => $group ),
                                array( 'key' => '_make_language', 'value' => $lang ),
                            ),
                        )
                    );
                    if ( ! empty( $matches ) ) {
                        echo '<link rel="alternate" hreflang="' . esc_attr( $hreflang ) . '" href="' . esc_url( get_permalink( (int) $matches[0] ) ) . '">' . "\n";
                    }
                }
            }
        }
    } elseif ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $description = make_t(
            'Guías claras, ideas y proyectos de punto de cruz para aprender técnicas, elegir materiales y encontrar tu siguiente patrón.',
            'Clear cross stitch guides, ideas and projects for learning techniques, choosing materials and finding your next pattern.'
        );
        $page = max( 1, (int) get_query_var( 'paged' ) );
        $theme = function_exists( 'make_current_stitch_theme' ) ? make_current_stitch_theme() : '';
        $canonical = '' !== $theme ? make_stitch_theme_url( $theme, make_current_language(), $page ) : make_journal_page_url( $page );

        foreach ( array( 'es' => 'es-ES', 'en' => 'en-US' ) as $lang => $hreflang ) {
            $url = '' !== $theme ? make_stitch_theme_url( $theme, $lang, $page ) : make_journal_page_url( $page, $lang );
            echo '<link rel="alternate" hreflang="' . esc_attr( $hreflang ) . '" href="' . esc_url( $url ) . '">' . "\n";
        }
    }

    if ( ! make_has_seo_plugin() && '' !== $description ) {
        echo '<meta name="description" content="' . esc_attr( $description ) . '">' . "\n";
    }
    if ( ! make_has_seo_plugin() && '' !== $canonical ) {
        echo '<link rel="canonical" href="' . esc_url( $canonical ) . '">' . "\n";
    }
}
add_action( 'wp_head', 'make_editorial_head_meta', 6 );

function make_editorial_robots( array $robots ): array {
    if ( is_search() || is_author() || is_date() || is_category() || is_tag() ) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
    }
    return $robots;
}
add_filter( 'wp_robots', 'make_editorial_robots', 20 );

function make_editorial_sitemap_taxonomies( array $taxonomies ): array {
    unset( $taxonomies['category'], $taxonomies['post_tag'] );
    return $taxonomies;
}
add_filter( 'wp_sitemaps_taxonomies', 'make_editorial_sitemap_taxonomies' );

function make_editorial_sitemap_providers( $provider, string $name ) {
    return 'users' === $name ? false : $provider;
}
add_filter( 'wp_sitemaps_add_provider', 'make_editorial_sitemap_providers', 10, 2 );


/**
 * Visual topic system for the editorial journal.
 * These are presentation groups over the existing make_topic/make_style terms.
 * They do not replace the underlying taxonomy, so the content model stays future-proof.
 */
function make_stitch_theme_config(): array {
    return array(
        'florals' => array(
            'es' => array( 'label'=>'Flores y botánica', 'description'=>'Flores, hojas, plantas y motivos naturales.' ),
            'en' => array( 'label'=>'Florals & botanical', 'description'=>'Flowers, leaves, plants and botanical motifs.' ),
            'topic' => array( 'florals','nature','gardening','spring' ),
            'style' => array( 'botanical' ),
        ),
        'animals' => array(
            'es' => array( 'label'=>'Animales y mascotas', 'description'=>'Gatos, perros y diseños para amantes de los animales.' ),
            'en' => array( 'label'=>'Animals & pets', 'description'=>'Cats, dogs and designs for animal lovers.' ),
            'topic' => array( 'animals','pets' ),
            'style' => array(),
        ),
        'pop-art' => array(
            'es' => array( 'label'=>'Pop art', 'description'=>'Color, contraste y diseños con mucha personalidad.' ),
            'en' => array( 'label'=>'Pop art', 'description'=>'Color, contrast and designs with plenty of personality.' ),
            'topic' => array( 'pop-art' ),
            'style' => array( 'pop-art','modern' ),
        ),
        'retro' => array(
            'es' => array( 'label'=>'Retro y vintage', 'description'=>'Guiños nostálgicos, formas setenteras y estética vintage.' ),
            'en' => array( 'label'=>'Retro & vintage', 'description'=>'Nostalgic references, seventies shapes and vintage style.' ),
            'topic' => array( 'retro' ),
            'style' => array( 'retro','vintage' ),
        ),
        'geometric' => array(
            'es' => array( 'label'=>'Minimal y geométrico', 'description'=>'Formas limpias, abstractas y fáciles de integrar en casa.' ),
            'en' => array( 'label'=>'Minimal & geometric', 'description'=>'Clean, abstract shapes that fit easily into modern homes.' ),
            'topic' => array( 'minimalist','geometric' ),
            'style' => array( 'minimalist','geometric' ),
        ),
        'celestial' => array(
            'es' => array( 'label'=>'Cielo y fantasía', 'description'=>'Lunas, estrellas, constelaciones y motivos de fantasía.' ),
            'en' => array( 'label'=>'Celestial & fantasy', 'description'=>'Moons, stars, constellations and fantasy motifs.' ),
            'topic' => array( 'celestial','fantasy' ),
            'style' => array(),
        ),
        'food' => array(
            'es' => array( 'label'=>'Comida y café', 'description'=>'Café, repostería y pequeños diseños para cocinas con carácter.' ),
            'en' => array( 'label'=>'Food & coffee', 'description'=>'Coffee, baking and playful designs for kitchens with character.' ),
            'topic' => array( 'food','coffee','baking' ),
            'style' => array(),
        ),
        'quotes' => array(
            'es' => array( 'label'=>'Frases', 'description'=>'Mensajes divertidos, modernos y pensados para regalar.' ),
            'en' => array( 'label'=>'Quotes', 'description'=>'Funny, modern messages made for stitching and gifting.' ),
            'topic' => array( 'quotes' ),
            'style' => array(),
        ),
        'seasonal' => array(
            'es' => array( 'label'=>'Temporada', 'description'=>'Navidad, Halloween, Pascua y estaciones del año.' ),
            'en' => array( 'label'=>'Seasonal', 'description'=>'Christmas, Halloween, Easter and seasonal projects.' ),
            'topic' => array( 'christmas','halloween','easter','spring','autumn' ),
            'style' => array(),
        ),
    );
}

function make_current_stitch_theme(): string {
    $theme = sanitize_key( (string) get_query_var( 'make_theme' ) );
    return isset( make_stitch_theme_config()[ $theme ] ) ? $theme : '';
}

function make_stitch_theme_url( string $theme, string $language = '', int $page = 1 ): string {
    $theme = sanitize_key( $theme );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $page = max( 1, $page );

    if ( ! isset( make_stitch_theme_config()[ $theme ] ) ) { return make_journal_url( $language ); }

    if ( '' !== (string) get_option( 'permalink_structure', '' ) ) {
        $base = 'en' === $language
            ? home_url( '/en/category/' . rawurlencode( $theme ) . '/' )
            : home_url( '/categoria/' . rawurlencode( $theme ) . '/' );

        return 1 === $page ? $base : trailingslashit( $base ) . 'page/' . $page . '/';
    }

    $args = array(
        'make_journal' => '1',
        'make_lang'    => $language,
        'make_theme'   => $theme,
    );
    if ( $page > 1 ) { $args['paged'] = $page; }

    return add_query_arg( $args, home_url( '/' ) );
}

function make_redirect_legacy_stitch_theme_url(): void {
    if ( is_admin() || '' === (string) get_option( 'permalink_structure', '' ) || ! isset( $_GET['make_theme'] ) ) {
        return;
    }

    $theme = sanitize_key( (string) wp_unslash( $_GET['make_theme'] ) );
    if ( ! isset( make_stitch_theme_config()[ $theme ] ) ) { return; }

    $language = isset( $_GET['make_lang'] )
        ? sanitize_key( (string) wp_unslash( $_GET['make_lang'] ) )
        : make_current_language();
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();

    $page = isset( $_GET['paged'] ) ? max( 1, absint( $_GET['paged'] ) ) : max( 1, (int) get_query_var( 'paged' ) );

    wp_safe_redirect( make_stitch_theme_url( $theme, $language, $page ), 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_stitch_theme_url', -90 );

function make_stitch_theme_cards( string $language = '' ): array {
    $language = in_array( $language, array('es','en'), true ) ? $language : make_current_language();
    $cards = array();

    foreach ( make_stitch_theme_config() as $id=>$config ) {
        $has_content = false;
        foreach ( array( 'make_topic'=>'topic', 'make_style'=>'style' ) as $taxonomy=>$dimension ) {
            foreach ( $config[ $dimension ] as $slug ) {
                $term = get_term_by( 'slug', $slug, $taxonomy );
                if ( $term instanceof WP_Term && (int) $term->count > 0 ) { $has_content = true; break 2; }
            }
        }
        if ( ! $has_content ) { continue; }

        $cards[] = array(
            'id'          => $id,
            'label'       => $config[ $language ]['label'],
            'description' => $config[ $language ]['description'],
            'url'         => make_stitch_theme_url( $id, $language ),
        );
    }
    return $cards;
}

function make_article_stitch_theme( int $post_id ): string {
    $topic_slugs = wp_get_post_terms( $post_id, 'make_topic', array( 'fields'=>'slugs' ) );
    $style_slugs = wp_get_post_terms( $post_id, 'make_style', array( 'fields'=>'slugs' ) );
    $topic_slugs = is_wp_error( $topic_slugs ) ? array() : $topic_slugs;
    $style_slugs = is_wp_error( $style_slugs ) ? array() : $style_slugs;

    foreach ( make_stitch_theme_config() as $id=>$config ) {
        if ( array_intersect( $topic_slugs, $config['topic'] ) || array_intersect( $style_slugs, $config['style'] ) ) {
            return $id;
        }
    }
    return 'florals';
}

function make_stitch_theme_tax_query( string $theme ): array {
    $config = make_stitch_theme_config();
    if ( ! isset( $config[ $theme ] ) ) { return array(); }

    $tax_query = array( 'relation'=>'OR' );
    if ( ! empty( $config[ $theme ]['topic'] ) ) {
        $tax_query[] = array(
            'taxonomy'=>'make_topic',
            'field'=>'slug',
            'terms'=>$config[ $theme ]['topic'],
        );
    }
    if ( ! empty( $config[ $theme ]['style'] ) ) {
        $tax_query[] = array(
            'taxonomy'=>'make_style',
            'field'=>'slug',
            'terms'=>$config[ $theme ]['style'],
        );
    }
    return count( $tax_query ) > 1 ? $tax_query : array();
}

function make_stitch_theme_query_var( array $vars ): array {
    $vars[] = 'make_theme';
    return $vars;
}
add_filter( 'query_vars', 'make_stitch_theme_query_var', 20 );

function make_stitch_theme_main_query( WP_Query $query ): void {
    if ( is_admin() || ! $query->is_main_query() || (int) get_query_var( 'make_journal' ) !== 1 ) { return; }
    $theme = make_current_stitch_theme();
    if ( '' === $theme ) { return; }
    $tax_query = make_stitch_theme_tax_query( $theme );
    if ( ! empty( $tax_query ) ) { $query->set( 'tax_query', $tax_query ); }
}
add_action( 'pre_get_posts', 'make_stitch_theme_main_query', 22 );

function make_journal_pagination_html( WP_Query $query, string $language = '', string $theme = '' ): string {
    $total = max( 1, (int) $query->max_num_pages );
    if ( $total < 2 ) { return ''; }

    $current = max( 1, (int) get_query_var( 'paged' ) );
    $language = in_array( $language, array('es','en'), true ) ? $language : make_current_language();
    $pages = array();

    $link = static function( int $page, string $label, string $class = '' ) use ( $language, $theme ): string {
        $url = '' !== $theme ? make_stitch_theme_url( $theme, $language, $page ) : make_journal_page_url( $page, $language );
        return '<a class="page-number ' . esc_attr( $class ) . '" href="' . esc_url( $url ) . '">' . esc_html( $label ) . '</a>';
    };

    if ( $current > 1 ) { $pages[] = $link( $current-1, make_t( '← Anterior', '← Previous' ), 'page-number--prev' ); }

    $start = max( 1, $current - 2 );
    $end = min( $total, $current + 2 );
    if ( $start > 1 ) {
        $pages[] = $link( 1, '1' );
        if ( $start > 2 ) { $pages[] = '<span class="page-number page-number--dots" aria-hidden="true">…</span>'; }
    }
    for ( $page=$start; $page<=$end; $page++ ) {
        if ( $page === $current ) {
            $pages[] = '<span class="page-number is-current" aria-current="page">' . esc_html( (string) $page ) . '</span>';
        } else {
            $pages[] = $link( $page, (string) $page );
        }
    }
    if ( $end < $total ) {
        if ( $end < $total-1 ) { $pages[] = '<span class="page-number page-number--dots" aria-hidden="true">…</span>'; }
        $pages[] = $link( $total, (string) $total );
    }
    if ( $current < $total ) { $pages[] = $link( $current+1, make_t( 'Siguiente →', 'Next →' ), 'page-number--next' ); }

    return '<div class="journal-pagination-buttons">' . implode( '', $pages ) . '</div>';
}
