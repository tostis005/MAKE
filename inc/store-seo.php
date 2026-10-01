<?php
/**
 * Search discovery for the Drielo storefront.
 *
 * Keeps the custom bilingual shop URLs self-describing for search engines and
 * makes collection/technique archives useful commercial landing pages.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function make_store_seo_page_number(): int {
    return max( 1, (int) get_query_var( 'paged' ) );
}

function make_store_seo_paged_url( string $base, int $page = 1 ): string {
    if ( $page <= 1 ) { return $base; }
    return trailingslashit( $base ) . 'page/' . $page . '/';
}

function make_store_seo_archive_base_url( string $language = '' ): string {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();

    if ( function_exists( 'is_shop' ) && is_shop() ) {
        $view = function_exists( 'make_store_view' ) ? make_store_view() : 'patterns';
        return function_exists( 'make_shop_view_url' ) ? make_shop_view_url( $view, $language ) : make_shop_url( $language );
    }

    if ( is_tax( array( 'product_collection', 'product_cat', 'pa_technique' ) ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term && function_exists( 'make_store_term_url' ) ) {
            return make_store_term_url( $term, $language );
        }
    }

    return '';
}

function make_store_seo_archive_url( string $language = '' ): string {
    $base = make_store_seo_archive_base_url( $language );
    return '' !== $base ? make_store_seo_paged_url( $base, make_store_seo_page_number() ) : '';
}

function make_store_seo_collection_techniques( WP_Term $term ): array {
    if ( 'product_collection' !== $term->taxonomy || ! function_exists( 'make_collection_product_ids' ) ) { return array(); }

    $techniques = array();
    foreach ( make_collection_product_ids( $term ) as $product_id ) {
        $slug = function_exists( 'make_store_product_technique' ) ? make_store_product_technique( (int) $product_id ) : '';
        if ( '' !== $slug ) { $techniques[ $slug ] = true; }
    }
    return array_keys( $techniques );
}

function make_store_seo_archive_title(): string {
    $language = make_current_language();
    $page     = make_store_seo_page_number();
    $title    = '';

    if ( function_exists( 'is_shop' ) && is_shop() ) {
        $view = function_exists( 'make_store_view' ) ? make_store_view() : 'patterns';
        if ( 'collections' === $view ) {
            $title = 'en' === $language ? 'Digital Pattern Collections' : 'Colecciones de patrones digitales';
        } else {
            $title = 'en' === $language ? 'Cross Stitch & Craft Pattern PDFs' : 'Patrones PDF de punto de cruz y manualidades';
        }
    } elseif ( is_tax( 'pa_technique' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $label = function_exists( 'make_store_technique_label' )
                ? make_store_technique_label( (string) $term->slug, $language )
                : (string) $term->name;
            if ( 'cross-stitch' === $term->slug ) {
                $title = 'en' === $language ? 'Cross Stitch Patterns PDF' : 'Patrones de Punto de Cruz PDF';
            } else {
                $title = 'en' === $language ? $label . ' Patterns PDF' : 'Patrones PDF de ' . $label;
            }
        }
    } elseif ( is_tax( 'product_collection' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $name = function_exists( 'make_collection_display_name' ) ? make_collection_display_name( $term ) : (string) $term->name;
            $techniques = make_store_seo_collection_techniques( $term );
            if ( 1 === count( $techniques ) && 'cross-stitch' === reset( $techniques ) ) {
                $title = 'en' === $language ? $name . ' Cross Stitch Patterns PDF' : $name . ' · Patrones de Punto de Cruz PDF';
            } else {
                $title = 'en' === $language ? $name . ' Pattern PDFs' : $name . ' · Patrones PDF';
            }
        }
    } elseif ( is_tax( 'product_cat' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $title = 'en' === $language ? $term->name . ' Pattern PDFs' : $term->name . ' · Patrones PDF';
        }
    }

    if ( '' === $title ) { return ''; }
    if ( $page > 1 ) {
        $title .= ' · ' . ( 'en' === $language ? 'Page ' . $page : 'Página ' . $page );
    }
    return $title . ' | ' . make_brand_name();
}

function make_store_seo_filter_document_title( string $title ): string {
    $store_title = make_store_seo_archive_title();
    return '' !== $store_title ? $store_title : $title;
}
add_filter( 'pre_get_document_title', 'make_store_seo_filter_document_title', 99 );

function make_store_seo_archive_description(): string {
    $language = make_current_language();

    if ( function_exists( 'is_shop' ) && is_shop() ) {
        $view = function_exists( 'make_store_view' ) ? make_store_view() : 'patterns';
        if ( 'collections' === $view ) {
            return 'en' === $language
                ? 'Browse themed collections of downloadable cross stitch, crochet and latch hook pattern PDFs, with clear charts and project details.'
                : 'Explora colecciones temáticas de patrones PDF descargables de punto de cruz, crochet y latch hook, con gráficos claros y detalles del proyecto.';
        }
        return 'en' === $language
            ? 'Shop downloadable cross stitch, crochet and latch hook pattern PDFs with printable charts, project details and instant digital access.'
            : 'Compra patrones PDF descargables de punto de cruz, crochet y latch hook con gráficos imprimibles, detalles del proyecto y acceso digital.';
    }

    if ( is_tax( 'pa_technique' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $label = function_exists( 'make_store_technique_label' )
                ? make_store_technique_label( (string) $term->slug, $language )
                : (string) $term->name;
            $count = max( 0, (int) $term->count );
            if ( 'cross-stitch' === $term->slug ) {
                return 'en' === $language
                    ? sprintf( 'Browse %d downloadable cross stitch pattern PDFs with printable symbol charts, DMC colour information and finished-design previews.', $count )
                    : sprintf( 'Explora %d patrones PDF descargables de punto de cruz con gráficos de símbolos imprimibles, colores DMC y vistas del diseño terminado.', $count );
            }
            return 'en' === $language
                ? sprintf( 'Browse %d downloadable %s pattern PDFs with clear charts and practical project details.', $count, $label )
                : sprintf( 'Explora %d patrones PDF descargables de %s con gráficos claros y detalles prácticos del proyecto.', $count, $label );
        }
    }

    if ( is_tax( 'product_collection' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            $name = function_exists( 'make_collection_display_name' ) ? make_collection_display_name( $term ) : (string) $term->name;
            $stats = function_exists( 'make_collection_stats' ) ? make_collection_stats( $term ) : array();
            $count = (int) ( $stats['pattern_count'] ?? $term->count );
            $techniques = make_store_seo_collection_techniques( $term );
            if ( 1 === count( $techniques ) && 'cross-stitch' === reset( $techniques ) ) {
                return 'en' === $language
                    ? sprintf( 'Explore %s: %d downloadable cross stitch pattern PDFs with printable charts, DMC colour details and finished-design previews.', $name, $count )
                    : sprintf( 'Explora %s: %d patrones PDF descargables de punto de cruz con gráficos imprimibles, colores DMC y vistas del diseño terminado.', $name, $count );
            }
            return 'en' === $language
                ? sprintf( 'Explore %s: %d downloadable digital pattern PDFs with clear charts, project details and finished-design previews.', $name, $count )
                : sprintf( 'Explora %s: %d patrones PDF digitales descargables con gráficos claros, detalles del proyecto y vistas del diseño terminado.', $name, $count );
        }
    }

    if ( is_tax( 'product_cat' ) ) {
        $term = get_queried_object();
        if ( $term instanceof WP_Term ) {
            return 'en' === $language
                ? sprintf( 'Browse %s digital pattern PDFs from Drielo, with downloadable charts and practical project details.', $term->name )
                : sprintf( 'Explora patrones PDF digitales de %s en Drielo, con gráficos descargables y detalles prácticos del proyecto.', $term->name );
        }
    }

    return '';
}

function make_store_seo_head_meta(): void {
    if ( ! ( ( function_exists( 'is_shop' ) && is_shop() ) || is_tax( array( 'product_collection', 'product_cat', 'pa_technique' ) ) ) ) {
        return;
    }

    $description = make_store_seo_archive_description();
    $canonical   = make_store_seo_archive_url();

    if ( function_exists( 'make_has_seo_plugin' ) && ! make_has_seo_plugin() ) {
        if ( '' !== $description ) {
            echo '<meta name="description" content="' . esc_attr( $description ) . '">' . "\n";
        }
        if ( '' !== $canonical ) {
            echo '<link rel="canonical" href="' . esc_url( $canonical ) . '">' . "\n";
        }
    }

    if ( ! function_exists( 'pll_current_language' ) ) {
        $es = make_store_seo_archive_url( 'es' );
        $en = make_store_seo_archive_url( 'en' );
        if ( '' !== $es ) {
            echo '<link rel="alternate" hreflang="es-ES" href="' . esc_url( $es ) . '">' . "\n";
            echo '<link rel="alternate" hreflang="x-default" href="' . esc_url( $es ) . '">' . "\n";
        }
        if ( '' !== $en ) {
            echo '<link rel="alternate" hreflang="en-US" href="' . esc_url( $en ) . '">' . "\n";
        }
    }

    if ( function_exists( 'make_has_seo_plugin' ) && make_has_seo_plugin() ) { return; }

    global $wp_query;
    $items = array();
    $offset = ( make_store_seo_page_number() - 1 ) * max( 1, (int) get_query_var( 'posts_per_page', (int) get_option( 'posts_per_page', 20 ) ) );
    if ( $wp_query instanceof WP_Query ) {
        foreach ( (array) $wp_query->posts as $post ) {
            if ( ! $post instanceof WP_Post || 'product' !== $post->post_type ) { continue; }
            $items[] = array(
                '@type'    => 'ListItem',
                'position' => $offset + count( $items ) + 1,
                'url'      => function_exists( 'make_product_url' ) ? make_product_url( $post, make_current_language() ) : get_permalink( $post ),
                'name'     => get_the_title( $post ),
            );
        }
    }

    $schema = array(
        '@context'    => 'https://schema.org',
        '@type'       => 'CollectionPage',
        'name'        => preg_replace( '/\s*\|\s*' . preg_quote( make_brand_name(), '/' ) . '$/u', '', make_store_seo_archive_title() ),
        'description' => $description,
        'url'         => $canonical,
        'inLanguage'  => 'en' === make_current_language() ? 'en-US' : 'es-ES',
    );
    if ( ! empty( $items ) ) {
        $schema['mainEntity'] = array(
            '@type'           => 'ItemList',
            'itemListElement' => $items,
        );
    }

    echo '<script type="application/ld+json">' . wp_json_encode( $schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) . '</script>' . "\n";
}
add_action( 'wp_head', 'make_store_seo_head_meta', 7 );

function make_store_seo_has_filter_query(): bool {
    foreach ( array_keys( $_GET ) as $key ) {
        $key = sanitize_key( (string) $key );
        if ( 0 === strpos( $key, 'drielo_' ) || in_array( $key, array( 'orderby', 'min_price', 'max_price', 'rating_filter', 'filtering' ), true ) ) {
            return true;
        }
    }
    return false;
}

function make_store_seo_robots( array $robots ): array {
    if ( function_exists( 'is_cart' ) && ( is_cart() || is_checkout() || is_account_page() ) ) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
        return $robots;
    }

    if ( ( ( function_exists( 'is_shop' ) && is_shop() ) || is_tax( array( 'product_collection', 'product_cat', 'pa_technique' ) ) ) && make_store_seo_has_filter_query() ) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
    }

    return $robots;
}
add_filter( 'wp_robots', 'make_store_seo_robots', 30 );
