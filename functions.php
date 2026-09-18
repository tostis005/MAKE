<?php
/** MAKE theme functions. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

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
    add_image_size( 'make-journal', 900, 560, true );
    register_nav_menus( array( 'primary' => __( 'Primary menu', 'make' ), 'footer' => __( 'Footer menu', 'make' ) ) );
}
add_action( 'after_setup_theme', 'make_theme_setup' );

function make_assets(): void {
    $version = wp_get_theme()->get( 'Version' ) ?: '1.0.0';
    wp_enqueue_style( 'make-style', get_stylesheet_uri(), array(), $version );
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
    return 'en' === $language ? home_url( '/en/' ) : home_url( '/' );
}

function make_language_switch_url( string $language ): string {
    $language = in_array( $language, array( 'es','en' ), true ) ? $language : 'es';
    if ( is_singular() && function_exists( 'pll_get_post' ) ) {
        $translated = (int) pll_get_post( get_queried_object_id(), $language );
        if ( $translated ) { return get_permalink( $translated ); }
    }
    if ( is_search() ) { return add_query_arg( 's', get_search_query(), make_home_url( $language ) ); }
    return make_home_url( $language );
}

function make_rewrite_rules(): void {
    add_rewrite_rule( '^en/?$', 'index.php?make_lang=en', 'top' );
}
add_action( 'init', 'make_rewrite_rules' );

function make_query_vars( array $vars ): array { $vars[] = 'make_lang'; return $vars; }
add_filter( 'query_vars', 'make_query_vars' );

function make_front_template( string $template ): string {
    if ( '/en' === make_request_path() ) {
        $front = locate_template( 'front-page.php' );
        if ( $front ) { return $front; }
    }
    return $template;
}
add_filter( 'template_include', 'make_front_template', 99 );

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
    $name = trim( (string) get_bloginfo( 'name' ) );
    return $name !== '' ? $name : make_t( 'Taller creativo', 'Creative studio' );
}

function make_brand_tagline(): string {
    $tagline = trim( (string) get_bloginfo( 'description' ) );
    return $tagline !== '' ? $tagline : make_t( 'patrones digitales para crear despacio', 'digital patterns for slow making' );
}

function make_journal_url(): string {
    $posts_page = (int) get_option( 'page_for_posts' );
    if ( $posts_page ) {
        $url = get_permalink( $posts_page );
        if ( $url ) { return $url; }
    }
    return home_url( '/journal/' );
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

add_filter( 'loop_shop_columns', static fn(): int => 3, 20 );
add_filter( 'loop_shop_per_page', static fn(): int => 12, 20 );

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
