<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/**
 * High-density Drielo cross-stitch category artwork.
 * Motifs use compact 80×45 stitch maps and are served as cacheable SVG images,
 * keeping every X crisp without bloating journal HTML.
 */
function make_stitch_theme_pattern_rle(): array {
    static $patterns = null;
    if ( is_array( $patterns ) ) { return $patterns; }

    $patterns = array_merge(
        require __DIR__ . '/category-art-data-1.php',
        require __DIR__ . '/category-art-data-2.php'
    );
    return $patterns;
}

function make_stitch_decode_row( string $encoded ): string {
    if ( '' === $encoded ) { return ''; }
    preg_match_all( '/(\d+)(.)/', $encoded, $matches, PREG_SET_ORDER );
    $row = '';
    foreach ( $matches as $match ) {
        $row .= str_repeat( (string) $match[2], (int) $match[1] );
    }
    return $row;
}

function make_stitch_theme_pattern( string $theme ): array {
    $patterns = make_stitch_theme_pattern_rle();
    if ( ! isset( $patterns[ $theme ] ) ) { $theme = 'florals'; }

    $rows = array_map( 'make_stitch_decode_row', $patterns[ $theme ] );
    $rows = array_slice( $rows, 0, 45 );
    while ( count( $rows ) < 45 ) { $rows[] = str_repeat( '.', 80 ); }

    return array_map(
        static fn( string $row ): string => substr( str_pad( $row, 80, '.' ), 0, 80 ),
        $rows
    );
}

function make_stitch_theme_svg( string $theme ): string {
    if ( ! isset( make_stitch_theme_config()[ $theme ] ) ) { $theme = 'florals'; }

    $pattern = make_stitch_theme_pattern( $theme );
    $palette = array(
        'p' => '#5A2E46',
        'r' => '#A94460',
        'd' => '#C98FA0',
        'h' => '#F1C9CC',
        'g' => '#7D8B63',
        'o' => '#5B6042',
        't' => '#C9A995',
        'b' => '#7A5138',
        'y' => '#BF8F48',
        'u' => '#89A5AE',
        'c' => '#3D2D37',
    );

    $cell = 6;
    $arm = 2;
    $paths = array_fill_keys( array_keys( $palette ), '' );

    foreach ( $pattern as $row_index => $row ) {
        foreach ( str_split( $row ) as $col_index => $code ) {
            if ( ! isset( $palette[ $code ] ) ) { continue; }

            $cx = $col_index * $cell + 3;
            $cy = $row_index * $cell + 3;
            $x1 = $cx - $arm;
            $x2 = $cx + $arm;
            $y1 = $cy - $arm;

            $paths[ $code ] .= 'M' . $x1 . ' ' . $y1 . 'l4 4M' . $x2 . ' ' . $y1 . 'l-4 4';
        }
    }

    $svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" aria-hidden="true" focusable="false">'
        . '<defs><pattern id="g" width="6" height="6" patternUnits="userSpaceOnUse">'
        . '<rect width="6" height="6" fill="#FCF8F2"/>'
        . '<path d="M6 0H0V6" fill="none" stroke="#E8DED5" stroke-width=".28"/>'
        . '</pattern></defs>'
        . '<rect width="480" height="270" rx="12" fill="url(#g)"/>';

    foreach ( $paths as $code => $d ) {
        if ( '' === $d ) { continue; }
        $svg .= '<path d="' . esc_attr( $d ) . '" fill="none" stroke="' . esc_attr( $palette[ $code ] )
            . '" stroke-width="1.45" stroke-linecap="round"/>';
    }

    return $svg . '</svg>';
}

function make_category_art_url( string $theme ): string {
    $theme = sanitize_key( $theme );
    if ( ! isset( make_stitch_theme_config()[ $theme ] ) ) { $theme = 'florals'; }
    return home_url( '/category-art/' . rawurlencode( $theme ) . '.svg' );
}

function make_stitch_theme_art_html( string $theme, string $class = 'stitch-theme-art' ): string {
    if ( ! isset( make_stitch_theme_config()[ $theme ] ) ) { $theme = 'florals'; }

    return '<span class="' . esc_attr( $class . ' ' . $class . '--' . $theme ) . '" aria-hidden="true">'
        . '<img src="' . esc_url( make_category_art_url( $theme ) ) . '" alt="" width="480" height="270" loading="lazy" decoding="async">'
        . '</span>';
}

function make_category_art_rewrite_rule(): void {
    add_rewrite_rule( '^category-art/([a-z0-9-]+)\.svg$', 'index.php?make_category_art=$matches[1]', 'top' );
}
add_action( 'init', 'make_category_art_rewrite_rule', 4 );

add_filter(
    'query_vars',
    static function( array $vars ): array {
        $vars[] = 'make_category_art';
        return $vars;
    }
);

function make_maybe_render_category_art(): void {
    $theme = sanitize_key( (string) get_query_var( 'make_category_art' ) );
    if ( '' === $theme ) { return; }

    if ( ! isset( make_stitch_theme_config()[ $theme ] ) ) {
        status_header( 404 );
        exit;
    }

    status_header( 200 );
    header( 'Content-Type: image/svg+xml; charset=UTF-8' );
    header( 'Cache-Control: public, max-age=604800, immutable' );
    header( 'X-Content-Type-Options: nosniff' );
    echo make_stitch_theme_svg( $theme );
    exit;
}
add_action( 'template_redirect', 'make_maybe_render_category_art', -120 );
