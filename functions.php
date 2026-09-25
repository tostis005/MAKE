<?php
/** Drielo theme functions. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

require_once get_template_directory() . '/inc/sitemap.php';
require_once get_template_directory() . '/inc/category-art.php';
require_once get_template_directory() . '/inc/store.php';
require_once get_template_directory() . '/inc/store-pagination.php';
require_once get_template_directory() . '/inc/pdf-library.php';
require_once get_template_directory() . '/inc/editorial-crafts.php';

function make_theme_setup(): void {
    load_theme_textdomain( 'make', get_template_directory() . '/languages' );
    add_theme_support( 'title-tag' );
    add_theme_support( 'post-thumbnails' );
    add_theme_support( 'automatic-feed-links' );
    add_theme_support( 'responsive-embeds' );
    add_theme_support( 'align-wide' );
    add_theme_support( 'html5', array( 'search-form','comment-form','comment-list','gallery','caption','style','script' ) );
    add_theme_support( 'woocommerce' );
    add_theme_support( 'wc-product-gallery-slider' );
    add_image_size( 'make-card', 760, 950, true );
    // Responsive storefront derivatives: browsers can choose a lean 1x card or the retina/tablet version.
    add_image_size( 'make-store-card', 560, 560, true );
    add_image_size( 'make-store-card-small-context', 320, 400, false );
    add_image_size( 'make-store-card-context', 560, 700, false );
    add_image_size( 'make-home-product-card', 560, 700, true );
    add_image_size( 'make-collection-preview', 240, 240, true );
    add_image_size( 'make-collection-preview-context', 300, 300, false );
    add_image_size( 'make-product-card', 700, 700, true );
    add_image_size( 'make-journal', 900, 560, true );
    register_nav_menus( array( 'primary' => __( 'Primary menu', 'make' ), 'footer' => __( 'Footer menu', 'make' ) ) );
}
add_action( 'after_setup_theme', 'make_theme_setup' );

// Store cards use the exact uploaded source image. This avoids any generated
// WooCommerce/WordPress derivative becoming the visible storefront asset.
add_filter( 'single_product_archive_thumbnail_size', static function (): string {
    return 'full';
}, 20 );

function make_attachment_cache_busted_url( int $attachment_id, string $url ): string {
    if ( $attachment_id <= 0 || '' === $url ) { return $url; }

    $hash = trim( (string) get_post_meta( $attachment_id, '_drielo_source_hash', true ) );
    if ( '' === $hash ) {
        $file = get_attached_file( $attachment_id );
        if ( $file && is_file( $file ) ) {
            $hash = md5_file( $file ) ?: '';
        }
    }

    return '' !== $hash ? add_query_arg( 'v', substr( $hash, 0, 12 ), $url ) : $url;
}

function make_static_attachment_image_html( int $attachment_id, string $size = 'medium_large', string $class = '' ): string {
    if ( $attachment_id <= 0 ) { return ''; }

    $image = wp_get_attachment_image_src( $attachment_id, $size );
    if ( ! is_array( $image ) || empty( $image[0] ) ) { return ''; }

    $alt = trim( (string) get_post_meta( $attachment_id, '_wp_attachment_image_alt', true ) );
    return sprintf(
        '<img src="%1$s" width="%2$d" height="%3$d" class="%4$s" alt="%5$s" loading="lazy" decoding="async">',
        esc_url( make_attachment_cache_busted_url( $attachment_id, $image[0] ) ),
        (int) $image[1],
        (int) $image[2],
        esc_attr( $class ),
        esc_attr( $alt )
    );
}
function make_loop_product_thumbnail(): void {
    global $product;
    if ( ! $product instanceof WC_Product ) { return; }

    $image_id = $product->get_image_id();
    if ( $image_id ) {
        echo wp_kses_post( make_static_attachment_image_html( $image_id, 'full', 'attachment-full size-full drielo-store-product-image' ) );
        return;
    }

    echo wc_placeholder_img( 'woocommerce_thumbnail' );
}
remove_action( 'woocommerce_before_shop_loop_item_title', 'woocommerce_template_loop_product_thumbnail', 10 );
add_action( 'woocommerce_before_shop_loop_item_title', 'make_loop_product_thumbnail', 10 );

function make_protected_single_product_image_html( string $html, int $attachment_id ): string {
    if ( $attachment_id <= 0 ) { return $html; }

    $image = wp_get_attachment_image_src( $attachment_id, 'full' );
    if ( ! is_array( $image ) || empty( $image[0] ) ) { return $html; }

    $thumb = wp_get_attachment_image_src( $attachment_id, 'thumbnail' );
    $thumb_url = is_array( $thumb ) && ! empty( $thumb[0] ) ? $thumb[0] : $image[0];
    $alt = trim( (string) get_post_meta( $attachment_id, '_wp_attachment_image_alt', true ) );

    global $product;
    $classes = 'woocommerce-product-gallery__image';
    $img_class = 'attachment-full size-full drielo-single-product-image';
    if ( $product instanceof WC_Product && (int) $product->get_image_id() === $attachment_id ) {
        $img_class .= ' wp-post-image';
    }

    return sprintf(
        '<div data-thumb="%1$s" data-thumb-alt="%2$s" class="%3$s"><img src="%4$s" width="%5$d" height="%6$d" class="%7$s" alt="%2$s" loading="lazy" decoding="async"></div>',
        esc_url( $thumb_url ),
        esc_attr( $alt ),
        esc_attr( $classes ),
        esc_url( make_attachment_cache_busted_url( $attachment_id, $image[0] ) ),
        (int) $image[1],
        (int) $image[2],
        esc_attr( $img_class )
    );
}
add_filter( 'woocommerce_single_product_image_thumbnail_html', 'make_protected_single_product_image_html', 40, 2 );



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
    return home_url( 'en' === $language ? '/en/' : '/' );
}

function make_article_base_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/articles/' : '/articulos/' );
}

function make_search_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/search/' : '/buscar/' );
}

function make_language_switch_url( string $language ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : 'es';

    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $page  = max( 1, (int) get_query_var( 'paged' ) );
        $craft = function_exists( 'make_current_editorial_craft' ) ? make_current_editorial_craft() : '';
        if ( '' !== $craft && function_exists( 'make_editorial_craft_url' ) ) {
            $section = function_exists( 'make_current_editorial_craft_section' ) ? make_current_editorial_craft_section() : '';
            return '' !== $section && function_exists( 'make_editorial_craft_section_url' )
                ? make_editorial_craft_section_url( $craft, $section, $language, $page )
                : make_editorial_craft_url( $craft, $language, $page );
        }
        $theme = function_exists( 'make_current_stitch_theme' ) ? make_current_stitch_theme() : '';
        return '' !== $theme ? make_stitch_theme_url( $theme, $language, $page ) : make_journal_page_url( $page, $language );
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

    if ( is_singular( 'product' ) && function_exists( 'make_product_url' ) ) {
        return make_product_url( get_queried_object_id(), $language );
    }

    if ( is_tax( array( 'product_collection', 'product_cat' ) ) && function_exists( 'make_store_term_url' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) { return make_store_term_url( $term, $language ); }
    }

    if ( function_exists( 'is_shop' ) && is_shop() ) {
        $view = function_exists( 'make_store_view' ) ? make_store_view() : 'patterns';
        return function_exists( 'make_shop_view_url' ) ? make_shop_view_url( $view, $language ) : make_shop_url( $language );
    }

    if ( function_exists( 'is_cart' ) && is_cart() ) { return make_cart_url( $language ); }
    if ( function_exists( 'is_checkout' ) && is_checkout() && function_exists( 'make_checkout_url' ) ) {
        if ( function_exists( 'make_store_current_endpoint_url' ) ) {
            $endpoint_url = make_store_current_endpoint_url( $language, 'checkout' );
            if ( '' !== $endpoint_url ) { return $endpoint_url; }
        }
        return make_checkout_url( $language );
    }
    if ( function_exists( 'is_account_page' ) && is_account_page() && function_exists( 'make_account_url' ) ) {
        if ( function_exists( 'make_store_current_endpoint_url' ) ) {
            $endpoint_url = make_store_current_endpoint_url( $language, 'account' );
            if ( '' !== $endpoint_url ) { return $endpoint_url; }
        }
        return make_account_url( $language );
    }

    if ( is_category() ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $section = (string) get_term_meta( $term->term_id, '_make_section_id', true );
            $config  = make_editorial_section_config();
            if ( '' !== $section && isset( $config[ $section ][ $language ]['slug'] ) ) {
                $slug = $config[ $section ][ $language ]['slug'];
                $base = 'en' === $language ? '/en/articles/section/' : '/articulos/seccion/';
                return home_url( $base . rawurlencode( $slug ) . '/' );
            }
        }
    }

    if ( is_search() ) {
        return add_query_arg( 's', get_search_query(), make_search_url( $language ) );
    }

    return make_home_url( $language );
}

function make_rewrite_rules(): void {
    add_rewrite_rule( '^en/?$', 'index.php?make_lang=en', 'top' );

    add_rewrite_rule( '^buscar/?$', 'index.php?make_lang=es', 'top' );
    add_rewrite_rule( '^en/search/?$', 'index.php?make_lang=en', 'top' );

    add_rewrite_rule( '^articulos/?$', 'index.php?make_journal=1&make_lang=es', 'top' );
    add_rewrite_rule( '^articulos/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^articulos/tema/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=es&make_theme_slug=$matches[1]', 'top' );
    add_rewrite_rule( '^articulos/tema/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&make_theme_slug=$matches[1]&paged=$matches[2]', 'top' );
    add_rewrite_rule( '^articulos/seccion/([a-z0-9-]+)/?$', 'index.php?category_name=$matches[1]&make_lang=es', 'top' );
    add_rewrite_rule( '^articulos/([a-z0-9-]+)/?$', 'index.php?name=$matches[1]&make_lang=es', 'top' );

    add_rewrite_rule( '^en/articles/?$', 'index.php?make_journal=1&make_lang=en', 'top' );
    add_rewrite_rule( '^en/articles/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^en/articles/topic/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=en&make_theme_slug=$matches[1]', 'top' );
    add_rewrite_rule( '^en/articles/topic/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&make_theme_slug=$matches[1]&paged=$matches[2]', 'top' );
    add_rewrite_rule( '^en/articles/section/([a-z0-9-]+)/?$', 'index.php?category_name=$matches[1]&make_lang=en', 'top' );
    add_rewrite_rule( '^en/articles/([a-z0-9-]+)/?$', 'index.php?name=$matches[1]&make_lang=en', 'top' );

    // Legacy editorial paths stay resolvable so template_redirect can 301 them.
    add_rewrite_rule( '^journal/?$', 'index.php?make_journal=1&make_lang=es', 'top' );
    add_rewrite_rule( '^journal/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^categoria/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=es&make_theme=$matches[1]', 'top' );
    add_rewrite_rule( '^categoria/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&make_theme=$matches[1]&paged=$matches[2]', 'top' );
    add_rewrite_rule( '^en/journal/?$', 'index.php?make_journal=1&make_lang=en', 'top' );
    add_rewrite_rule( '^en/journal/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^en/category/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=en&make_theme=$matches[1]', 'top' );
    add_rewrite_rule( '^en/category/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&make_theme=$matches[1]&paged=$matches[2]', 'top' );
}
add_action( 'init', 'make_rewrite_rules', 20 );

function make_maybe_flush_editorial_rewrites(): void {
    $schema_version = '4';
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
    return make_article_base_url( $language );
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

function make_cart_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    if ( 'en' === $language ) { return home_url( '/en/cart/' ); }
    return home_url( '/carrito/' );
}

function make_checkout_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    if ( 'en' === $language ) { return home_url( '/en/checkout/' ); }
    return home_url( '/finalizar-compra/' );
}

function make_account_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    if ( 'en' === $language ) { return home_url( '/en/my-account/' ); }
    return home_url( '/mi-cuenta/' );
}

function make_shop_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/shop/' : '/tienda/' );
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

function make_pattern_url( string $query ): string { return add_query_arg( 's', $query, make_search_url() ); }


function make_editorial_post_link( string $url, WP_Post $post, bool $leavename = false, bool $sample = false ): string {
    if ( 'post' !== $post->post_type ) { return $url; }
    $language = (string) get_post_meta( $post->ID, '_make_language', true );
    if ( ! in_array( $language, array( 'es','en' ), true ) ) { return $url; }
    $slug = $leavename ? '%postname%' : $post->post_name;
    return trailingslashit( make_article_base_url( $language ) ) . rawurlencode( $slug ) . '/';
}
add_filter( 'post_link', 'make_editorial_post_link', 20, 4 );

function make_editorial_category_link( string $url, int $term_id ): string {
    $section_id = (string) get_term_meta( $term_id, '_make_section_id', true );
    $language   = (string) get_term_meta( $term_id, '_make_language', true );
    if ( '' === $section_id || ! in_array( $language, array( 'es','en' ), true ) ) { return $url; }
    $term = get_term( $term_id, 'category' );
    if ( ! $term instanceof WP_Term ) { return $url; }
    $base = 'en' === $language ? '/en/articles/section/' : '/articulos/seccion/';
    return home_url( $base . rawurlencode( $term->slug ) . '/' );
}
add_filter( 'category_link', 'make_editorial_category_link', 20, 2 );

function make_redirect_legacy_language_query(): void {
    if ( is_admin() || ! isset( $_GET['make_lang'] ) ) { return; }
    $language = sanitize_key( (string) wp_unslash( $_GET['make_lang'] ) );
    if ( ! in_array( $language, array( 'es','en' ), true ) ) { return; }

    $target = make_language_switch_url( $language );
    $args = array();
    $query = isset( $_SERVER['QUERY_STRING'] ) ? (string) wp_unslash( $_SERVER['QUERY_STRING'] ) : '';
    if ( '' !== $query ) {
        parse_str( $query, $args );
        unset( $args['make_lang'] );
    }
    if ( ! empty( $args ) ) { $target = add_query_arg( $args, $target ); }

    wp_safe_redirect( $target, 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_language_query', -85 );

function make_redirect_legacy_editorial_paths(): void {
    if ( is_admin() || is_feed() || is_preview() ) { return; }

    $target = '';
    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $page  = max( 1, (int) get_query_var( 'paged' ) );
        $craft = function_exists( 'make_current_editorial_craft' ) ? make_current_editorial_craft() : '';
        $section = function_exists( 'make_current_editorial_craft_section' ) ? make_current_editorial_craft_section() : '';
        $theme = make_current_stitch_theme();
        if ( '' !== $craft && function_exists( 'make_editorial_craft_url' ) ) {
            $target = '' !== $section && function_exists( 'make_editorial_craft_section_url' )
                ? make_editorial_craft_section_url( $craft, $section, make_current_language(), $page )
                : make_editorial_craft_url( $craft, make_current_language(), $page );
        } else {
            $target = '' !== $theme ? make_stitch_theme_url( $theme, make_current_language(), $page ) : make_journal_page_url( $page, make_current_language() );
        }
    } elseif ( is_singular( 'post' ) ) {
        $target = get_permalink( get_queried_object_id() );
    } elseif ( is_category() ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term && '' !== (string) get_term_meta( $term->term_id, '_make_section_id', true ) ) {
            $link = get_category_link( $term );
            if ( ! is_wp_error( $link ) ) { $target = $link; }
        }
    }

    if ( '' === $target ) { return; }
    $current_path = make_request_path();
    $target_path  = '/' . trim( (string) wp_parse_url( $target, PHP_URL_PATH ), '/' );
    if ( $current_path === $target_path ) { return; }

    wp_safe_redirect( $target, 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_editorial_paths', 2 );

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
add_filter( 'loop_shop_per_page', static fn(): int => 20, 20 );

function make_related_product_layout( array $args ): array {
    $args['posts_per_page'] = 4;
    $args['columns'] = 4;
    return $args;
}
add_filter( 'woocommerce_output_related_products_args', 'make_related_product_layout', 20 );

function make_related_products_heading(): string {
    return make_t( 'Productos relacionados', 'Related products' );
}
add_filter( 'woocommerce_product_related_products_heading', 'make_related_products_heading', 20 );

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
                'description' => 'Técnicas, materiales y respuestas claras para crear con más seguridad.',
            ),
            'en' => array(
                'slug' => 'learn',
                'label' => 'Learn',
                'description' => 'Techniques, materials and clear answers for making with more confidence.',
            ),
        ),
        'ideas' => array(
            'es' => array(
                'slug' => 'ideas',
                'label' => 'Ideas e inspiración',
                'description' => 'Temas, estilos y proyectos para encontrar algo que de verdad apetezca crear.',
            ),
            'en' => array(
                'slug' => 'inspiration',
                'label' => 'Ideas & inspiration',
                'description' => 'Themes, styles and projects for finding something you genuinely want to make.',
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
    if ( function_exists( 'make_article_craft' ) && function_exists( 'make_editorial_craft_art_html' ) ) {
        $craft = make_article_craft( $post_id );
        if ( 'cross-stitch' !== $craft ) {
            return make_editorial_craft_art_html( $craft, 'make-editorial-art' );
        }
    }
    return make_stitch_theme_art_html( make_article_stitch_theme( $post_id ), 'make-editorial-art' );
}

function make_related_articles( int $post_id, int $limit = 3 ): array {
    $language = (string) get_post_meta( $post_id, '_make_language', true );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $weighted_taxonomies = array(
        'make_craft'        => 20,
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
        $fallback_args = array(
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
        );
        if ( ! empty( $source_terms['make_craft'] ) ) {
            $fallback_args['tax_query'] = array(
                array(
                    'taxonomy' => 'make_craft',
                    'field'    => 'term_id',
                    'terms'    => $source_terms['make_craft'],
                ),
            );
        }
        $fallback = get_posts( $fallback_args );
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

    if ( is_singular( 'product' ) ) {
        $language  = make_current_language();
        $seo_title = trim( (string) get_post_meta( get_queried_object_id(), '_drielo_seo_title_' . $language, true ) );
        if ( '' !== $seo_title ) { return $seo_title; }
    }

    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $craft = function_exists( 'make_current_editorial_craft' ) ? make_current_editorial_craft() : '';
        $crafts = function_exists( 'make_editorial_craft_config' ) ? make_editorial_craft_config() : array();
        if ( '' !== $craft && isset( $crafts[ $craft ][ make_current_language() ]['label'] ) ) {
            $section = function_exists( 'make_current_editorial_craft_section' ) ? make_current_editorial_craft_section() : '';
            $sections = make_editorial_section_config();
            $suffix = '' !== $section && isset( $sections[ $section ][ make_current_language() ]['label'] )
                ? (string) $sections[ $section ][ make_current_language() ]['label']
                : make_t( 'Guías y tutoriales', 'Guides & tutorials' );
            return $crafts[ $craft ][ make_current_language() ]['label'] . ' · ' . $suffix . ' | ' . make_brand_name();
        }

        $theme = function_exists( 'make_current_stitch_theme' ) ? make_current_stitch_theme() : '';
        $config = function_exists( 'make_stitch_theme_config' ) ? make_stitch_theme_config() : array();
        if ( '' !== $theme && isset( $config[ $theme ][ make_current_language() ]['label'] ) ) {
            return $config[ $theme ][ make_current_language() ]['label'] . ' · ' . make_t( 'Punto de cruz', 'Cross stitch' ) . ' | ' . make_brand_name();
        }
        return make_t( 'Guías de punto de cruz, crochet y latch hook', 'Cross stitch, crochet and latch hook guides' ) . ' | ' . make_brand_name();
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
        $canonical = get_permalink( $post_id );

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
    } elseif ( is_singular( 'product' ) ) {
        $post_id  = get_queried_object_id();
        $language = make_current_language();
        $description = trim( (string) get_post_meta( $post_id, '_drielo_meta_description_' . $language, true ) );
        $canonical = function_exists( 'make_product_url' ) ? make_product_url( $post_id, $language ) : get_permalink( $post_id );

        if ( ! function_exists( 'pll_current_language' ) ) {
            $es_url = function_exists( 'make_product_url' ) ? make_product_url( $post_id, 'es' ) : get_permalink( $post_id );
            $en_url = function_exists( 'make_product_url' ) ? make_product_url( $post_id, 'en' ) : get_permalink( $post_id );
            echo '<link rel="alternate" hreflang="es-ES" href="' . esc_url( $es_url ) . '">' . "\n";
            echo '<link rel="alternate" hreflang="en-US" href="' . esc_url( $en_url ) . '">' . "\n";
            echo '<link rel="alternate" hreflang="x-default" href="' . esc_url( $es_url ) . '">' . "\n";
        }
    } elseif ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $page = max( 1, (int) get_query_var( 'paged' ) );
        $craft = function_exists( 'make_current_editorial_craft' ) ? make_current_editorial_craft() : '';
        $crafts = function_exists( 'make_editorial_craft_config' ) ? make_editorial_craft_config() : array();
        $theme = function_exists( 'make_current_stitch_theme' ) ? make_current_stitch_theme() : '';

        if ( '' !== $craft && isset( $crafts[ $craft ][ make_current_language() ] ) ) {
            $description = (string) $crafts[ $craft ][ make_current_language() ]['meta_description'];
            $section = function_exists( 'make_current_editorial_craft_section' ) ? make_current_editorial_craft_section() : '';
            $canonical = '' !== $section && function_exists( 'make_editorial_craft_section_url' )
                ? make_editorial_craft_section_url( $craft, $section, make_current_language(), $page )
                : make_editorial_craft_url( $craft, make_current_language(), $page );
        } else {
            $description = make_t(
                'Guías prácticas de punto de cruz, C2C crochet, tapestry crochet y latch hook para aprender, resolver dudas y encontrar tu siguiente proyecto.',
                'Practical cross stitch, C2C crochet, tapestry crochet and latch hook guides for learning, solving problems and finding your next project.'
            );
            $canonical = '' !== $theme ? make_stitch_theme_url( $theme, make_current_language(), $page ) : make_journal_page_url( $page );
        }

        foreach ( array( 'es' => 'es-ES', 'en' => 'en-US' ) as $lang => $hreflang ) {
            if ( '' !== $craft && function_exists( 'make_editorial_craft_url' ) ) {
                $section = function_exists( 'make_current_editorial_craft_section' ) ? make_current_editorial_craft_section() : '';
                $url = '' !== $section && function_exists( 'make_editorial_craft_section_url' )
                    ? make_editorial_craft_section_url( $craft, $section, $lang, $page )
                    : make_editorial_craft_url( $craft, $lang, $page );
            } else {
                $url = '' !== $theme ? make_stitch_theme_url( $theme, $lang, $page ) : make_journal_page_url( $page, $lang );
            }
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
            'es' => array( 'slug'=>'flores-y-botanica', 'label'=>'Flores y botánica', 'description'=>'Flores, hojas, plantas y motivos naturales.' ),
            'en' => array( 'slug'=>'florals', 'label'=>'Florals & botanical', 'description'=>'Flowers, leaves, plants and botanical motifs.' ),
            'topic' => array( 'florals','nature','gardening','spring' ),
            'style' => array( 'botanical' ),
        ),
        'animals' => array(
            'es' => array( 'slug'=>'animales-y-mascotas', 'label'=>'Animales y mascotas', 'description'=>'Gatos, perros y diseños para amantes de los animales.' ),
            'en' => array( 'slug'=>'animals-pets', 'label'=>'Animals & pets', 'description'=>'Cats, dogs and designs for animal lovers.' ),
            'topic' => array( 'animals','pets' ),
            'style' => array(),
        ),
        'pop-art' => array(
            'es' => array( 'slug'=>'pop-art', 'label'=>'Pop art', 'description'=>'Color, contraste y diseños con mucha personalidad.' ),
            'en' => array( 'label'=>'Pop art', 'description'=>'Color, contrast and designs with plenty of personality.' ),
            'topic' => array( 'pop-art' ),
            'style' => array( 'pop-art','modern' ),
        ),
        'retro' => array(
            'es' => array( 'slug'=>'retro-y-vintage', 'label'=>'Retro y vintage', 'description'=>'Guiños nostálgicos, formas setenteras y estética vintage.' ),
            'en' => array( 'slug'=>'retro-vintage', 'label'=>'Retro & vintage', 'description'=>'Nostalgic references, seventies shapes and vintage style.' ),
            'topic' => array( 'retro' ),
            'style' => array( 'retro','vintage' ),
        ),
        'geometric' => array(
            'es' => array( 'slug'=>'minimal-y-geometrico', 'label'=>'Minimal y geométrico', 'description'=>'Formas limpias, abstractas y fáciles de integrar en casa.' ),
            'en' => array( 'slug'=>'minimal-geometric', 'label'=>'Minimal & geometric', 'description'=>'Clean, abstract shapes that fit easily into modern homes.' ),
            'topic' => array( 'minimalist','geometric' ),
            'style' => array( 'minimalist','geometric' ),
        ),
        'celestial' => array(
            'es' => array( 'slug'=>'cielo-y-fantasia', 'label'=>'Cielo y fantasía', 'description'=>'Lunas, estrellas, constelaciones y motivos de fantasía.' ),
            'en' => array( 'slug'=>'celestial-fantasy', 'label'=>'Celestial & fantasy', 'description'=>'Moons, stars, constellations and fantasy motifs.' ),
            'topic' => array( 'celestial','fantasy' ),
            'style' => array(),
        ),
        'food' => array(
            'es' => array( 'slug'=>'comida-y-cafe', 'label'=>'Comida y café', 'description'=>'Café, repostería y pequeños diseños para cocinas con carácter.' ),
            'en' => array( 'slug'=>'food-coffee', 'label'=>'Food & coffee', 'description'=>'Coffee, baking and playful designs for kitchens with character.' ),
            'topic' => array( 'food','coffee','baking' ),
            'style' => array(),
        ),
        'quotes' => array(
            'es' => array( 'slug'=>'frases', 'label'=>'Frases', 'description'=>'Mensajes divertidos, modernos y pensados para regalar.' ),
            'en' => array( 'slug'=>'quotes', 'label'=>'Quotes', 'description'=>'Funny, modern messages made for stitching and gifting.' ),
            'topic' => array( 'quotes' ),
            'style' => array(),
        ),
        'seasonal' => array(
            'es' => array( 'slug'=>'temporada', 'label'=>'Temporada', 'description'=>'Navidad, Halloween, Pascua y estaciones del año.' ),
            'en' => array( 'slug'=>'seasonal', 'label'=>'Seasonal', 'description'=>'Christmas, Halloween, Easter and seasonal projects.' ),
            'topic' => array( 'christmas','halloween','easter','spring','autumn' ),
            'style' => array(),
        ),
    );
}

function make_current_stitch_theme(): string {
    $config = make_stitch_theme_config();
    $theme = sanitize_key( (string) get_query_var( 'make_theme' ) );
    if ( isset( $config[ $theme ] ) ) { return $theme; }

    $slug = sanitize_title( (string) get_query_var( 'make_theme_slug' ) );
    if ( '' === $slug ) { return ''; }
    $language = make_current_language();
    foreach ( $config as $id => $item ) {
        if ( isset( $item[ $language ]['slug'] ) && $slug === sanitize_title( (string) $item[ $language ]['slug'] ) ) {
            return (string) $id;
        }
    }
    return '';
}

function make_stitch_theme_url( string $theme, string $language = '', int $page = 1 ): string {
    $theme = sanitize_key( $theme );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $page = max( 1, $page );
    $config = make_stitch_theme_config();

    if ( ! isset( $config[ $theme ] ) ) { return make_journal_url( $language ); }
    $slug = sanitize_title( (string) ( $config[ $theme ][ $language ]['slug'] ?? $theme ) );

    $base = 'en' === $language
        ? home_url( '/en/articles/topic/' . rawurlencode( $slug ) . '/' )
        : home_url( '/articulos/tema/' . rawurlencode( $slug ) . '/' );

    return 1 === $page ? $base : trailingslashit( $base ) . 'page/' . $page . '/';
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

    $theme_query = array( 'relation'=>'OR' );
    if ( ! empty( $config[ $theme ]['topic'] ) ) {
        $theme_query[] = array(
            'taxonomy'=>'make_topic',
            'field'=>'slug',
            'terms'=>$config[ $theme ]['topic'],
        );
    }
    if ( ! empty( $config[ $theme ]['style'] ) ) {
        $theme_query[] = array(
            'taxonomy'=>'make_style',
            'field'=>'slug',
            'terms'=>$config[ $theme ]['style'],
        );
    }
    if ( count( $theme_query ) < 2 ) { return array(); }

    return array(
        'relation'=>'AND',
        array(
            'taxonomy'=>'make_craft',
            'field'=>'slug',
            'terms'=>array('cross-stitch'),
        ),
        $theme_query,
    );
}

function make_stitch_theme_query_var( array $vars ): array {
    $vars[] = 'make_theme';
    $vars[] = 'make_theme_slug';
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

function make_journal_pagination_html( WP_Query $query, string $language = '', string $theme = '', string $craft = '', string $section = '' ): string {
    $total = max( 1, (int) $query->max_num_pages );
    if ( $total < 2 ) { return ''; }

    $current = max( 1, (int) get_query_var( 'paged' ) );
    $language = in_array( $language, array('es','en'), true ) ? $language : make_current_language();
    $pages = array();

    $link = static function( int $page, string $label, string $class = '' ) use ( $language, $theme, $craft, $section ): string {
        if ( '' !== $craft && function_exists( 'make_editorial_craft_url' ) ) {
            $url = '' !== $section && function_exists( 'make_editorial_craft_section_url' )
                ? make_editorial_craft_section_url( $craft, $section, $language, $page )
                : make_editorial_craft_url( $craft, $language, $page );
        } else {
            $url = '' !== $theme ? make_stitch_theme_url( $theme, $language, $page ) : make_journal_page_url( $page, $language );
        }
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


/* Drielo professional storefront pages v1 */

function make_contact_recipient(): string {
    return 'tostis005@gmail.com';
}

function make_contact_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/contact/' : '/contacto/' );
}

function make_privacy_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/privacy/' : '/privacidad/' );
}

function make_refund_policy_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/refunds/' : '/reembolsos/' );
}

function make_terms_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    return home_url( 'en' === $language ? '/en/terms/' : '/terminos-y-condiciones/' );
}

function make_info_page_key(): string {
    $key = sanitize_key( (string) get_query_var( 'make_info_page' ) );
    return in_array( $key, array( 'contact', 'privacy', 'refunds', 'terms' ), true ) ? $key : '';
}

function make_info_page_url( string $key, string $language = '' ): string {
    if ( 'contact' === $key ) { return make_contact_url( $language ); }
    if ( 'privacy' === $key ) { return make_privacy_url( $language ); }
    if ( 'refunds' === $key ) { return make_refund_policy_url( $language ); }
    if ( 'terms' === $key ) { return make_terms_url( $language ); }
    return make_home_url( $language );
}

function make_info_page_title( string $key = '' ): string {
    $key = $key ?: make_info_page_key();
    $titles = array(
        'contact' => make_t( 'Contacto', 'Contact' ),
        'privacy' => make_t( 'Política de privacidad', 'Privacy policy' ),
        'refunds' => make_t( 'Política de reembolso', 'Refund policy' ),
        'terms'   => make_t( 'Términos y condiciones', 'Terms & conditions' ),
    );
    return $titles[ $key ] ?? make_brand_name();
}

function make_register_info_rewrites(): void {
    add_rewrite_rule( '^contacto/?$', 'index.php?make_info_page=contact&make_lang=es', 'top' );
    add_rewrite_rule( '^privacidad/?$', 'index.php?make_info_page=privacy&make_lang=es', 'top' );
    add_rewrite_rule( '^reembolsos/?$', 'index.php?make_info_page=refunds&make_lang=es', 'top' );
    add_rewrite_rule( '^terminos-y-condiciones/?$', 'index.php?make_info_page=terms&make_lang=es', 'top' );

    add_rewrite_rule( '^en/contact/?$', 'index.php?make_info_page=contact&make_lang=en', 'top' );
    add_rewrite_rule( '^en/privacy/?$', 'index.php?make_info_page=privacy&make_lang=en', 'top' );
    add_rewrite_rule( '^en/refunds/?$', 'index.php?make_info_page=refunds&make_lang=en', 'top' );
    add_rewrite_rule( '^en/terms/?$', 'index.php?make_info_page=terms&make_lang=en', 'top' );
}
add_action( 'init', 'make_register_info_rewrites', 21 );

function make_maybe_flush_info_rewrites(): void {
    $version = '1';
    if ( $version === (string) get_option( 'drielo_info_rewrite_schema', '' ) ) { return; }
    flush_rewrite_rules( false );
    update_option( 'drielo_info_rewrite_schema', $version, false );
}
add_action( 'init', 'make_maybe_flush_info_rewrites', 110 );

function make_info_query_vars( array $vars ): array {
    $vars[] = 'make_info_page';
    return $vars;
}
add_filter( 'query_vars', 'make_info_query_vars' );

function make_info_template_router( string $template ): string {
    if ( '' === make_info_page_key() ) { return $template; }
    $info_template = locate_template( 'page-info.php' );
    return $info_template ?: $template;
}
add_filter( 'template_include', 'make_info_template_router', 98 );

function make_info_page_status(): void {
    if ( '' === make_info_page_key() ) { return; }
    global $wp_query;
    if ( $wp_query instanceof WP_Query ) {
        $wp_query->is_404 = false;
        $wp_query->is_page = true;
    }
    status_header( 200 );
}
add_action( 'template_redirect', 'make_info_page_status', -50 );

add_filter( 'redirect_canonical', static function ( $redirect_url ) {
    return '' !== make_info_page_key() ? false : $redirect_url;
}, 10, 1 );

add_filter( 'pre_get_document_title', static function ( string $title ): string {
    return '' !== make_info_page_key() ? make_info_page_title() . ' — ' . make_brand_name() : $title;
}, 20 );

function make_info_page_canonical(): void {
    $key = make_info_page_key();
    if ( '' === $key ) { return; }
    echo '<link rel="canonical" href="' . esc_url( make_info_page_url( $key ) ) . '">' . "\n";
}
add_action( 'wp_head', 'make_info_page_canonical', 4 );

function make_register_contact_message_type(): void {
    register_post_type(
        'drielo_contact',
        array(
            'labels' => array(
                'name'          => 'Contact messages',
                'singular_name' => 'Contact message',
                'menu_name'     => 'Contact messages',
            ),
            'public'              => false,
            'show_ui'             => true,
            'show_in_menu'        => true,
            'menu_icon'           => 'dashicons-email-alt',
            'supports'            => array( 'title', 'editor' ),
            'exclude_from_search' => true,
            'show_in_rest'        => false,
        )
    );
}
add_action( 'init', 'make_register_contact_message_type', 8 );

function make_contact_redirect( string $language, array $args = array() ): void {
    $url = make_contact_url( $language );
    if ( $args ) { $url = add_query_arg( $args, $url ); }
    wp_safe_redirect( $url );
    exit;
}

function make_contact_form_handler(): void {
    $language = isset( $_POST['contact_language'] ) ? sanitize_key( (string) wp_unslash( $_POST['contact_language'] ) ) : 'es';
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : 'es';

    if (
        ! isset( $_POST['make_contact_nonce'] ) ||
        ! wp_verify_nonce( sanitize_text_field( (string) wp_unslash( $_POST['make_contact_nonce'] ) ), 'make_contact_form' )
    ) {
        make_contact_redirect( $language, array( 'contact_error' => 'security' ) );
    }

    $honeypot = isset( $_POST['company'] ) ? trim( (string) wp_unslash( $_POST['company'] ) ) : '';
    $started  = isset( $_POST['started_at'] ) ? absint( $_POST['started_at'] ) : 0;
    $elapsed  = $started > 0 ? time() - $started : 0;

    if ( '' !== $honeypot || $elapsed < 2 || $elapsed > 7200 ) {
        make_contact_redirect( $language, array( 'sent' => '1' ) );
    }

    $name    = isset( $_POST['contact_name'] ) ? sanitize_text_field( (string) wp_unslash( $_POST['contact_name'] ) ) : '';
    $email   = isset( $_POST['contact_email'] ) ? sanitize_email( (string) wp_unslash( $_POST['contact_email'] ) ) : '';
    $message = isset( $_POST['contact_message'] ) ? sanitize_textarea_field( (string) wp_unslash( $_POST['contact_message'] ) ) : '';
    $privacy = ! empty( $_POST['privacy_accept'] );

    if ( '' === $name || ! is_email( $email ) || mb_strlen( $message ) < 10 || mb_strlen( $message ) > 5000 || ! $privacy ) {
        make_contact_redirect( $language, array( 'contact_error' => 'fields' ) );
    }

    $ip = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( (string) wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : 'unknown';
    $rate_key = 'drielo_contact_' . md5( $ip . wp_salt( 'nonce' ) );
    $rate_count = (int) get_transient( $rate_key );

    if ( $rate_count >= 5 ) {
        make_contact_redirect( $language, array( 'contact_error' => 'rate' ) );
    }
    set_transient( $rate_key, $rate_count + 1, HOUR_IN_SECONDS );

    $post_id = wp_insert_post(
        array(
            'post_type'    => 'drielo_contact',
            'post_status'  => 'private',
            'post_title'   => wp_strip_all_tags( $name . ' — ' . $email ),
            'post_content' => $message,
        ),
        true
    );

    if ( ! is_wp_error( $post_id ) && $post_id ) {
        update_post_meta( (int) $post_id, '_drielo_contact_name', $name );
        update_post_meta( (int) $post_id, '_drielo_contact_email', $email );
        update_post_meta( (int) $post_id, '_drielo_contact_language', $language );
    }

    $subject = '[Drielo] ' . ( 'en' === $language ? 'New contact message' : 'Nuevo mensaje de contacto' ) . ' — ' . mb_substr( $name, 0, 80 );
    $body = "Nombre / Name: {$name}\nEmail: {$email}\nIdioma / Language: {$language}\n\nMensaje / Message:\n{$message}\n";
    $headers = array(
        'Content-Type: text/plain; charset=UTF-8',
        'Reply-To: ' . $name . ' <' . $email . '>',
    );

    $mail_sent = wp_mail( make_contact_recipient(), $subject, $body, $headers );

    if ( ! is_wp_error( $post_id ) && $post_id ) {
        update_post_meta( (int) $post_id, '_drielo_contact_mail_sent', $mail_sent ? 'yes' : 'no' );
    }

    make_contact_redirect( $language, array( 'sent' => '1' ) );
}
add_action( 'admin_post_nopriv_make_contact', 'make_contact_form_handler' );
add_action( 'admin_post_make_contact', 'make_contact_form_handler' );

function make_cart_has_digital_content(): bool {
    if ( ! function_exists( 'WC' ) || ! WC()->cart ) { return false; }
    foreach ( WC()->cart->get_cart() as $item ) {
        $product = isset( $item['data'] ) && $item['data'] instanceof WC_Product ? $item['data'] : null;
        if ( $product && ( $product->is_downloadable() || $product->is_virtual() ) ) { return true; }
    }
    return false;
}

function make_digital_content_checkout_consent(): void {
    if ( ! make_cart_has_digital_content() ) { return; }
    $label = make_t(
        'Solicito el acceso inmediato al contenido digital y reconozco que, cuando la ley aplicable lo permita, al comenzar la descarga o el acceso puedo perder el derecho de desistimiento correspondiente.',
        'I request immediate access to the digital content and acknowledge that, where applicable law allows, once download or access begins I may lose the relevant right of withdrawal.'
    );
    woocommerce_form_field(
        'make_digital_content_consent',
        array(
            'type'     => 'checkbox',
            'class'    => array( 'form-row', 'make-digital-consent' ),
            'required' => true,
            'label'    => $label,
        ),
        WC()->checkout()->get_value( 'make_digital_content_consent' )
    );
}
add_action( 'woocommerce_review_order_before_submit', 'make_digital_content_checkout_consent', 8 );

function make_validate_digital_content_checkout_consent(): void {
    if ( make_cart_has_digital_content() && empty( $_POST['make_digital_content_consent'] ) ) {
        wc_add_notice(
            make_t(
                'Confirma el acceso inmediato al contenido digital para continuar.',
                'Please confirm immediate access to the digital content to continue.'
            ),
            'error'
        );
    }
}
add_action( 'woocommerce_checkout_process', 'make_validate_digital_content_checkout_consent' );

function make_save_digital_content_checkout_consent( WC_Order $order ): void {
    if ( ! empty( $_POST['make_digital_content_consent'] ) ) {
        $order->update_meta_data( '_drielo_digital_content_consent', 'yes' );
        $order->update_meta_data( '_drielo_digital_content_consent_at', gmdate( 'c' ) );
    }
}
add_action( 'woocommerce_checkout_create_order', 'make_save_digital_content_checkout_consent', 10, 1 );
