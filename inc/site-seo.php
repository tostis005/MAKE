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
