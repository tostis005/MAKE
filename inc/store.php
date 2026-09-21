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
    $url = get_term_link( $term );
    if ( is_wp_error( $url ) ) { return; }

    wp_safe_redirect( $url, 301 );
    exit;
}
add_action( 'template_redirect', 'make_redirect_legacy_collection_url', 3 );

function make_store_routes(): void {
    add_rewrite_rule( '^tienda/colecciones/?$', 'index.php?post_type=product&make_store_view=collections&make_lang=es', 'top' );
    add_rewrite_rule( '^tienda/collections/?$', 'index.php?post_type=product&make_store_view=collections&make_lang=en', 'top' );
}
add_action( 'init', 'make_store_routes', 7 );

function make_store_query_vars( array $vars ): array {
    $vars[] = 'make_store_view';
    return $vars;
}
add_filter( 'query_vars', 'make_store_query_vars' );

function make_store_maybe_flush_rewrites(): void {
    $schema_version = '2';
    if ( $schema_version === (string) get_option( 'drielo_store_schema_version', '' ) ) { return; }
    flush_rewrite_rules( false );
    update_option( 'drielo_store_schema_version', $schema_version, false );
}
add_action( 'init', 'make_store_maybe_flush_rewrites', 99 );


function make_localize_store_post_link( string $url, $post ): string {
    if ( ! function_exists( 'make_is_english' ) || ! make_is_english() ) { return $url; }
    if ( $post instanceof WP_Post && 'product' === $post->post_type ) {
        return add_query_arg( 'make_lang', 'en', $url );
    }
    return $url;
}
add_filter( 'post_type_link', 'make_localize_store_post_link', 20, 2 );

function make_localize_store_term_link( string $url, WP_Term $term, string $taxonomy ): string {
    if ( ! function_exists( 'make_is_english' ) || ! make_is_english() ) { return $url; }
    if ( in_array( $taxonomy, array( 'product_collection', 'product_cat' ), true ) ) {
        return add_query_arg( 'make_lang', 'en', $url );
    }
    return $url;
}
add_filter( 'term_link', 'make_localize_store_term_link', 20, 3 );

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

    if ( function_exists( 'wc_setcookie' ) ) {
        wc_setcookie( 'drielo_currency', $currency, time() + YEAR_IN_SECONDS );
    } elseif ( ! headers_sent() ) {
        setcookie( 'drielo_currency', $currency, time() + YEAR_IN_SECONDS, COOKIEPATH ?: '/', COOKIE_DOMAIN, is_ssl(), true );
    }

    $_COOKIE['drielo_currency'] = $currency;

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
add_filter( 'woocommerce_currency', 'make_filter_store_currency', 50 );

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

    $shop_url = remove_query_arg( array( 'view', 'make_store_view', 'make_lang' ), make_shop_url() );

    if ( 'collections' === $view ) {
        $path = 'en' === $language ? 'collections' : 'colecciones';
        return trailingslashit( trailingslashit( $shop_url ) . $path );
    }

    return 'en' === $language ? add_query_arg( 'make_lang', 'en', $shop_url ) : $shop_url;
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
        $url        = get_term_link( $term );
        $product_id = make_collection_cover_product_id( $term );
        if ( is_wp_error( $url ) ) { continue; }

        $cover_id = (int) get_term_meta( $term->term_id, 'drielo_collection_cover_id', true );

        echo '<article class="drielo-collection-card">';
        echo '<a class="drielo-collection-media" href="' . esc_url( $url ) . '">';
        if ( $cover_id ) {
            echo wp_get_attachment_image( $cover_id, 'make-card', false, array( 'loading' => 'lazy' ) );
        } elseif ( $product_id && has_post_thumbnail( $product_id ) ) {
            echo get_the_post_thumbnail( $product_id, 'make-card', array( 'loading' => 'lazy' ) );
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
                $thumb = get_the_post_thumbnail_url( $sibling_id, 'woocommerce_thumbnail' );
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
