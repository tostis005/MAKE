<?php
/**
 * Drielo storefront extensions.
 *
 * Every pattern is an individual WooCommerce downloadable product.
 * product_collection groups interchangeable designs that share a thread palette.
 * USD is the default checkout currency; shoppers can switch to EUR.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

const DRIELO_DEFAULT_PRODUCT_PRICE = 4.99;
const DRIELO_COLLECTION_ADDON_PRICE = 1.49;
const DRIELO_DEFAULT_CURRENCY = 'USD';

function make_register_store_taxonomies(): void {
    register_taxonomy(
        'product_collection',
        array( 'product' ),
        array(
            'labels' => array(
                'name'          => __( 'Collections', 'make' ),
                'singular_name' => __( 'Collection', 'make' ),
                'menu_name'     => __( 'Collections', 'make' ),
                'all_items'     => __( 'All collections', 'make' ),
                'edit_item'     => __( 'Edit collection', 'make' ),
                'add_new_item'  => __( 'Add collection', 'make' ),
                'search_items'  => __( 'Search collections', 'make' ),
            ),
            'public'            => true,
            'show_ui'           => true,
            'show_admin_column' => true,
            'show_in_rest'      => true,
            'hierarchical'      => false,
            'rewrite'           => array( 'slug' => 'collection', 'with_front' => false ),
            'query_var'         => true,
        )
    );
}
add_action( 'init', 'make_register_store_taxonomies', 6 );


function make_redirect_legacy_collection_url(): void {
    if ( is_admin() ) { return; }

    $request_uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '';
    $path = (string) wp_parse_url( $request_uri, PHP_URL_PATH );
    if ( ! preg_match( '#/collection/marilyn-pop-portraits/?$#i', $path ) ) { return; }

    $term = get_term_by( 'slug', 'pop-art-portraits', 'product_collection' );
    if ( ! $term instanceof WP_Term ) { return; }
    $url = make_store_term_url( $term, 'es' );

    wp_safe_redirect( $url, 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_collection_url', 1 );

function make_store_routes(): void {
    add_rewrite_rule( '^en/shop/?$', 'index.php?post_type=product&make_lang=en', 'top' );

    add_rewrite_rule( '^tienda/colecciones/?$', 'index.php?post_type=product&make_store_view=collections&make_lang=es', 'top' );
    add_rewrite_rule( '^en/shop/collections/?$', 'index.php?post_type=product&make_store_view=collections&make_lang=en', 'top' );

    add_rewrite_rule( '^tienda/coleccion/([a-z0-9-]+)/?$', 'index.php?make_collection_local=$matches[1]&make_lang=es', 'top' );
    add_rewrite_rule( '^en/shop/collection/([a-z0-9-]+)/?$', 'index.php?make_collection_local=$matches[1]&make_lang=en', 'top' );
    add_rewrite_rule( '^tienda/categoria/([a-z0-9-]+)/?$', 'index.php?make_product_cat_local=$matches[1]&make_lang=es', 'top' );
    add_rewrite_rule( '^en/shop/category/([a-z0-9-]+)/?$', 'index.php?make_product_cat_local=$matches[1]&make_lang=en', 'top' );

    add_rewrite_rule( '^tienda/(?!colecciones/?$|coleccion/|categoria/)([a-z0-9-]+)/?$', 'index.php?post_type=product&make_product_slug=$matches[1]&make_lang=es', 'top' );
    add_rewrite_rule( '^en/shop/(?!collections/?$|collection/|category/)([a-z0-9-]+)/?$', 'index.php?post_type=product&make_product_slug=$matches[1]&make_lang=en', 'top' );

    add_rewrite_rule( '^tienda/collections/?$', 'index.php?post_type=product&make_store_view=collections&make_lang=en', 'top' );

    $cart_id     = function_exists( 'wc_get_page_id' ) ? (int) wc_get_page_id( 'cart' ) : 0;
    $checkout_id = function_exists( 'wc_get_page_id' ) ? (int) wc_get_page_id( 'checkout' ) : 0;
    $account_id  = function_exists( 'wc_get_page_id' ) ? (int) wc_get_page_id( 'myaccount' ) : 0;

    if ( $cart_id > 0 ) {
        add_rewrite_rule( '^carrito/?$', 'index.php?page_id=' . $cart_id . '&make_lang=es', 'top' );
        add_rewrite_rule( '^en/cart/?$', 'index.php?page_id=' . $cart_id . '&make_lang=en', 'top' );
    }
    if ( $checkout_id > 0 ) {
        add_rewrite_rule( '^finalizar-compra/?$', 'index.php?page_id=' . $checkout_id . '&make_lang=es', 'top' );
        add_rewrite_rule( '^en/checkout/?$', 'index.php?page_id=' . $checkout_id . '&make_lang=en', 'top' );
        foreach ( array( 'order-pay', 'order-received' ) as $endpoint ) {
            $es_slug = make_store_endpoint_slug( $endpoint, 'es' );
            $en_slug = make_store_endpoint_slug( $endpoint, 'en' );
            add_rewrite_rule( '^finalizar-compra/' . preg_quote( $es_slug, '#' ) . '/([^/]+)/?$', 'index.php?page_id=' . $checkout_id . '&' . $endpoint . '=$matches[1]&make_lang=es', 'top' );
            add_rewrite_rule( '^en/checkout/' . preg_quote( $en_slug, '#' ) . '/([^/]+)/?$', 'index.php?page_id=' . $checkout_id . '&' . $endpoint . '=$matches[1]&make_lang=en', 'top' );
        }
    }
    if ( $account_id > 0 ) {
        add_rewrite_rule( '^mi-cuenta/?$', 'index.php?page_id=' . $account_id . '&make_lang=es', 'top' );
        add_rewrite_rule( '^en/my-account/?$', 'index.php?page_id=' . $account_id . '&make_lang=en', 'top' );
        foreach ( array( 'orders','downloads','edit-account','edit-address','payment-methods','add-payment-method','lost-password','customer-logout' ) as $endpoint ) {
            $es_slug = make_store_endpoint_slug( $endpoint, 'es' );
            $en_slug = make_store_endpoint_slug( $endpoint, 'en' );
            add_rewrite_rule( '^mi-cuenta/' . preg_quote( $es_slug, '#' ) . '/?$', 'index.php?page_id=' . $account_id . '&' . $endpoint . '=1&make_lang=es', 'top' );
            add_rewrite_rule( '^mi-cuenta/' . preg_quote( $es_slug, '#' ) . '/([^/]+)/?$', 'index.php?page_id=' . $account_id . '&' . $endpoint . '=$matches[1]&make_lang=es', 'top' );
            add_rewrite_rule( '^en/my-account/' . preg_quote( $en_slug, '#' ) . '/?$', 'index.php?page_id=' . $account_id . '&' . $endpoint . '=1&make_lang=en', 'top' );
            add_rewrite_rule( '^en/my-account/' . preg_quote( $en_slug, '#' ) . '/([^/]+)/?$', 'index.php?page_id=' . $account_id . '&' . $endpoint . '=$matches[1]&make_lang=en', 'top' );
        }
    }
}
add_action( 'init', 'make_store_routes', 20 );

function make_store_query_vars( array $vars ): array {
    $vars[] = 'make_store_view';
    $vars[] = 'make_product_slug';
    $vars[] = 'make_collection_local';
    $vars[] = 'make_product_cat_local';
    return $vars;
}
add_filter( 'query_vars', 'make_store_query_vars' );

function make_store_maybe_flush_rewrites(): void {
    $schema_version = '4';
    if ( $schema_version === (string) get_option( 'drielo_store_schema_version', '' ) ) { return; }
    flush_rewrite_rules( false );
    update_option( 'drielo_store_schema_version', $schema_version, false );
}
add_action( 'init', 'make_store_maybe_flush_rewrites', 99 );


function make_product_local_slug( $product, string $language = '' ): string {
    $post = $product instanceof WP_Post ? $product : get_post( is_object( $product ) && method_exists( $product, 'get_id' ) ? $product->get_id() : (int) $product );
    if ( ! $post instanceof WP_Post || 'product' !== $post->post_type ) { return ''; }

    $language = in_array( $language, array( 'es','en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );

    if ( 'en' === $language ) { return sanitize_title( $post->post_name ); }

    $saved = trim( (string) get_post_meta( $post->ID, '_drielo_slug_es', true ) );
    if ( '' !== $saved ) { return sanitize_title( $saved ); }

    $title = trim( (string) get_post_meta( $post->ID, '_drielo_title_es', true ) );
    if ( '' === $title ) { $title = $post->post_title; }
    return sanitize_title( $title . ' patron punto de cruz' );
}

function make_product_url( $product, string $language = '' ): string {
    $post = $product instanceof WP_Post ? $product : get_post( is_object( $product ) && method_exists( $product, 'get_id' ) ? $product->get_id() : (int) $product );
    if ( ! $post instanceof WP_Post ) { return function_exists( 'make_shop_url' ) ? make_shop_url( $language ) : home_url( '/tienda/' ); }

    $language = in_array( $language, array( 'es','en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );
    $slug = make_product_local_slug( $post, $language );
    $base = 'en' === $language ? '/en/shop/' : '/tienda/';
    return home_url( $base . rawurlencode( $slug ) . '/' );
}

function make_store_term_local_slug( WP_Term $term, string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );
    if ( 'en' === $language ) { return sanitize_title( $term->slug ); }

    $name = trim( (string) get_term_meta( $term->term_id, 'drielo_name_es', true ) );
    if ( '' === $name ) { $name = $term->name; }
    return sanitize_title( $name );
}

function make_store_term_url( WP_Term $term, string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );
    $slug = make_store_term_local_slug( $term, $language );

    if ( 'product_collection' === $term->taxonomy ) {
        $base = 'en' === $language ? '/en/shop/collection/' : '/tienda/coleccion/';
        return home_url( $base . rawurlencode( $slug ) . '/' );
    }
    if ( 'product_cat' === $term->taxonomy ) {
        $base = 'en' === $language ? '/en/shop/category/' : '/tienda/categoria/';
        return home_url( $base . rawurlencode( $slug ) . '/' );
    }
    return home_url( '/' );
}

function make_store_find_product_by_local_slug( string $slug, string $language ): int {
    static $cache = array();
    $key = $language . ':' . $slug;
    if ( isset( $cache[ $key ] ) ) { return $cache[ $key ]; }

    $ids = get_posts( array(
        'post_type' => 'product',
        'post_status' => 'publish',
        'posts_per_page' => -1,
        'fields' => 'ids',
        'meta_key' => '_drielo_managed_product',
        'meta_value' => '1',
        'no_found_rows' => true,
    ) );
    foreach ( $ids as $id ) {
        if ( $slug === make_product_local_slug( (int) $id, $language ) ) {
            return $cache[ $key ] = (int) $id;
        }
    }
    return $cache[ $key ] = 0;
}

function make_store_find_term_by_local_slug( string $taxonomy, string $slug, string $language ): ?WP_Term {
    $terms = get_terms( array( 'taxonomy' => $taxonomy, 'hide_empty' => false ) );
    if ( is_wp_error( $terms ) ) { return null; }
    foreach ( $terms as $term ) {
        if ( $term instanceof WP_Term && $slug === make_store_term_local_slug( $term, $language ) ) { return $term; }
    }
    return null;
}

function make_store_resolve_pretty_routes( array $vars ): array {
    $language = isset( $vars['make_lang'] ) && 'en' === $vars['make_lang'] ? 'en' : 'es';

    if ( ! empty( $vars['make_product_slug'] ) ) {
        $id = make_store_find_product_by_local_slug( sanitize_title( (string) $vars['make_product_slug'] ), $language );
        unset( $vars['make_product_slug'] );
        if ( $id > 0 ) {
            $vars['post_type'] = 'product';
            $vars['p'] = $id;
        }
    }

    if ( ! empty( $vars['make_collection_local'] ) ) {
        $term = make_store_find_term_by_local_slug( 'product_collection', sanitize_title( (string) $vars['make_collection_local'] ), $language );
        unset( $vars['make_collection_local'] );
        if ( $term instanceof WP_Term ) { $vars['product_collection'] = $term->slug; }
    }

    if ( ! empty( $vars['make_product_cat_local'] ) ) {
        $term = make_store_find_term_by_local_slug( 'product_cat', sanitize_title( (string) $vars['make_product_cat_local'] ), $language );
        unset( $vars['make_product_cat_local'] );
        if ( $term instanceof WP_Term ) { $vars['product_cat'] = $term->slug; }
    }

    return $vars;
}
add_filter( 'request', 'make_store_resolve_pretty_routes', 20 );

function make_store_endpoint_slug( string $endpoint, string $language = '' ): string {
    $language = in_array( $language, array( 'es','en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );
    $map = array(
        'orders'             => array( 'es'=>'pedidos', 'en'=>'orders' ),
        'downloads'          => array( 'es'=>'descargas', 'en'=>'downloads' ),
        'edit-account'       => array( 'es'=>'editar-cuenta', 'en'=>'edit-account' ),
        'edit-address'       => array( 'es'=>'editar-direccion', 'en'=>'edit-address' ),
        'payment-methods'    => array( 'es'=>'metodos-de-pago', 'en'=>'payment-methods' ),
        'add-payment-method' => array( 'es'=>'anadir-metodo-de-pago', 'en'=>'add-payment-method' ),
        'lost-password'      => array( 'es'=>'contrasena-perdida', 'en'=>'lost-password' ),
        'customer-logout'    => array( 'es'=>'cerrar-sesion', 'en'=>'customer-logout' ),
        'order-pay'          => array( 'es'=>'pagar-pedido', 'en'=>'order-pay' ),
        'order-received'     => array( 'es'=>'pedido-recibido', 'en'=>'order-received' ),
    );
    return isset( $map[ $endpoint ][ $language ] ) ? $map[ $endpoint ][ $language ] : sanitize_title( $endpoint );
}

function make_store_endpoint_url( string $endpoint, $value = '', string $language = '', string $context = 'account' ): string {
    $language = in_array( $language, array( 'es','en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );
    $base = 'checkout' === $context && function_exists( 'make_checkout_url' ) ? make_checkout_url( $language ) : make_account_url( $language );
    $url = trailingslashit( $base ) . rawurlencode( make_store_endpoint_slug( $endpoint, $language ) ) . '/';
    if ( '' !== (string) $value && '1' !== (string) $value ) { $url .= rawurlencode( (string) $value ) . '/'; }
    return $url;
}

function make_store_current_endpoint_url( string $language, string $context = 'account' ): string {
    $endpoints = 'checkout' === $context
        ? array( 'order-pay','order-received' )
        : array( 'orders','downloads','edit-account','edit-address','payment-methods','add-payment-method','lost-password','customer-logout' );
    foreach ( $endpoints as $endpoint ) {
        $value = get_query_var( $endpoint, null );
        if ( null !== $value && '' !== (string) $value ) {
            return make_store_endpoint_url( $endpoint, $value, $language, $context );
        }
    }
    return '';
}

function make_localize_store_post_link( string $url, $post ): string {
    if ( $post instanceof WP_Post && 'product' === $post->post_type ) {
        return make_product_url( $post );
    }
    return $url;
}
add_filter( 'post_type_link', 'make_localize_store_post_link', 20, 2 );

function make_localize_store_term_link( string $url, WP_Term $term, string $taxonomy ): string {
    if ( in_array( $taxonomy, array( 'product_collection', 'product_cat' ), true ) ) {
        return make_store_term_url( $term );
    }
    return $url;
}
add_filter( 'term_link', 'make_localize_store_term_link', 20, 3 );

function make_store_shop_page_permalink( string $url ): string {
    if ( is_admin() && ! wp_doing_ajax() ) { return $url; }
    return make_shop_url();
}
function make_store_cart_page_permalink( string $url ): string {
    if ( is_admin() && ! wp_doing_ajax() ) { return $url; }
    return make_cart_url();
}
function make_store_checkout_page_permalink( string $url ): string {
    if ( is_admin() && ! wp_doing_ajax() ) { return $url; }
    return make_checkout_url();
}
function make_store_account_page_permalink( string $url ): string {
    if ( is_admin() && ! wp_doing_ajax() ) { return $url; }
    return make_account_url();
}
add_filter( 'woocommerce_get_shop_page_permalink', 'make_store_shop_page_permalink', 20 );
add_filter( 'woocommerce_get_cart_page_permalink', 'make_store_cart_page_permalink', 20 );
add_filter( 'woocommerce_get_checkout_page_permalink', 'make_store_checkout_page_permalink', 20 );
add_filter( 'woocommerce_get_myaccount_page_permalink', 'make_store_account_page_permalink', 20 );
add_filter( 'woocommerce_get_cart_url', 'make_store_cart_page_permalink', 20 );
add_filter( 'woocommerce_get_checkout_url', 'make_store_checkout_page_permalink', 20 );

function make_store_localize_endpoint_url( string $url, string $endpoint, $value, string $permalink ): string {
    if ( in_array( $endpoint, array( 'order-pay','order-received' ), true ) ) {
        return make_store_endpoint_url( $endpoint, $value, '', 'checkout' );
    }
    if ( in_array( $endpoint, array( 'orders','downloads','edit-account','edit-address','payment-methods','add-payment-method','lost-password','customer-logout' ), true ) ) {
        return make_store_endpoint_url( $endpoint, $value, '', 'account' );
    }
    return $url;
}
add_filter( 'woocommerce_get_endpoint_url', 'make_store_localize_endpoint_url', 20, 4 );

function make_redirect_legacy_store_paths(): void {
    if ( is_admin() || is_feed() || is_preview() || isset( $_GET['make_lang'] ) ) { return; }

    $target = '';
    if ( function_exists( 'is_product' ) && is_product() ) {
        $target = make_product_url( get_queried_object_id(), make_current_language() );
    } elseif ( is_tax( array( 'product_collection','product_cat' ) ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) { $target = make_store_term_url( $term, make_current_language() ); }
    } elseif ( function_exists( 'is_shop' ) && is_shop() ) {
        $target = make_shop_view_url( make_store_view(), make_current_language() );
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

    wp_safe_redirect( $target, 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_store_paths', 3 );


function make_store_allowed_currencies(): array {
    return array( 'USD', 'EUR' );
}

function make_store_currency(): string {
    if ( isset( $_GET['currency'] ) ) {
        $requested = strtoupper( sanitize_text_field( wp_unslash( $_GET['currency'] ) ) );
        if ( in_array( $requested, make_store_allowed_currencies(), true ) ) {
            return $requested;
        }
    }

    if ( isset( $_COOKIE['drielo_currency'] ) ) {
        $saved = strtoupper( sanitize_text_field( wp_unslash( $_COOKIE['drielo_currency'] ) ) );
        if ( in_array( $saved, make_store_allowed_currencies(), true ) ) {
            return $saved;
        }
    }

    return DRIELO_DEFAULT_CURRENCY;
}

/**
 * USD is the catalogue base currency. EUR prices are calculated from the
 * latest ECB reference rate and cached locally so checkout never depends on
 * a live API response.
 */
function make_store_usd_eur_rate(): float {
    $cached = (float) get_transient( 'drielo_usd_eur_rate' );
    if ( $cached > 0.5 && $cached < 1.5 ) { return $cached; }

    $fallback = (float) get_option( 'drielo_usd_eur_rate_fallback', 0.871743 );
    if ( $fallback <= 0.5 || $fallback >= 1.5 ) { $fallback = 0.871743; }

    if ( ! function_exists( 'wp_remote_get' ) ) { return $fallback; }

    $response = wp_remote_get(
        'https://api.frankfurter.dev/v2/providers/ecb/rate/usd/eur',
        array(
            'timeout'     => 5,
            'redirection' => 2,
            'headers'     => array( 'Accept' => 'application/json' ),
        )
    );

    if ( is_wp_error( $response ) || 200 !== (int) wp_remote_retrieve_response_code( $response ) ) {
        set_transient( 'drielo_usd_eur_rate', $fallback, HOUR_IN_SECONDS );
        return $fallback;
    }

    $body = json_decode( (string) wp_remote_retrieve_body( $response ), true );
    $rate = is_array( $body ) && isset( $body['rate'] ) ? (float) $body['rate'] : 0.0;

    if ( $rate <= 0.5 || $rate >= 1.5 ) {
        set_transient( 'drielo_usd_eur_rate', $fallback, HOUR_IN_SECONDS );
        return $fallback;
    }

    update_option( 'drielo_usd_eur_rate_fallback', $rate, false );
    update_option( 'drielo_usd_eur_rate_date', sanitize_text_field( (string) ( $body['date'] ?? '' ) ), false );
    set_transient( 'drielo_usd_eur_rate', $rate, 12 * HOUR_IN_SECONDS );
    return $rate;
}

function make_store_price_from_usd( $price ) {
    if ( 'EUR' !== make_store_currency() || '' === $price || ! is_numeric( $price ) ) { return $price; }
    return round( (float) $price * make_store_usd_eur_rate(), 6 );
}

function make_store_convert_product_price( $price, $product ) {
    if ( is_admin() && ! wp_doing_ajax() ) { return $price; }
    return make_store_price_from_usd( $price );
}
add_filter( 'woocommerce_product_get_price', 'make_store_convert_product_price', 30, 2 );
add_filter( 'woocommerce_product_get_regular_price', 'make_store_convert_product_price', 30, 2 );
add_filter( 'woocommerce_product_get_sale_price', 'make_store_convert_product_price', 30, 2 );
add_filter( 'woocommerce_product_variation_get_price', 'make_store_convert_product_price', 30, 2 );
add_filter( 'woocommerce_product_variation_get_regular_price', 'make_store_convert_product_price', 30, 2 );
add_filter( 'woocommerce_product_variation_get_sale_price', 'make_store_convert_product_price', 30, 2 );

function make_store_variation_price_hash( array $hash ): array {
    $hash['drielo_currency'] = make_store_currency();
    if ( 'EUR' === make_store_currency() ) {
        $hash['drielo_usd_eur_rate'] = make_store_usd_eur_rate();
    }
    return $hash;
}
add_filter( 'woocommerce_get_variation_prices_hash', 'make_store_variation_price_hash', 20 );

function make_store_persist_currency(): void {
    if ( ! isset( $_GET['currency'] ) ) { return; }

    $currency = strtoupper( sanitize_text_field( wp_unslash( $_GET['currency'] ) ) );
    if ( ! in_array( $currency, make_store_allowed_currencies(), true ) ) { return; }

    $rate_cookie = number_format( make_store_usd_eur_rate(), 6, '.', '' );

    if ( function_exists( 'wc_setcookie' ) ) {
        wc_setcookie( 'drielo_currency', $currency, time() + YEAR_IN_SECONDS );
        wc_setcookie( 'drielo_usd_eur_rate', $rate_cookie, time() + DAY_IN_SECONDS );
    } elseif ( ! headers_sent() ) {
        setcookie( 'drielo_currency', $currency, time() + YEAR_IN_SECONDS, COOKIEPATH ?: '/', COOKIE_DOMAIN, is_ssl(), true );
        setcookie( 'drielo_usd_eur_rate', $rate_cookie, time() + DAY_IN_SECONDS, COOKIEPATH ?: '/', COOKIE_DOMAIN, is_ssl(), true );
    }

    $_COOKIE['drielo_currency'] = $currency;
    $_COOKIE['drielo_usd_eur_rate'] = $rate_cookie;

    // The selection lives in the cookie; remove the switching parameter from
    // the visible URL immediately after setting it.
    if ( ! wp_doing_ajax() && ! headers_sent() ) {
        $request = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
        $path    = (string) wp_parse_url( $request, PHP_URL_PATH );
        $query   = (string) wp_parse_url( $request, PHP_URL_QUERY );
        $url     = home_url( $path ?: '/' );
        $args    = array();

        if ( '' !== $query ) {
            parse_str( $query, $args );
            unset( $args['currency'] );
        }
        if ( ! empty( $args ) ) { $url = add_query_arg( $args, $url ); }

        wp_safe_redirect( $url, 302 );
        exit;
    }
}
add_action( 'init', 'make_store_persist_currency', 20 );

function make_filter_store_currency( string $currency ): string {
    if ( is_admin() && ! wp_doing_ajax() ) { return $currency; }
    return make_store_currency();
}
add_filter( 'woocommerce_currency', 'make_filter_store_currency', PHP_INT_MAX );

function make_store_currency_symbol( string $symbol, string $currency ): string {
    $currency = strtoupper( $currency );
    if ( 'USD' === $currency ) { return chr( 36 ); }
    if ( 'EUR' === $currency ) { return '€'; }
    return $symbol;
}
add_filter( 'woocommerce_currency_symbol', 'make_store_currency_symbol', PHP_INT_MAX, 2 );

function make_currency_switch_url( string $currency ): string {
    $currency = in_array( $currency, make_store_allowed_currencies(), true ) ? $currency : DRIELO_DEFAULT_CURRENCY;
    $request  = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
    $path     = (string) wp_parse_url( $request, PHP_URL_PATH );
    $query    = (string) wp_parse_url( $request, PHP_URL_QUERY );
    $url      = home_url( $path ?: '/' );
    $args     = array();

    if ( '' !== $query ) {
        parse_str( $query, $args );
        unset( $args['currency'] );
        if ( ! empty( $args ) ) { $url = add_query_arg( $args, $url ); }
    }

    return add_query_arg( 'currency', $currency, $url );
}

function make_store_body_class( array $classes ): array {
    if ( class_exists( 'WooCommerce' ) ) {
        $classes[] = 'make-currency-' . strtolower( make_store_currency() );
    }
    return $classes;
}
add_filter( 'body_class', 'make_store_body_class', 35 );

function make_store_disable_page_cache(): void {
    if ( is_admin() ) { return; }

    $is_storefront = ( function_exists( 'is_woocommerce' ) && is_woocommerce() )
        || ( function_exists( 'is_cart' ) && is_cart() )
        || ( function_exists( 'is_checkout' ) && is_checkout() )
        || ( function_exists( 'is_account_page' ) && is_account_page() )
        || is_tax( 'product_collection' );

    if ( ! $is_storefront ) { return; }

    if ( ! defined( 'DONOTCACHEPAGE' ) ) { define( 'DONOTCACHEPAGE', true ); }
    if ( ! defined( 'DONOTCACHEOBJECT' ) ) { define( 'DONOTCACHEOBJECT', true ); }

    nocache_headers();
    header( 'Cache-Control: private, no-store, no-cache, must-revalidate, max-age=0', true );
    header( 'Vary: Cookie', false );
}
add_action( 'template_redirect', 'make_store_disable_page_cache', 0 );

/**
 * New simple products default to digital pattern settings. A manually supplied
 * price is never overwritten, so exceptions can be priced product by product.
 */
function make_default_pattern_product_settings( $product ): void {
    if ( ! $product instanceof WC_Product_Simple ) { return; }

    if ( '' === (string) $product->get_regular_price( 'edit' ) && '' === (string) $product->get_sale_price( 'edit' ) ) {
        $product->set_regular_price( (string) DRIELO_DEFAULT_PRODUCT_PRICE );
    }

    $product->set_virtual( true );
    $product->set_downloadable( true );
    $product->set_sold_individually( true );
}
add_action( 'woocommerce_admin_process_product_object', 'make_default_pattern_product_settings', 20 );

function make_downloadables_sold_individually( bool $sold_individually, $product ): bool {
    if ( $product instanceof WC_Product && $product->is_downloadable() ) { return true; }
    return $sold_individually;
}
add_filter( 'woocommerce_is_sold_individually', 'make_downloadables_sold_individually', 20, 2 );

function make_collection_meta_fields_add(): void {
    ?>
    <div class="form-field">
        <label for="drielo_palette_hex"><?php esc_html_e( 'Palette colours', 'make' ); ?></label>
        <input type="text" name="drielo_palette_hex" id="drielo_palette_hex" placeholder="#B9657D, #6E586C, #A7B497">
        <p><?php esc_html_e( 'Comma-separated HEX colours used to preview the shared palette.', 'make' ); ?></p>
    </div>
    <div class="form-field">
        <label for="drielo_thread_codes"><?php esc_html_e( 'Thread codes', 'make' ); ?></label>
        <input type="text" name="drielo_thread_codes" id="drielo_thread_codes" placeholder="DMC 310, 815, 3721…">
        <p><?php esc_html_e( 'Shared thread references for this collection.', 'make' ); ?></p>
    </div>
    <?php
}
add_action( 'product_collection_add_form_fields', 'make_collection_meta_fields_add' );

function make_collection_meta_fields_edit( WP_Term $term ): void {
    $palette = (string) get_term_meta( $term->term_id, 'drielo_palette_hex', true );
    $threads = (string) get_term_meta( $term->term_id, 'drielo_thread_codes', true );
    ?>
    <tr class="form-field">
        <th scope="row"><label for="drielo_palette_hex"><?php esc_html_e( 'Palette colours', 'make' ); ?></label></th>
        <td><input type="text" name="drielo_palette_hex" id="drielo_palette_hex" value="<?php echo esc_attr( $palette ); ?>"><p class="description"><?php esc_html_e( 'Comma-separated HEX colours.', 'make' ); ?></p></td>
    </tr>
    <tr class="form-field">
        <th scope="row"><label for="drielo_thread_codes"><?php esc_html_e( 'Thread codes', 'make' ); ?></label></th>
        <td><input type="text" name="drielo_thread_codes" id="drielo_thread_codes" value="<?php echo esc_attr( $threads ); ?>"><p class="description"><?php esc_html_e( 'Shared DMC or other thread references.', 'make' ); ?></p></td>
    </tr>
    <?php
}
add_action( 'product_collection_edit_form_fields', 'make_collection_meta_fields_edit' );

function make_sanitize_palette_hex( string $value ): string {
    $colours = array_filter( array_map( 'trim', explode( ',', $value ) ) );
    $clean   = array();

    foreach ( array_slice( $colours, 0, 16 ) as $colour ) {
        $hex = sanitize_hex_color( $colour );
        if ( $hex ) { $clean[] = strtoupper( $hex ); }
    }

    return implode( ', ', $clean );
}

function make_save_collection_meta( int $term_id ): void {
    if ( isset( $_POST['drielo_palette_hex'] ) ) {
        update_term_meta( $term_id, 'drielo_palette_hex', make_sanitize_palette_hex( sanitize_text_field( wp_unslash( $_POST['drielo_palette_hex'] ) ) ) );
    }
    if ( isset( $_POST['drielo_thread_codes'] ) ) {
        update_term_meta( $term_id, 'drielo_thread_codes', sanitize_text_field( wp_unslash( $_POST['drielo_thread_codes'] ) ) );
    }
}
add_action( 'created_product_collection', 'make_save_collection_meta' );
add_action( 'edited_product_collection', 'make_save_collection_meta' );

function make_collection_palette( WP_Term $term ): array {
    $raw = (string) get_term_meta( $term->term_id, 'drielo_palette_hex', true );
    if ( '' === $raw ) { return array(); }
    return array_values( array_filter( array_map( 'sanitize_hex_color', array_map( 'trim', explode( ',', $raw ) ) ) ) );
}

function make_collection_display_name( WP_Term $term ): string {
    $lang = function_exists( 'make_current_language' ) ? make_current_language() : 'en';
    $key  = 'es' === $lang ? 'drielo_name_es' : 'drielo_name_en';
    $name = trim( (string) get_term_meta( $term->term_id, $key, true ) );
    return '' !== $name ? $name : (string) $term->name;
}

function make_collection_display_description( WP_Term $term ): string {
    $lang = function_exists( 'make_current_language' ) ? make_current_language() : 'en';
    $key  = 'es' === $lang ? 'drielo_description_es' : 'drielo_description_en';
    $copy = trim( (string) get_term_meta( $term->term_id, $key, true ) );
    return '' !== $copy ? $copy : trim( wp_strip_all_tags( (string) $term->description ) );
}

function make_primary_product_collection( int $product_id ): ?WP_Term {
    $terms = get_the_terms( $product_id, 'product_collection' );
    if ( ! is_array( $terms ) || empty( $terms ) ) { return null; }
    $first = reset( $terms );
    return $first instanceof WP_Term ? $first : null;
}

function make_store_view(): string {
    $view = sanitize_key( (string) get_query_var( 'make_store_view' ) );
    if ( '' === $view && isset( $_GET['view'] ) ) {
        $view = sanitize_key( wp_unslash( $_GET['view'] ) );
    }
    return 'collections' === $view ? 'collections' : 'patterns';
}

function make_shop_view_url( string $view, string $language = '' ): string {
    $view     = 'collections' === $view ? 'collections' : 'patterns';
    $language = in_array( $language, array( 'es', 'en' ), true )
        ? $language
        : ( function_exists( 'make_current_language' ) ? make_current_language() : 'es' );

    $shop_url = make_shop_url( $language );
    if ( 'collections' !== $view ) { return $shop_url; }

    return trailingslashit( $shop_url ) . ( 'en' === $language ? 'collections/' : 'colecciones/' );
}

function make_redirect_legacy_collection_view(): void {
    if ( is_admin() || ! function_exists( 'is_shop' ) || ! is_shop() ) { return; }
    if ( ! isset( $_GET['view'] ) || 'collections' !== sanitize_key( wp_unslash( $_GET['view'] ) ) ) { return; }

    wp_safe_redirect( make_shop_view_url( 'collections' ), 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_collection_view', 4 );

function make_render_shop_view_switcher(): void {
    $is_shop_page       = function_exists( 'is_shop' ) && is_shop();
    $is_product_page    = function_exists( 'is_product' ) && is_product();
    $is_collection_term = is_tax( 'product_collection' );

    if ( ! $is_shop_page && ! $is_product_page && ! $is_collection_term ) { return; }

    if ( $is_collection_term ) {
        $view = 'collections';
    } elseif ( $is_product_page ) {
        $view = 'patterns';
    } else {
        $view = make_store_view();
    }
    ?>
    <nav class="drielo-shop-views" aria-label="<?php echo esc_attr( make_t( 'Cómo ver la tienda', 'Shop view' ) ); ?>">
        <a class="<?php echo 'patterns' === $view ? 'is-active' : ''; ?>" href="<?php echo esc_url( make_shop_view_url( 'patterns' ) ); ?>"><?php echo esc_html( make_t( 'Diseños individuales', 'Individual designs' ) ); ?></a>
        <a class="<?php echo 'collections' === $view ? 'is-active' : ''; ?>" href="<?php echo esc_url( make_shop_view_url( 'collections' ) ); ?>"><?php echo esc_html( make_t( 'Ver por colección', 'Browse collections' ) ); ?></a>
    </nav>
    <?php
}

function make_collection_cover_product_id( WP_Term $term ): int {
    $ids = get_posts(
        array(
            'post_type'      => 'product',
            'post_status'    => 'publish',
            'posts_per_page' => 1,
            'fields'         => 'ids',
            'orderby'        => 'menu_order date',
            'order'          => 'ASC',
            'tax_query'      => array(
                array(
                    'taxonomy' => 'product_collection',
                    'field'    => 'term_id',
                    'terms'    => array( $term->term_id ),
                ),
            ),
        )
    );
    return empty( $ids ) ? 0 : (int) $ids[0];
}

function make_collection_product_ids( WP_Term $term ): array {
    $ids = get_posts(
        array(
            'post_type'      => 'product',
            'post_status'    => 'publish',
            'posts_per_page' => -1,
            'fields'         => 'ids',
            'orderby'        => 'menu_order date title',
            'order'          => 'ASC',
            'tax_query'      => array(
                array(
                    'taxonomy' => 'product_collection',
                    'field'    => 'term_id',
                    'terms'    => array( $term->term_id ),
                ),
            ),
        )
    );
    return array_map( 'intval', $ids );
}

function make_render_palette_swatches( WP_Term $term ): void {
    $palette = make_collection_palette( $term );
    if ( empty( $palette ) ) { return; }

    echo '<span class="drielo-palette" aria-label="' . esc_attr( make_t( 'Paleta compartida', 'Shared palette' ) ) . '">';
    foreach ( $palette as $colour ) {
        echo '<i style="--swatch:' . esc_attr( $colour ) . '"></i>';
    }
    echo '</span>';
}

function make_render_collection_grid(): void {
    $terms = get_terms(
        array(
            'taxonomy'   => 'product_collection',
            'hide_empty' => true,
            'orderby'    => 'name',
            'order'      => 'ASC',
        )
    );

    if ( is_wp_error( $terms ) || empty( $terms ) ) {
        echo '<div class="drielo-store-empty"><strong>' . esc_html( make_t( 'Las colecciones aparecerán aquí en cuanto carguemos los primeros patrones.', 'Collections will appear here as soon as the first patterns are loaded.' ) ) . '</strong></div>';
        return;
    }

    echo '<div class="drielo-collection-grid">';
    foreach ( $terms as $term ) {
        if ( ! $term instanceof WP_Term ) { continue; }
        $url         = get_term_link( $term );
        $preview_ids = make_collection_product_ids( $term );
        $product_id  = empty( $preview_ids ) ? make_collection_cover_product_id( $term ) : (int) $preview_ids[0];
        if ( is_wp_error( $url ) ) { continue; }

        echo '<article class="drielo-collection-card">';
        echo '<a class="drielo-collection-media" href="' . esc_url( $url ) . '">';
        if ( ! empty( $preview_ids ) && function_exists( 'make_static_attachment_image_html' ) ) {
            $preview_count = count( $preview_ids );
            $columns = $preview_count > 9 ? 4 : ( $preview_count > 4 ? 3 : 2 );
            echo '<span class="drielo-collection-thumbs" style="--drielo-collection-columns:' . esc_attr( (string) $columns ) . '">';
            foreach ( $preview_ids as $preview_id ) {
                $thumb_id = (int) get_post_thumbnail_id( $preview_id );
                if ( $thumb_id <= 0 ) { continue; }
                echo wp_kses_post( make_static_attachment_image_html( $thumb_id, 'woocommerce_thumbnail', 'drielo-collection-preview' ) );
            }
            echo '</span>';
        } elseif ( $product_id && has_post_thumbnail( $product_id ) && function_exists( 'make_static_attachment_image_html' ) ) {
            echo wp_kses_post( make_static_attachment_image_html( (int) get_post_thumbnail_id( $product_id ), 'medium_large', 'drielo-collection-preview' ) );
        } else {
            echo '<span class="drielo-collection-placeholder" aria-hidden="true"><b>×</b><b>×</b><b>×</b><b>×</b><b>×</b></span>';
        }
        echo '</a>';
        echo '<div class="drielo-collection-copy">';
        echo '<div class="drielo-collection-topline"><span>' . esc_html( sprintf( make_t( '%d diseños', '%d designs' ), (int) $term->count ) ) . '</span>';
        make_render_palette_swatches( $term );
        echo '</div>';
        $display_name = make_collection_display_name( $term );
        $display_description = make_collection_display_description( $term );
        echo '<h2><a href="' . esc_url( $url ) . '">' . esc_html( $display_name ) . '</a></h2>';
        if ( '' !== $display_description ) {
            echo '<p>' . esc_html( wp_trim_words( $display_description, 18 ) ) . '</p>';
        } else {
            echo '<p>' . esc_html( make_t( 'Una paleta compartida, varios diseños que puedes combinar.', 'One shared palette, several designs you can combine.' ) ) . '</p>';
        }
        echo '<div class="drielo-collection-footer"><span>' . wp_kses_post( sprintf( make_t( 'Desde %s por diseño', 'From %s per design' ), wc_price( make_store_price_from_usd( DRIELO_DEFAULT_PRODUCT_PRICE ) ) ) ) . '</span><strong>' . esc_html( make_t( 'Ver colección →', 'View collection →' ) ) . '</strong></div>';
        echo '</div></article>';
    }
    echo '</div>';
}

function make_product_collection_label(): void {
    global $product;
    if ( ! $product instanceof WC_Product ) { return; }
    $term = make_primary_product_collection( $product->get_id() );
    if ( ! $term ) { return; }
    $url = get_term_link( $term );
    if ( is_wp_error( $url ) ) { return; }
    echo '<div class="drielo-product-collection"><a href="' . esc_url( $url ) . '">' . esc_html( make_t( 'Colección', 'Collection' ) ) . ' · ' . esc_html( make_collection_display_name( $term ) ) . '</a></div>';
}
add_action( 'woocommerce_after_shop_loop_item_title', 'make_product_collection_label', 7 );

function make_single_product_collection_context(): void {
    global $product;
    if ( ! $product instanceof WC_Product ) { return; }
    $term = make_primary_product_collection( $product->get_id() );
    if ( ! $term ) { return; }
    $url = get_term_link( $term );
    if ( is_wp_error( $url ) ) { return; }

    echo '<div class="drielo-single-collection">';
    echo '<a href="' . esc_url( $url ) . '"><span>' . esc_html( make_t( 'Colección', 'Collection' ) ) . '</span><strong>' . esc_html( make_collection_display_name( $term ) ) . '</strong></a>';
    make_render_palette_swatches( $term );
    echo '</div>';
}
add_action( 'woocommerce_single_product_summary', 'make_single_product_collection_context', 4 );

function make_collection_sibling_ids( int $product_id, WP_Term $term ): array {
    $ids = get_posts(
        array(
            'post_type'      => 'product',
            'post_status'    => 'publish',
            'posts_per_page' => -1,
            'fields'         => 'ids',
            'post__not_in'   => array( $product_id ),
            'orderby'        => 'menu_order title',
            'order'          => 'ASC',
            'tax_query'      => array(
                array(
                    'taxonomy' => 'product_collection',
                    'field'    => 'term_id',
                    'terms'    => array( $term->term_id ),
                ),
            ),
        )
    );
    return array_map( 'intval', $ids );
}

function make_render_collection_addons(): void {
    global $product;
    if ( ! $product instanceof WC_Product || ! $product->is_purchasable() ) { return; }

    $term = make_primary_product_collection( $product->get_id() );
    if ( ! $term ) { return; }

    $siblings = make_collection_sibling_ids( $product->get_id(), $term );
    if ( empty( $siblings ) ) { return; }

    $collection_url = get_term_link( $term );
    ?>
    <section class="drielo-addon-picker" aria-labelledby="drielo-addon-title">
        <div class="drielo-addon-head">
            <div>
                <span class="section-kicker"><?php echo esc_html( make_t( 'Completa la colección', 'Build your collection' ) ); ?></span>
                <h3 id="drielo-addon-title"><?php echo esc_html( sprintf( make_t( 'Añade más diseños de %s', 'Add more designs from %s' ), make_collection_display_name( $term ) ) ); ?></h3>
            </div>
            <span class="drielo-addon-price"><?php echo wp_kses_post( sprintf( make_t( '+%s cada uno', '+%s each' ), wc_price( make_store_price_from_usd( DRIELO_COLLECTION_ADDON_PRICE ) ) ) ); ?></span>
        </div>
        <p><?php echo esc_html( make_t( 'Comparten la misma paleta de color. Marca todos los que quieras y se añadirán al carrito con precio especial.', 'They share the same colour palette. Select as many as you like and they will be added to the cart at the special price.' ) ); ?></p>
        <?php wp_nonce_field( 'drielo_collection_addons_' . $product->get_id(), 'drielo_collection_addons_nonce', false ); ?>
        <div class="drielo-addon-list">
            <?php foreach ( $siblings as $sibling_id ) :
                $sibling = wc_get_product( $sibling_id );
                if ( ! $sibling instanceof WC_Product || ! $sibling->is_purchasable() || ! $sibling->is_in_stock() ) { continue; }
                $thumb = get_the_post_thumbnail_url( $sibling_id, 'thumbnail' );
                ?>
                <label class="drielo-addon-option">
                    <input type="checkbox" name="drielo_collection_addons[]" value="<?php echo esc_attr( (string) $sibling_id ); ?>">
                    <span class="drielo-addon-check" aria-hidden="true">✓</span>
                    <span class="drielo-addon-thumb">
                        <?php if ( $thumb ) : ?><img src="<?php echo esc_url( $thumb ); ?>" alt="" loading="lazy"><?php else : ?><span aria-hidden="true">×</span><?php endif; ?>
                    </span>
                    <span class="drielo-addon-name"><strong><?php echo esc_html( $sibling->get_name() ); ?></strong><small><?php echo wp_kses_post( '+' . wc_price( make_store_price_from_usd( DRIELO_COLLECTION_ADDON_PRICE ) ) ); ?></small></span>
                </label>
            <?php endforeach; ?>
        </div>
        <?php if ( ! is_wp_error( $collection_url ) ) : ?><a class="drielo-addon-collection-link" href="<?php echo esc_url( $collection_url ); ?>"><?php echo esc_html( make_t( 'Ver todos los diseños de la colección', 'See every design in the collection' ) ); ?> →</a><?php endif; ?>
    </section>
    <?php
}
add_action( 'woocommerce_before_add_to_cart_button', 'make_render_collection_addons', 12 );

function make_products_share_collection( int $parent_id, int $addon_id, string $required_slug ): bool {
    if ( $parent_id === $addon_id || $parent_id <= 0 || $addon_id <= 0 ) { return false; }
    $parent_terms = wp_get_post_terms( $parent_id, 'product_collection', array( 'fields' => 'slugs' ) );
    $addon_terms  = wp_get_post_terms( $addon_id, 'product_collection', array( 'fields' => 'slugs' ) );
    if ( is_wp_error( $parent_terms ) || is_wp_error( $addon_terms ) ) { return false; }
    return in_array( $required_slug, $parent_terms, true ) && in_array( $required_slug, $addon_terms, true );
}

function make_add_selected_collection_products( string $cart_item_key, int $product_id, int $quantity, int $variation_id, array $variation, array $cart_item_data ): void {
    static $adding_addons = false;

    if ( $adding_addons || ! empty( $cart_item_data['_drielo_collection_addon'] ) ) { return; }
    if ( empty( $_POST['drielo_collection_addons'] ) || ! is_array( $_POST['drielo_collection_addons'] ) ) { return; }

    $nonce = isset( $_POST['drielo_collection_addons_nonce'] ) ? sanitize_text_field( wp_unslash( $_POST['drielo_collection_addons_nonce'] ) ) : '';
    if ( ! wp_verify_nonce( $nonce, 'drielo_collection_addons_' . $product_id ) ) { return; }

    $term = make_primary_product_collection( $product_id );
    if ( ! $term || ! function_exists( 'WC' ) || ! WC()->cart ) { return; }

    $selected = array_values( array_unique( array_map( 'absint', wp_unslash( $_POST['drielo_collection_addons'] ) ) ) );
    $selected = array_slice( array_filter( $selected ), 0, 50 );
    if ( empty( $selected ) ) { return; }

    $adding_addons = true;
    foreach ( $selected as $addon_id ) {
        $addon = wc_get_product( $addon_id );
        if ( ! $addon instanceof WC_Product || ! $addon->is_purchasable() || ! $addon->is_in_stock() ) { continue; }
        if ( ! make_products_share_collection( $product_id, $addon_id, $term->slug ) ) { continue; }

        WC()->cart->add_to_cart(
            $addon_id,
            1,
            0,
            array(),
            array(
                '_drielo_collection_addon' => true,
                '_drielo_parent_cart_key'  => $cart_item_key,
                '_drielo_parent_product'   => $product_id,
                '_drielo_collection_slug'  => $term->slug,
                '_drielo_bundle_key'       => wp_generate_uuid4(),
            )
        );
    }
    $adding_addons = false;
}
add_action( 'woocommerce_add_to_cart', 'make_add_selected_collection_products', 20, 6 );

function make_price_collection_addons( $cart ): void {
    if ( ! $cart instanceof WC_Cart ) { return; }
    if ( is_admin() && ! wp_doing_ajax() ) { return; }

    foreach ( $cart->get_cart() as $cart_item ) {
        if ( empty( $cart_item['_drielo_collection_addon'] ) || empty( $cart_item['data'] ) || ! $cart_item['data'] instanceof WC_Product ) { continue; }
        $cart_item['data']->set_price( DRIELO_COLLECTION_ADDON_PRICE );
    }
}
add_action( 'woocommerce_before_calculate_totals', 'make_price_collection_addons', 20 );

function make_collection_addon_cart_data( array $item_data, array $cart_item ): array {
    if ( empty( $cart_item['_drielo_collection_addon'] ) ) { return $item_data; }
    $item_data[] = array(
        'key'   => make_t( 'Precio de colección', 'Collection price' ),
        'value' => wp_strip_all_tags( wc_price( make_store_price_from_usd( DRIELO_COLLECTION_ADDON_PRICE ) ) ),
    );
    return $item_data;
}
add_filter( 'woocommerce_get_item_data', 'make_collection_addon_cart_data', 20, 2 );

function make_store_collection_addon_order_meta( $item, string $cart_item_key, array $values, $order ): void {
    if ( empty( $values['_drielo_collection_addon'] ) ) { return; }
    $item->add_meta_data( '_drielo_collection_addon', 'yes', true );
    if ( ! empty( $values['_drielo_collection_slug'] ) ) {
        $item->add_meta_data( '_drielo_collection', sanitize_key( $values['_drielo_collection_slug'] ), true );
    }
}
add_action( 'woocommerce_checkout_create_order_line_item', 'make_store_collection_addon_order_meta', 20, 4 );

function make_remove_linked_collection_addons( string $removed_cart_item_key, $cart ): void {
    if ( ! $cart instanceof WC_Cart ) { return; }
    $remove = array();
    foreach ( $cart->get_cart() as $key => $item ) {
        if ( ! empty( $item['_drielo_collection_addon'] ) && isset( $item['_drielo_parent_cart_key'] ) && $removed_cart_item_key === $item['_drielo_parent_cart_key'] ) {
            $remove[] = $key;
        }
    }
    foreach ( $remove as $key ) { $cart->remove_cart_item( $key ); }
}
add_action( 'woocommerce_cart_item_removed', 'make_remove_linked_collection_addons', 20, 2 );

function make_collection_archive_note(): void {
    if ( ! is_tax( 'product_collection' ) ) { return; }
    $term = get_queried_object();
    if ( ! $term instanceof WP_Term ) { return; }
    echo '<div class="drielo-collection-note"><div><span class="section-kicker">' . esc_html( make_t( 'Paleta compartida', 'Shared palette' ) ) . '</span>';
    make_render_palette_swatches( $term );
    echo '</div></div>';
}


function make_pending_download_availability( string $text, $product ): string {
    if ( $product instanceof WC_Product && '1' === (string) get_post_meta( $product->get_id(), '_drielo_download_pending', true ) ) {
        return make_t( 'Vista previa publicada · descarga aún no activada', 'Preview published · download not active yet' );
    }
    return $text;
}
add_filter( 'woocommerce_get_availability_text', 'make_pending_download_availability', 20, 2 );

function make_pending_download_notice(): void {
    global $product;
    if ( ! $product instanceof WC_Product ) { return; }
    if ( '1' !== (string) get_post_meta( $product->get_id(), '_drielo_download_pending', true ) ) { return; }
    echo '<div class="drielo-download-pending">' .
        esc_html( make_t(
            'La ficha está lista para revisión. La compra se activará cuando el PDF descargable quede conectado.',
            'This product page is ready for review. Purchasing will activate when the downloadable PDF is connected.'
        ) ) .
    '</div>';
}
add_action( 'woocommerce_single_product_summary', 'make_pending_download_notice', 24 );


/**
 * Make product reference codes searchable from the site-wide search.
 *
 * Product codes are stored twice on managed products:
 * - WooCommerce SKU: DRIELO-P0004
 * - Drielo code meta: P0004
 *
 * Visitors can therefore search P0004, P-0004 or DRIELO-P0004.
 */
function make_product_code_search_sql( string $search, WP_Query $query ): string {
    if ( is_admin() || ! $query->is_search() || ! $query->is_main_query() ) {
        return $search;
    }

    $raw = trim( (string) $query->get( 's' ) );
    if ( '' === $raw ) {
        return $search;
    }

    $normalized = strtoupper( preg_replace( '/[^A-Z0-9]/i', '', $raw ) );
    $code = '';

    if ( preg_match( '/^DRIELOP(\d{1,8})$/', $normalized, $matches ) ) {
        $code = 'P' . str_pad( $matches[1], 4, '0', STR_PAD_LEFT );
    } elseif ( preg_match( '/^P(\d{1,8})$/', $normalized, $matches ) ) {
        $code = 'P' . str_pad( $matches[1], 4, '0', STR_PAD_LEFT );
    } elseif ( preg_match( '/^(\d{1,8})$/', $normalized, $matches ) ) {
        $code = 'P' . str_pad( $matches[1], 4, '0', STR_PAD_LEFT );
    }

    if ( '' === $code ) {
        return $search;
    }

    global $wpdb;

    $sku       = 'DRIELO-' . $code;
    $pdf_code  = 'P-' . substr( $code, 1 );
    $needle_a  = '%' . $wpdb->esc_like( $code ) . '%';
    $needle_b  = '%' . $wpdb->esc_like( $sku ) . '%';
    $needle_c  = '%' . $wpdb->esc_like( $pdf_code ) . '%';

    $meta_sql = $wpdb->prepare(
        "EXISTS (
            SELECT 1
            FROM {$wpdb->postmeta} drielo_code_meta
            WHERE drielo_code_meta.post_id = {$wpdb->posts}.ID
              AND drielo_code_meta.meta_key IN ('_sku', '_drielo_product_code')
              AND (
                    drielo_code_meta.meta_value LIKE %s
                 OR drielo_code_meta.meta_value LIKE %s
                 OR drielo_code_meta.meta_value LIKE %s
              )
        )",
        $needle_a,
        $needle_b,
        $needle_c
    );

    $base = trim( $search );
    if ( '' !== $base ) {
        $base = preg_replace( '/^AND\s+/i', '', $base );
        return " AND ( ({$base}) OR {$meta_sql} )";
    }

    return " AND ({$meta_sql})";
}
add_filter( 'posts_search', 'make_product_code_search_sql', 20, 2 );

function make_product_reference_code( int $product_id ): string {
    $code = (string) get_post_meta( $product_id, '_drielo_product_code', true );
    if ( '' !== $code ) {
        return strtoupper( $code );
    }

    $sku = (string) get_post_meta( $product_id, '_sku', true );
    if ( preg_match( '/P-?(\d+)$/i', $sku, $matches ) ) {
        return 'P' . str_pad( $matches[1], 4, '0', STR_PAD_LEFT );
    }

    return '';
}

function make_render_product_reference(): void {
    if ( ! is_product() ) {
        return;
    }

    global $product;
    if ( ! $product instanceof WC_Product ) {
        return;
    }

    $code = make_product_reference_code( $product->get_id() );
    if ( '' === $code ) {
        return;
    }

    echo '<div class="drielo-product-reference"><span>' .
        esc_html( make_t( 'Código', 'Code' ) ) .
        '</span><strong>' . esc_html( $code ) . '</strong></div>';
}
add_action( 'woocommerce_single_product_summary', 'make_render_product_reference', 6 );


/* Bilingual product presentation ----------------------------------------- */

function make_store_should_localize_products(): bool {
    if ( PHP_SAPI === 'cli' ) { return false; }
    if ( is_admin() && ! wp_doing_ajax() ) { return false; }
    return true;
}

function make_product_localized_meta( int $product_id, string $field, string $fallback = '' ): string {
    if ( $product_id <= 0 ) { return $fallback; }

    $language = function_exists( 'make_current_language' ) ? make_current_language() : 'es';
    $language = 'en' === $language ? 'en' : 'es';
    $value = (string) get_post_meta( $product_id, '_drielo_' . $field . '_' . $language, true );

    if ( '' === trim( $value ) && 'en' !== $language ) {
        $value = (string) get_post_meta( $product_id, '_drielo_' . $field . '_en', true );
    }

    return '' !== trim( $value ) ? $value : $fallback;
}

function make_localize_product_name( string $name, $product ): string {
    if ( ! make_store_should_localize_products() || ! $product instanceof WC_Product ) { return $name; }
    return make_product_localized_meta( $product->get_id(), 'title', $name );
}
add_filter( 'woocommerce_product_get_name', 'make_localize_product_name', 20, 2 );
add_filter( 'woocommerce_product_variation_get_name', 'make_localize_product_name', 20, 2 );

function make_localize_product_post_title( string $title, int $post_id = 0 ): string {
    if ( ! make_store_should_localize_products() || $post_id <= 0 || 'product' !== get_post_type( $post_id ) ) { return $title; }
    return make_product_localized_meta( $post_id, 'title', $title );
}
add_filter( 'the_title', 'make_localize_product_post_title', 20, 2 );

function make_localize_product_description( string $description, $product ): string {
    if ( ! make_store_should_localize_products() || ! $product instanceof WC_Product ) { return $description; }
    return make_product_localized_meta( $product->get_id(), 'description', $description );
}
add_filter( 'woocommerce_product_get_description', 'make_localize_product_description', 20, 2 );

function make_localize_product_short_description( string $description, $product ): string {
    if ( ! make_store_should_localize_products() || ! $product instanceof WC_Product ) { return $description; }
    return make_product_localized_meta( $product->get_id(), 'short_description', $description );
}
add_filter( 'woocommerce_product_get_short_description', 'make_localize_product_short_description', 20, 2 );

function make_localize_product_content( string $content ): string {
    if ( ! make_store_should_localize_products() || ! is_singular( 'product' ) ) { return $content; }
    $product_id = get_queried_object_id();
    return make_product_localized_meta( $product_id, 'description', $content );
}
add_filter( 'the_content', 'make_localize_product_content', 20 );

function make_localize_product_excerpt( string $excerpt, $post = null ): string {
    if ( ! make_store_should_localize_products() ) { return $excerpt; }
    $post_id = $post instanceof WP_Post ? $post->ID : ( is_numeric( $post ) ? (int) $post : get_the_ID() );
    if ( $post_id <= 0 || 'product' !== get_post_type( $post_id ) ) { return $excerpt; }
    return wp_strip_all_tags( make_product_localized_meta( $post_id, 'short_description', $excerpt ) );
}
add_filter( 'get_the_excerpt', 'make_localize_product_excerpt', 20, 2 );

function make_localize_woocommerce_short_description( string $description ): string {
    if ( ! make_store_should_localize_products() ) { return $description; }
    global $product;
    if ( ! $product instanceof WC_Product ) { return $description; }
    return make_product_localized_meta( $product->get_id(), 'short_description', $description );
}
add_filter( 'woocommerce_short_description', 'make_localize_woocommerce_short_description', 20 );

function make_localize_product_purchase_note( string $note, $product ): string {
    if ( ! make_store_should_localize_products() || ! $product instanceof WC_Product ) { return $note; }
    return make_product_localized_meta( $product->get_id(), 'purchase_note', $note );
}
add_filter( 'woocommerce_product_get_purchase_note', 'make_localize_product_purchase_note', 20, 2 );

function make_localize_product_attribute_label( string $label, string $name, $product = null ): string {
    if ( ! make_store_should_localize_products() || ! function_exists( 'make_is_english' ) || make_is_english() ) { return $label; }

    $labels = array(
        'Pattern size'   => 'Tamaño del patrón',
        'DMC colours'    => 'Colores DMC',
        'Skill level'    => 'Nivel',
        'Stitch type'    => 'Tipo de puntada',
        'Total stitches' => 'Puntadas totales',
    );

    return $labels[ $label ] ?? $labels[ $name ] ?? $label;
}
add_filter( 'woocommerce_attribute_label', 'make_localize_product_attribute_label', 20, 3 );

function make_localize_product_attribute_value( string $value, $attribute, array $values ): string {
    if ( ! make_store_should_localize_products() || ! function_exists( 'make_is_english' ) || make_is_english() ) { return $value; }

    return str_replace(
        array( 'Beginner friendly', 'Full cross stitch' ),
        array( 'Apto para principiantes', 'Punto de cruz completo' ),
        $value
    );
}
add_filter( 'woocommerce_attribute', 'make_localize_product_attribute_value', 20, 3 );

function make_localize_product_term( $term, string $taxonomy ) {
    if ( ! make_store_should_localize_products() || ! $term instanceof WP_Term || ! function_exists( 'make_is_english' ) || make_is_english() ) {
        return $term;
    }

    $name = '';
    if ( 'product_cat' === $taxonomy ) {
        $name = trim( (string) get_term_meta( $term->term_id, 'drielo_name_es', true ) );
    } elseif ( 'product_tag' === $taxonomy ) {
        $tags = array(
            'beginner-friendly' => 'Apto para principiantes',
            'full-cross-stitch' => 'Punto de cruz completo',
            '19-dmc-colours'    => '19 colores DMC',
            'portrait'          => 'Retrato',
            'bubble-gum'        => 'Chicle',
            'sunglasses'        => 'Gafas de sol',
            'wink'              => 'Guiño',
        );
        $name = $tags[ $term->slug ] ?? '';
    }

    if ( '' === $name ) { return $term; }

    $localized = clone $term;
    $localized->name = $name;
    return $localized;
}
add_filter( 'get_term', 'make_localize_product_term', 20, 2 );
