<?php
/**
 * Site-wide SEO for the bilingual Drielo home routes.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function make_is_home_route(): bool {
    $path = function_exists( 'make_request_path' ) ? make_request_path() : '/';
    return '/' === $path || '/en' === $path;
}

function make_home_seo_title(): string {
    return make_t(
        'Patrones digitales de punto de cruz | Drielo',
        'Digital Cross Stitch Patterns | Drielo'
    );
}

function make_home_seo_description(): string {
    return make_t(
        'Descubre patrones PDF descargables de punto de cruz con gráficos claros, diseños cuidados y acceso digital para empezar tu próximo proyecto.',
        'Discover downloadable cross stitch pattern PDFs with clear charts, considered designs and digital access for your next project.'
    );
}

function make_home_seo_document_title( string $title ): string {
    return make_is_home_route() ? make_home_seo_title() : $title;
}
add_filter( 'pre_get_document_title', 'make_home_seo_document_title', 120 );

function make_home_seo_head(): void {
    if ( ! make_is_home_route() ) { return; }

    $language   = make_current_language();
    $canonical  = make_home_url( $language );
    $description = make_home_seo_description();

    if ( function_exists( 'make_has_seo_plugin' ) && ! make_has_seo_plugin() ) {
        echo '<meta name="description" content="' . esc_attr( $description ) . '">' . "\n";
        echo '<link rel="canonical" href="' . esc_url( $canonical ) . '">' . "\n";
    }

    if ( ! function_exists( 'pll_current_language' ) ) {
        $es = make_home_url( 'es' );
        $en = make_home_url( 'en' );
        echo '<link rel="alternate" hreflang="es-ES" href="' . esc_url( $es ) . '">' . "\n";
        echo '<link rel="alternate" hreflang="en-US" href="' . esc_url( $en ) . '">' . "\n";
        echo '<link rel="alternate" hreflang="x-default" href="' . esc_url( $es ) . '">' . "\n";
    }

    if ( function_exists( 'make_has_seo_plugin' ) && make_has_seo_plugin() ) { return; }

    $organization = array(
        '@type' => 'Organization',
        '@id'   => home_url( '/#organization' ),
        'name'  => make_brand_name(),
        'url'   => home_url( '/' ),
    );
    $logo = get_site_icon_url( 512 );
    if ( $logo ) {
        $organization['logo'] = array(
            '@type' => 'ImageObject',
            'url'   => $logo,
        );
    }

    $website = array(
        '@type'       => 'WebSite',
        '@id'         => home_url( '/#website' ),
        'url'         => home_url( '/' ),
        'name'        => make_brand_name(),
        'description' => $description,
        'inLanguage'  => 'en' === $language ? 'en-US' : 'es-ES',
        'publisher'   => array( '@id' => home_url( '/#organization' ) ),
    );

    $schema = array(
        '@context' => 'https://schema.org',
        '@graph'   => array( $organization, $website ),
    );

    echo '<script type="application/ld+json">' . wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) . '</script>' . "\n";
}
add_action( 'wp_head', 'make_home_seo_head', 7 );


function make_social_seo_context(): array {
    $title       = wp_get_document_title();
    $description = '';
    $url         = '';
    $image       = '';
    $type        = 'website';

    if ( make_is_home_route() ) {
        $description = make_home_seo_description();
        $url = make_home_url();
    } elseif ( is_singular( 'product' ) ) {
        $product_id = get_queried_object_id();
        $language   = make_current_language();
        $description = trim( (string) get_post_meta( $product_id, '_drielo_meta_description_' . $language, true ) );
        if ( '' === $description ) {
            $description = trim( wp_strip_all_tags( (string) get_post_meta( $product_id, '_drielo_short_description_' . $language, true ) ) );
        }
        if ( '' === $description ) {
            $description = trim( wp_strip_all_tags( (string) get_post_field( 'post_excerpt', $product_id ) ) );
        }
        $url = function_exists( 'make_product_url' ) ? make_product_url( $product_id, $language ) : get_permalink( $product_id );
        if ( has_post_thumbnail( $product_id ) ) {
            $image = (string) wp_get_attachment_image_url( get_post_thumbnail_id( $product_id ), 'large' );
        }
    } elseif ( is_singular( 'post' ) ) {
        $post_id = get_queried_object_id();
        $description = trim( (string) get_post_meta( $post_id, '_make_meta_description', true ) );
        if ( '' === $description ) {
            $description = trim( wp_strip_all_tags( (string) get_the_excerpt( $post_id ) ) );
        }
        $url  = get_permalink( $post_id );
        $type = 'article';
        if ( has_post_thumbnail( $post_id ) ) {
            $image = (string) wp_get_attachment_image_url( get_post_thumbnail_id( $post_id ), 'large' );
        }
    } elseif ( ( function_exists( 'is_shop' ) && is_shop() ) || is_tax( array( 'product_collection', 'product_cat', 'pa_technique' ) ) ) {
        $description = function_exists( 'make_store_seo_archive_description' ) ? make_store_seo_archive_description() : '';
        $url = function_exists( 'make_store_seo_archive_url' ) ? make_store_seo_archive_url() : '';
    } elseif ( is_category() ) {
        $description = function_exists( 'make_editorial_archive_description' ) ? make_editorial_archive_description() : '';
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $link = get_category_link( $term );
            if ( ! is_wp_error( $link ) ) { $url = (string) $link; }
        }
    }

    if ( '' === $description ) {
        $description = trim( (string) get_bloginfo( 'description' ) );
    }
    $description = wp_html_excerpt( wp_strip_all_tags( $description ), 200, '…' );
    if ( '' === $url ) {
        $url = home_url( make_request_path() . '/' );
    }
    if ( '' === $image ) {
        $image = (string) get_site_icon_url( 512 );
    }

    return array(
        'title'       => $title,
        'description' => $description,
        'url'         => $url,
        'image'       => $image,
        'type'        => $type,
    );
}

function make_social_seo_head(): void {
    if ( function_exists( 'make_has_seo_plugin' ) && make_has_seo_plugin() ) { return; }
    if ( is_search() || is_404() || is_feed() ) { return; }

    $meta = make_social_seo_context();
    if ( '' === $meta['title'] || '' === $meta['url'] ) { return; }

    echo '<meta property="og:site_name" content="' . esc_attr( make_brand_name() ) . '">' . "\n";
    echo '<meta property="og:type" content="' . esc_attr( $meta['type'] ) . '">' . "\n";
    echo '<meta property="og:title" content="' . esc_attr( $meta['title'] ) . '">' . "\n";
    echo '<meta property="og:url" content="' . esc_url( $meta['url'] ) . '">' . "\n";
    if ( '' !== $meta['description'] ) {
        echo '<meta property="og:description" content="' . esc_attr( $meta['description'] ) . '">' . "\n";
    }
    if ( '' !== $meta['image'] ) {
        echo '<meta property="og:image" content="' . esc_url( $meta['image'] ) . '">' . "\n";
    }
    echo '<meta name="twitter:card" content="' . ( '' !== $meta['image'] ? 'summary_large_image' : 'summary' ) . '">' . "\n";
    echo '<meta name="twitter:title" content="' . esc_attr( $meta['title'] ) . '">' . "\n";
    if ( '' !== $meta['description'] ) {
        echo '<meta name="twitter:description" content="' . esc_attr( $meta['description'] ) . '">' . "\n";
    }
    if ( '' !== $meta['image'] ) {
        echo '<meta name="twitter:image" content="' . esc_url( $meta['image'] ) . '">' . "\n";
    }
}
add_action( 'wp_head', 'make_social_seo_head', 9 );

function make_store_breadcrumb_schema_head(): void {
    if ( function_exists( 'make_has_seo_plugin' ) && make_has_seo_plugin() ) { return; }
    if ( ! ( is_singular( 'product' ) || is_tax( array( 'product_collection', 'pa_technique' ) ) || ( function_exists( 'is_shop' ) && is_shop() ) ) ) {
        return;
    }

    $language = make_current_language();
    $items = array(
        array(
            '@type'    => 'ListItem',
            'position' => 1,
            'name'     => make_t( 'Inicio', 'Home' ),
            'item'     => make_home_url( $language ),
        ),
        array(
            '@type'    => 'ListItem',
            'position' => 2,
            'name'     => make_t( 'Tienda de patrones', 'Pattern shop' ),
            'item'     => make_shop_url( $language ),
        ),
    );

    if ( is_tax( array( 'product_collection', 'pa_technique' ) ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $name = 'product_collection' === $term->taxonomy && function_exists( 'make_collection_display_name' )
                ? make_collection_display_name( $term )
                : ( function_exists( 'make_store_technique_label' ) ? make_store_technique_label( (string) $term->slug, $language ) : (string) $term->name );
            $items[] = array(
                '@type'    => 'ListItem',
                'position' => 3,
                'name'     => $name,
                'item'     => make_store_term_url( $term, $language ),
            );
        }
    } elseif ( is_singular( 'product' ) ) {
        $product_id = get_queried_object_id();
        $collection = function_exists( 'make_primary_product_collection' ) ? make_primary_product_collection( $product_id ) : null;
        if ( $collection instanceof WP_Term && ( ! function_exists( 'make_collection_is_visible' ) || make_collection_is_visible( $collection ) ) ) {
            $items[] = array(
                '@type'    => 'ListItem',
                'position' => count( $items ) + 1,
                'name'     => function_exists( 'make_collection_display_name' ) ? make_collection_display_name( $collection ) : (string) $collection->name,
                'item'     => make_store_term_url( $collection, $language ),
            );
        }
        $items[] = array(
            '@type'    => 'ListItem',
            'position' => count( $items ) + 1,
            'name'     => get_the_title( $product_id ),
            'item'     => make_product_url( $product_id, $language ),
        );
    }

    $schema = array(
        '@context'        => 'https://schema.org',
        '@type'           => 'BreadcrumbList',
        'itemListElement' => $items,
    );
    echo '<script type="application/ld+json">' . wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) . '</script>' . "\n";
}
add_action( 'wp_head', 'make_store_breadcrumb_schema_head', 10 );
