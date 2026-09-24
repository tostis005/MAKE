<?php
/**
 * Private PDF validation library for Drielo administrators.
 *
 * URL: /pdfs/
 * The route is intentionally not backed by a WordPress Page, so it never
 * appears in menus or public sitemaps. Both the library and each PDF download
 * require an authenticated administrator.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function make_pdf_library_routes(): void {
    add_rewrite_rule( '^pdfs/?$', 'index.php?make_pdf_library=1', 'top' );
    add_rewrite_rule( '^pdfs/page/([0-9]+)/?$', 'index.php?make_pdf_library=1&paged=$matches[1]', 'top' );
}
add_action( 'init', 'make_pdf_library_routes', 18 );

function make_pdf_library_query_vars( array $vars ): array {
    $vars[] = 'make_pdf_library';
    return $vars;
}
add_filter( 'query_vars', 'make_pdf_library_query_vars' );

function make_pdf_library_maybe_flush_rewrites(): void {
    $version = '1';
    if ( $version === (string) get_option( 'drielo_pdf_library_schema', '' ) ) { return; }

    flush_rewrite_rules( false );
    update_option( 'drielo_pdf_library_schema', $version, false );
}
add_action( 'init', 'make_pdf_library_maybe_flush_rewrites', 102 );

function make_is_pdf_library_request(): bool {
    return 1 === (int) get_query_var( 'make_pdf_library' );
}

function make_pdf_library_guard(): void {
    if ( ! make_is_pdf_library_request() ) { return; }

    if ( ! is_user_logged_in() ) {
        auth_redirect();
        exit;
    }

    if ( ! current_user_can( 'manage_options' ) ) {
        wp_die(
            esc_html__( 'You do not have permission to view this page.', 'make' ),
            esc_html__( 'Private PDF library', 'make' ),
            array( 'response' => 403 )
        );
    }

    if ( ! defined( 'DONOTCACHEPAGE' ) ) { define( 'DONOTCACHEPAGE', true ); }
    if ( ! defined( 'DONOTCACHEOBJECT' ) ) { define( 'DONOTCACHEOBJECT', true ); }

    nocache_headers();
    header( 'Cache-Control: private, no-store, no-cache, must-revalidate, max-age=0', true );
    header( 'X-Robots-Tag: noindex, nofollow, noarchive', true );
}
add_action( 'template_redirect', 'make_pdf_library_guard', -20 );

function make_pdf_library_template( string $template ): string {
    if ( ! make_is_pdf_library_request() ) { return $template; }

    $private_template = locate_template( 'page-pdfs.php' );
    return $private_template ?: $template;
}
add_filter( 'template_include', 'make_pdf_library_template', 120 );

function make_pdf_library_assets(): void {
    if ( ! make_is_pdf_library_request() ) { return; }

    $file = get_template_directory() . '/assets/css/pdf-library.css';
    wp_enqueue_style(
        'make-pdf-library',
        get_template_directory_uri() . '/assets/css/pdf-library.css',
        array( 'make-style' ),
        is_file( $file ) ? (string) filemtime( $file ) : ( wp_get_theme()->get( 'Version' ) ?: '1.0.0' )
    );
}
add_action( 'wp_enqueue_scripts', 'make_pdf_library_assets', 40 );

function make_pdf_library_body_class( array $classes ): array {
    if ( make_is_pdf_library_request() ) { $classes[] = 'drielo-pdf-library'; }
    return $classes;
}
add_filter( 'body_class', 'make_pdf_library_body_class', 40 );

function make_pdf_library_robots( array $robots ): array {
    if ( make_is_pdf_library_request() ) {
        $robots['noindex'] = true;
        $robots['nofollow'] = true;
        $robots['noarchive'] = true;
    }
    return $robots;
}
add_filter( 'wp_robots', 'make_pdf_library_robots', 50 );

function make_pdf_library_document_title( array $parts ): array {
    if ( make_is_pdf_library_request() ) {
        $parts['title'] = 'PDFs';
    }
    return $parts;
}
add_filter( 'document_title_parts', 'make_pdf_library_document_title', 50 );

function make_pdf_library_filter_config(): array {
    return array(
        'drielo_technique'    => array( 'taxonomy' => 'pa_technique',    'label' => 'Técnica' ),
        'drielo_theme'        => array( 'taxonomy' => 'pa_theme',        'label' => 'Tema' ),
        'drielo_style'        => array( 'taxonomy' => 'pa_style',        'label' => 'Estilo' ),
        'drielo_project'      => array( 'taxonomy' => 'pa_project',      'label' => 'Proyecto' ),
        'drielo_orientation'  => array( 'taxonomy' => 'pa_orientation',  'label' => 'Orientación' ),
        'drielo_season'       => array( 'taxonomy' => 'pa_season',       'label' => 'Temporada' ),
        'drielo_difficulty'   => array( 'taxonomy' => 'pa_difficulty',   'label' => 'Dificultad' ),
        'drielo_color_family' => array( 'taxonomy' => 'pa_color-family', 'label' => 'Color' ),
        'drielo_collection'   => array( 'taxonomy' => 'product_collection', 'label' => 'Colección' ),
    );
}

function make_pdf_library_active_filters(): array {
    $active = array();

    foreach ( make_pdf_library_filter_config() as $query_key => $config ) {
        if ( ! isset( $_GET[ $query_key ] ) ) { continue; }

        $value = wp_unslash( $_GET[ $query_key ] );
        if ( is_array( $value ) ) { $value = reset( $value ); }
        $value = sanitize_title( (string) $value );

        if ( '' !== $value ) { $active[ $query_key ] = $value; }
    }

    return $active;
}

function make_pdf_library_products_query(): WP_Query {
    $tax_query = array();
    $active = make_pdf_library_active_filters();

    foreach ( make_pdf_library_filter_config() as $query_key => $config ) {
        if ( empty( $active[ $query_key ] ) ) { continue; }

        $taxonomy = (string) $config['taxonomy'];
        if ( ! taxonomy_exists( $taxonomy ) ) { continue; }

        $tax_query[] = array(
            'taxonomy' => $taxonomy,
            'field'    => 'slug',
            'terms'    => array( $active[ $query_key ] ),
        );
    }

    if ( count( $tax_query ) > 1 ) {
        $tax_query['relation'] = 'AND';
    }

    $args = array(
        'post_type'              => 'product',
        'post_status'            => 'publish',
        'posts_per_page'         => 24,
        'paged'                  => max( 1, (int) get_query_var( 'paged' ) ),
        'orderby'                => array( 'menu_order' => 'ASC', 'title' => 'ASC' ),
        'ignore_sticky_posts'    => true,
        'update_post_meta_cache' => true,
        'update_post_term_cache' => true,
    );

    if ( ! empty( $tax_query ) ) {
        $args['tax_query'] = $tax_query;
    }

    return new WP_Query( $args );
}

function make_pdf_library_term_label( WP_Term $term, string $taxonomy ): string {
    if ( 'product_collection' === $taxonomy && function_exists( 'make_collection_display_name' ) ) {
        return make_collection_display_name( $term );
    }

    if ( 'pa_technique' === $taxonomy && function_exists( 'make_store_technique_config' ) ) {
        $config = make_store_technique_config();
        $language = function_exists( 'make_current_language' ) ? make_current_language() : 'es';
        if ( isset( $config[ $term->slug ] ) ) {
            return (string) ( $config[ $term->slug ][ $language ] ?? $config[ $term->slug ]['en'] ?? $term->name );
        }
    }

    return (string) $term->name;
}

function make_pdf_library_product_technique_label( int $product_id ): string {
    $slug = function_exists( 'make_store_product_technique' )
        ? sanitize_title( make_store_product_technique( $product_id ) )
        : '';

    if ( '' !== $slug && function_exists( 'make_store_technique_config' ) ) {
        $config = make_store_technique_config();
        $language = function_exists( 'make_current_language' ) ? make_current_language() : 'es';
        if ( isset( $config[ $slug ] ) ) {
            return (string) ( $config[ $slug ][ $language ] ?? $config[ $slug ]['en'] ?? $slug );
        }
    }

    if ( taxonomy_exists( 'pa_technique' ) ) {
        $terms = wp_get_object_terms( $product_id, 'pa_technique' );
        if ( ! is_wp_error( $terms ) && ! empty( $terms ) && $terms[0] instanceof WP_Term ) {
            return make_pdf_library_term_label( $terms[0], 'pa_technique' );
        }
    }

    return '—';
}

function make_pdf_library_pdf_record( WC_Product $product ): ?array {
    $downloads = $product->get_downloads();
    if ( empty( $downloads ) ) { return null; }

    foreach ( $downloads as $download_id => $download ) {
        if ( ! is_object( $download ) || ! method_exists( $download, 'get_file' ) ) { continue; }

        $file = trim( (string) $download->get_file() );
        $name = method_exists( $download, 'get_name' ) ? trim( (string) $download->get_name() ) : '';
        $path = (string) wp_parse_url( $file, PHP_URL_PATH );

        if ( '' !== $file && ( str_ends_with( strtolower( $path ), '.pdf' ) || str_contains( strtolower( $name ), '.pdf' ) ) ) {
            return array(
                'id'   => (string) $download_id,
                'file' => $file,
                'name' => $name,
            );
        }
    }

    return null;
}

function make_pdf_library_download_url( int $product_id ): string {
    return wp_nonce_url(
        add_query_arg(
            array(
                'action'     => 'drielo_admin_pdf_download',
                'product_id' => $product_id,
            ),
            admin_url( 'admin-post.php' )
        ),
        'drielo_admin_pdf_download_' . $product_id
    );
}

function make_pdf_library_local_file( string $file ): string {
    $candidate = '';

    if ( preg_match( '#^https?://#i', $file ) ) {
        $uploads = wp_get_upload_dir();
        $baseurl = isset( $uploads['baseurl'] ) ? untrailingslashit( (string) $uploads['baseurl'] ) : '';
        $basedir = isset( $uploads['basedir'] ) ? untrailingslashit( (string) $uploads['basedir'] ) : '';

        if ( '' !== $baseurl && '' !== $basedir && 0 === strpos( $file, $baseurl . '/' ) ) {
            $relative = rawurldecode( substr( $file, strlen( $baseurl ) ) );
            $candidate = $basedir . $relative;
        }
    } else {
        $candidate = $file;
        if ( '' !== $candidate && '/' !== substr( $candidate, 0, 1 ) ) {
            $candidate = ABSPATH . ltrim( $candidate, '/' );
        }
    }

    if ( '' === $candidate || ! is_file( $candidate ) || ! is_readable( $candidate ) ) {
        return '';
    }

    $real = realpath( $candidate );
    if ( false === $real ) { return ''; }

    $real = wp_normalize_path( $real );
    $allowed_roots = array_filter(
        array_map(
            static function ( string $root ): string {
                $resolved = realpath( $root );
                return false === $resolved ? '' : trailingslashit( wp_normalize_path( $resolved ) );
            },
            array( ABSPATH, WP_CONTENT_DIR )
        )
    );

    foreach ( $allowed_roots as $root ) {
        if ( 0 === strpos( $real, $root ) ) { return $real; }
    }

    return '';
}

function make_pdf_library_download(): void {
    $product_id = isset( $_GET['product_id'] ) ? absint( $_GET['product_id'] ) : 0;

    if ( $product_id <= 0 || ! current_user_can( 'manage_options' ) ) {
        wp_die( esc_html__( 'You do not have permission to download this file.', 'make' ), '', array( 'response' => 403 ) );
    }

    check_admin_referer( 'drielo_admin_pdf_download_' . $product_id );

    $product = wc_get_product( $product_id );
    if ( ! $product instanceof WC_Product ) {
        wp_die( esc_html__( 'Product not found.', 'make' ), '', array( 'response' => 404 ) );
    }

    $record = make_pdf_library_pdf_record( $product );
    if ( null === $record ) {
        wp_die( esc_html__( 'This product does not have a PDF download.', 'make' ), '', array( 'response' => 404 ) );
    }

    $file = (string) $record['file'];
    $local = make_pdf_library_local_file( $file );

    if ( '' !== $local ) {
        $path = (string) wp_parse_url( $file, PHP_URL_PATH );
        $filename = sanitize_file_name( basename( rawurldecode( $path ) ) );
        if ( '' === $filename || ! str_ends_with( strtolower( $filename ), '.pdf' ) ) {
            $code = function_exists( 'make_product_reference_code' ) ? make_product_reference_code( $product_id ) : '';
            $filename = 'Drielo_' . ( '' !== $code ? $code : (string) $product_id ) . '.pdf';
        }

        while ( ob_get_level() ) { ob_end_clean(); }

        nocache_headers();
        header( 'Content-Type: application/pdf' );
        header( 'Content-Disposition: attachment; filename="' . str_replace( '"', '', $filename ) . '"' );
        header( 'Content-Length: ' . (string) filesize( $local ) );
        header( 'X-Content-Type-Options: nosniff' );
        header( 'X-Robots-Tag: noindex, nofollow, noarchive', true );

        readfile( $local );
        exit;
    }

    $validated = wp_http_validate_url( $file );
    if ( ! $validated ) {
        wp_die( esc_html__( 'The PDF file location is invalid.', 'make' ), '', array( 'response' => 500 ) );
    }

    if ( ! wp_safe_redirect( $validated, 302, 'Drielo PDF Library' ) ) {
        wp_die( esc_html__( 'The PDF file could not be opened safely.', 'make' ), '', array( 'response' => 500 ) );
    }
    exit;
}
add_action( 'admin_post_drielo_admin_pdf_download', 'make_pdf_library_download' );

function make_pdf_library_download_login(): void {
    auth_redirect();
    exit;
}
add_action( 'admin_post_nopriv_drielo_admin_pdf_download', 'make_pdf_library_download_login' );
