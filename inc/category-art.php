<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/**
 * High-density Drielo cross-stitch category artwork.
 * The approved motifs are stored as compact 80×45 stitch maps, avoiding
 * compressed bitmap sprites so every X stays crisp on standard and Retina screens.
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
    return array_map( 'make_stitch_decode_row', $patterns[ $theme ] );
}

function make_stitch_theme_art_html( string $theme, string $class = 'stitch-theme-art' ): string {
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
    $cols = strlen( (string) $pattern[0] );
    $rows = count( $pattern );
    $width = $cols * $cell;
    $height = $rows * $cell;
    $arm = 1.82;
    $grid_id = 'grid-' . $theme . '-' . wp_rand( 1000, 999999 );
    $paths = array_fill_keys( array_keys( $palette ), '' );

    foreach ( $pattern as $row_index => $row ) {
        foreach ( str_split( $row ) as $col_index => $code ) {
            if ( ! isset( $palette[ $code ] ) ) { continue; }

            $cx = $col_index * $cell + ( $cell / 2 );
            $cy = $row_index * $cell + ( $cell / 2 );
            $x1 = round( $cx - $arm, 2 );
            $x2 = round( $cx + $arm, 2 );
            $y1 = round( $cy - $arm, 2 );
            $y2 = round( $cy + $arm, 2 );

            $paths[ $code ] .= 'M' . $x1 . ' ' . $y1 . 'L' . $x2 . ' ' . $y2
                . 'M' . $x2 . ' ' . $y1 . 'L' . $x1 . ' ' . $y2;
        }
    }

    $svg = '<svg viewBox="0 0 ' . $width . ' ' . $height . '" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">'
        . '<defs><pattern id="' . esc_attr( $grid_id ) . '" width="' . $cell . '" height="' . $cell . '" patternUnits="userSpaceOnUse">'
        . '<rect width="' . $cell . '" height="' . $cell . '" fill="#FCF8F2"></rect>'
        . '<path d="M' . $cell . ' 0H0V' . $cell . '" fill="none" stroke="#E8DED5" stroke-width=".34"></path>'
        . '</pattern></defs>'
        . '<rect width="100%" height="100%" rx="12" fill="url(#' . esc_attr( $grid_id ) . ')"></rect>';

    foreach ( $paths as $code => $d ) {
        if ( '' === $d ) { continue; }
        $svg .= '<path d="' . esc_attr( $d ) . '" fill="none" stroke="#FFFFFF" stroke-opacity=".34" stroke-width="2.05" stroke-linecap="round"></path>'
            . '<path d="' . esc_attr( $d ) . '" fill="none" stroke="' . esc_attr( $palette[ $code ] ) . '" stroke-width="1.38" stroke-linecap="round"></path>';
    }

    $svg .= '</svg>';

    return '<span class="' . esc_attr( $class . ' ' . $class . '--' . $theme ) . '" aria-hidden="true">' . $svg . '</span>';
}
