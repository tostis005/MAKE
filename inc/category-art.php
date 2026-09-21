<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/**
 * Drielo category artwork using the exact generated cross-stitch compositions.
 * One 3×3 WebP sprite keeps the nine category cards visually identical to the
 * approved generated artwork while loading a single cacheable image.
 */
function make_category_art_sprite_url(): string {
    $relative = '/assets/images/categories/category-art-generated.webp';
    $path = get_template_directory() . $relative;
    $version = is_file( $path ) ? (string) filemtime( $path ) : wp_get_theme()->get( 'Version' );
    return add_query_arg( 'v', rawurlencode( $version ), get_template_directory_uri() . $relative );
}

function make_stitch_theme_art_html( string $theme, string $class = 'stitch-theme-art' ): string {
    $positions = array(
        'animals'   => array( '0%', '0%' ),
        'celestial' => array( '50%', '0%' ),
        'florals'   => array( '100%', '0%' ),
        'food'      => array( '0%', '50%' ),
        'geometric' => array( '50%', '50%' ),
        'pop-art'   => array( '100%', '50%' ),
        'quotes'    => array( '0%', '100%' ),
        'retro'     => array( '50%', '100%' ),
        'seasonal'  => array( '100%', '100%' ),
    );

    $theme = sanitize_key( $theme );
    if ( ! isset( $positions[ $theme ] ) ) { $theme = 'florals'; }

    return '<span class="' . esc_attr( $class . ' ' . $class . '--' . $theme ) . '" aria-hidden="true"'
        . ' style="--drielo-category-art:url(&quot;' . esc_url( make_category_art_sprite_url() ) . '&quot;);'
        . '--drielo-art-x:' . esc_attr( $positions[ $theme ][0] ) . ';'
        . '--drielo-art-y:' . esc_attr( $positions[ $theme ][1] ) . '"></span>';
}
