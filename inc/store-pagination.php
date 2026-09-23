<?php
/**
 * Drielo storefront pagination.
 *
 * Kept separate from store.php so pagination routing and canonical redirects
 * cannot interfere with product/collection route code.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function make_store_pagination_routes(): void {
    add_rewrite_rule( '^tienda/page/([0-9]+)/?$', 'index.php?post_type=product&make_lang=es&paged=$matches[1]', 'top' );
    add_rewrite_rule( '^en/shop/page/([0-9]+)/?$', 'index.php?post_type=product&make_lang=en&paged=$matches[1]', 'top' );
}
add_action( 'init', 'make_store_pagination_routes', 19 );

function make_store_pagination_maybe_flush_rewrites(): void {
    $version = '1';
    if ( $version === (string) get_option( 'drielo_store_pagination_schema', '' ) ) { return; }

    flush_rewrite_rules( false );
    update_option( 'drielo_store_pagination_schema', $version, false );
}
add_action( 'init', 'make_store_pagination_maybe_flush_rewrites', 101 );

remove_action( 'template_redirect', 'make_redirect_legacy_store_paths', 3 );

function make_redirect_legacy_store_paths_paginated(): void {
    if ( is_admin() || is_feed() || is_preview() || isset( $_GET['make_lang'] ) ) { return; }

    $target = '';
    if ( function_exists( 'is_product' ) && is_product() ) {
        $target = make_product_url( get_queried_object_id(), make_current_language() );
    } elseif ( is_tax( array( 'product_collection','product_cat' ) ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) { $target = make_store_term_url( $term, make_current_language() ); }
    } elseif ( function_exists( 'is_shop' ) && is_shop() ) {
        $target = make_shop_view_url( make_store_view(), make_current_language() );
        $page = max( 1, (int) get_query_var( 'paged' ) );
        if ( $page > 1 && 'patterns' === make_store_view() ) {
            $target = trailingslashit( $target ) . 'page/' . $page . '/';
        }
    } elseif ( function_exists( 'is_cart' ) && is_cart() ) {
        $target = make_cart_url( make_current_language() );
    } elseif ( function_exists( 'is_checkout' ) && is_checkout() ) {
        $target = make_store_current_endpoint_url( make_current_language(), 'checkout' );
        if ( '' === $target ) { $target = make_checkout_url( make_current_language() ); }
    } elseif ( function_exists( 'is_account_page' ) && is_account_page() ) {
        $target = make_store_current_endpoint_url( make_current_language(), 'account' );
        if ( '' === $target ) { $target = make_account_url( make_current_language() ); }
    }

    if ( '' === $target ) { return; }

    $request = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
    $current_path = '/' . trim( (string) wp_parse_url( $request, PHP_URL_PATH ), '/' );
    $target_path  = '/' . trim( (string) wp_parse_url( $target, PHP_URL_PATH ), '/' );

    if ( $current_path === $target_path ) { return; }

    $preserve = array();
    foreach ( $_GET as $key => $value ) {
        $key = sanitize_key( (string) $key );
        if ( 'currency' === $key || 0 === strpos( $key, 'drielo_' ) ) {
            $preserve[ $key ] = is_array( $value )
                ? array_map( 'sanitize_text_field', wp_unslash( $value ) )
                : sanitize_text_field( wp_unslash( $value ) );
        }
    }
    if ( $preserve ) { $target = add_query_arg( $preserve, $target ); }

    wp_safe_redirect( $target, 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_store_paths_paginated', 3 );
