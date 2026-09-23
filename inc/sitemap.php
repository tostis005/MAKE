<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/**
 * Drielo language sitemaps.
 *
 * Public endpoints:
 * - /sitemap.xml    -> sitemap index
 * - /sitemap-es.xml -> Spanish URLs
 * - /sitemap-en.xml -> English URLs
 *
 * Mirrors the language-separated sitemap architecture used by HOME.
 */

function make_sitemap_xml_escape( string $value ): string {
    return htmlspecialchars( $value, ENT_QUOTES | ENT_XML1, 'UTF-8' );
}

function make_sitemap_language_meta_query( string $language ): array {
    if ( 'en' === $language ) {
        return array(
            array( 'key' => '_make_language', 'value' => 'en', 'compare' => '=' ),
        );
    }

    return array(
        'relation' => 'OR',
        array( 'key' => '_make_language', 'compare' => 'NOT EXISTS' ),
        array( 'key' => '_make_language', 'value' => 'en', 'compare' => '!=' ),
    );
}

function make_sitemap_urls( string $language ): array {
    $language = 'en' === $language ? 'en' : 'es';
    $urls = array();

    $add = static function( array &$list, string $loc, string $lastmod = '' ): void {
        if ( '' === $loc ) { return; }
        $list[ $loc ] = array( 'loc' => $loc, 'lastmod' => $lastmod );
    };

    $add( $urls, make_home_url( $language ) );
    $add( $urls, make_journal_url( $language ) );

    if ( function_exists( 'make_editorial_craft_config' ) && function_exists( 'make_editorial_craft_url' ) ) {
        foreach ( array_keys( make_editorial_craft_config() ) as $craft ) {
            if ( function_exists( 'make_editorial_craft_has_content' ) && ! make_editorial_craft_has_content( (string) $craft, $language ) ) { continue; }
            $add( $urls, make_editorial_craft_url( (string) $craft, $language ) );

            if ( function_exists( 'make_editorial_sections_for_craft' ) && function_exists( 'make_editorial_craft_section_url' ) ) {
                foreach ( make_editorial_sections_for_craft( (string) $craft, $language ) as $section ) {
                    if ( ! empty( $section['id'] ) ) {
                        $add( $urls, make_editorial_craft_section_url( (string) $craft, (string) $section['id'], $language ) );
                    }
                }
            }
        }
    }

    if ( function_exists( 'make_shop_view_url' ) ) {
        $add( $urls, make_shop_view_url( 'patterns', $language ) );
        $add( $urls, make_shop_view_url( 'collections', $language ) );
    }

    if ( function_exists( 'make_stitch_theme_cards' ) && function_exists( 'make_stitch_theme_url' ) ) {
        foreach ( make_stitch_theme_cards( $language ) as $theme ) {
            if ( ! empty( $theme['id'] ) ) {
                $add( $urls, make_stitch_theme_url( (string) $theme['id'], $language ) );
            }
        }
    }

    foreach ( array( 'post', 'product' ) as $post_type ) {
        if ( ! post_type_exists( $post_type ) ) { continue; }

        $args = array(
            'post_type'      => $post_type,
            'post_status'    => 'publish',
            'posts_per_page' => -1,
            'orderby'        => 'modified',
            'order'          => 'DESC',
            'no_found_rows'  => true,
            'has_password'   => false,
        );
        if ( 'post' === $post_type ) {
            $args['meta_query'] = make_sitemap_language_meta_query( $language );
        }

        $items = get_posts( $args );
        foreach ( $items as $item ) {
            if ( ! $item instanceof WP_Post ) { continue; }

            $loc = 'product' === $post_type && function_exists( 'make_product_url' )
                ? make_product_url( $item, $language )
                : get_permalink( $item );
            if ( ! is_string( $loc ) || '' === $loc ) { continue; }

            $modified = '0000-00-00 00:00:00' !== $item->post_modified_gmt
                ? $item->post_modified_gmt
                : $item->post_modified;
            $lastmod = $modified ? mysql2date( 'c', $modified, false ) : '';

            $add( $urls, $loc, is_string( $lastmod ) ? $lastmod : '' );
        }
    }

    if ( function_exists( 'make_store_term_url' ) ) {
        foreach ( array( 'product_collection', 'product_cat' ) as $taxonomy ) {
            if ( ! taxonomy_exists( $taxonomy ) ) { continue; }
            $terms = get_terms( array( 'taxonomy' => $taxonomy, 'hide_empty' => true ) );
            if ( is_wp_error( $terms ) ) { continue; }
            foreach ( $terms as $term ) {
                if ( $term instanceof WP_Term ) { $add( $urls, make_store_term_url( $term, $language ) ); }
            }
        }
    }

    return array_values( $urls );
}

function make_render_sitemap_index(): void {
    $root = trailingslashit( home_url( '/' ) );
    $entries = array(
        $root . 'sitemap-es.xml',
        $root . 'sitemap-en.xml',
    );

    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    echo '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
    foreach ( $entries as $loc ) {
        echo '  <sitemap><loc>' . make_sitemap_xml_escape( $loc ) . "</loc></sitemap>\n";
    }
    echo "</sitemapindex>\n";
}

function make_render_language_sitemap( string $language ): void {
    $urls = make_sitemap_urls( $language );

    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
    foreach ( $urls as $entry ) {
        echo "  <url>\n";
        echo '    <loc>' . make_sitemap_xml_escape( (string) $entry['loc'] ) . "</loc>\n";
        if ( ! empty( $entry['lastmod'] ) ) {
            echo '    <lastmod>' . make_sitemap_xml_escape( (string) $entry['lastmod'] ) . "</lastmod>\n";
        }
        echo "  </url>\n";
    }
    echo "</urlset>\n";
}

function make_maybe_render_sitemap(): void {
    $uri  = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '';
    $path = trim( (string) wp_parse_url( $uri, PHP_URL_PATH ), '/' );

    if ( 'wp-sitemap.xml' === $path ) {
        wp_safe_redirect( home_url( '/sitemap.xml' ), 301 );
        exit;
    }

    if ( ! in_array( $path, array( 'sitemap.xml', 'sitemap-es.xml', 'sitemap-en.xml' ), true ) ) {
        return;
    }

    status_header( 200 );
    header( 'Content-Type: application/xml; charset=UTF-8' );
    header( 'Cache-Control: public, max-age=900' );

    if ( 'sitemap.xml' === $path ) {
        make_render_sitemap_index();
    } else {
        make_render_language_sitemap( 'sitemap-en.xml' === $path ? 'en' : 'es' );
    }

    exit;
}
add_action( 'template_redirect', 'make_maybe_render_sitemap', -100 );

add_filter( 'wp_sitemaps_enabled', '__return_false' );

add_filter(
    'robots_txt',
    static function( string $output, bool $public ): string {
        if ( ! $public ) { return $output; }

        $sitemap = home_url( '/sitemap.xml' );
        if ( false === stripos( $output, 'Sitemap: ' . $sitemap ) ) {
            $output = rtrim( $output ) . "\nSitemap: " . $sitemap . "\n";
        }

        return $output;
    },
    20,
    2
);
