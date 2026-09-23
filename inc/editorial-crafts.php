<?php
/**
 * Multicraft editorial architecture for Drielo.
 *
 * Adds technique-first discovery, localized craft hubs, breadcrumbs and
 * context-aware commerce modules to the existing JSON-driven editorial system.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function make_editorial_craft_config(): array {
    return array(
        'cross-stitch' => array(
            'symbol' => '×',
            'es' => array(
                'slug' => 'punto-de-cruz',
                'label' => 'Punto de cruz',
                'description' => 'Guías, técnicas, materiales e ideas para disfrutar más del punto de cruz.',
                'meta_description' => 'Aprende punto de cruz con guías prácticas sobre patrones, materiales, técnicas, acabados e ideas de proyectos.',
            ),
            'en' => array(
                'slug' => 'cross-stitch',
                'label' => 'Cross Stitch',
                'description' => 'Guides, techniques, materials and ideas for getting more from cross stitch.',
                'meta_description' => 'Learn cross stitch with practical guides to patterns, materials, techniques, finishing and project ideas.',
            ),
        ),
        'c2c-crochet' => array(
            'symbol' => '↗',
            'es' => array(
                'slug' => 'c2c-crochet',
                'label' => 'C2C Crochet',
                'description' => 'Aprende corner-to-corner crochet, lee gráficos y convierte diseños por cuadrícula en proyectos de ganchillo.',
                'meta_description' => 'Guías de C2C Crochet sobre gráficos, cambios de color, aumentos, disminuciones, materiales y proyectos paso a paso.',
            ),
            'en' => array(
                'slug' => 'c2c-crochet',
                'label' => 'C2C Crochet',
                'description' => 'Learn corner-to-corner crochet, read graphs and turn grid designs into crochet projects.',
                'meta_description' => 'C2C crochet guides covering graphs, color changes, increases, decreases, materials and step-by-step projects.',
            ),
        ),
        'tapestry-crochet' => array(
            'symbol' => '▦',
            'es' => array(
                'slug' => 'tapestry-crochet',
                'label' => 'Tapestry Crochet',
                'description' => 'Colorwork, gráficos, cambios de color y técnicas para crear imágenes limpias con tapestry crochet.',
                'meta_description' => 'Aprende tapestry crochet con guías sobre colorwork, gráficos, cambios de color, tensión, materiales y proyectos.',
            ),
            'en' => array(
                'slug' => 'tapestry-crochet',
                'label' => 'Tapestry Crochet',
                'description' => 'Colorwork, charts, color changes and techniques for creating clean images with tapestry crochet.',
                'meta_description' => 'Learn tapestry crochet with guides to colorwork, charts, color changes, tension, materials and projects.',
            ),
        ),
        'latch-hook' => array(
            'symbol' => '⌁',
            'es' => array(
                'slug' => 'latch-hook',
                'label' => 'Latch Hook',
                'description' => 'Herramientas, lienzos, gráficos y acabados para convertir diseños en alfombras y piezas textiles.',
                'meta_description' => 'Aprende latch hook con guías sobre herramientas, canvas, hilo, lectura de patrones, acabados, alfombras y wall hangings.',
            ),
            'en' => array(
                'slug' => 'latch-hook',
                'label' => 'Latch Hook',
                'description' => 'Tools, canvas, charts and finishing techniques for turning designs into rugs and textile pieces.',
                'meta_description' => 'Learn latch hook with guides to tools, canvas, yarn, reading patterns, finishing, rugs and wall hangings.',
            ),
        ),
    );
}

function make_current_editorial_craft(): string {
    $config = make_editorial_craft_config();

    $id = sanitize_key( (string) get_query_var( 'make_craft' ) );
    if ( isset( $config[ $id ] ) ) { return $id; }

    $slug = sanitize_title( (string) get_query_var( 'make_craft_slug' ) );
    if ( '' === $slug ) { return ''; }

    $language = make_current_language();
    foreach ( $config as $craft_id => $craft ) {
        if ( $slug === sanitize_title( (string) ( $craft[ $language ]['slug'] ?? $craft_id ) ) ) {
            return (string) $craft_id;
        }
    }

    return '';
}

function make_editorial_craft_url( string $craft, string $language = '', int $page = 1 ): string {
    $config = make_editorial_craft_config();
    $craft = sanitize_key( $craft );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $page = max( 1, $page );

    if ( ! isset( $config[ $craft ] ) ) { return make_journal_url( $language ); }

    $slug = sanitize_title( (string) ( $config[ $craft ][ $language ]['slug'] ?? $craft ) );
    $base = 'en' === $language
        ? home_url( '/en/articles/craft/' . rawurlencode( $slug ) . '/' )
        : home_url( '/articulos/tecnica/' . rawurlencode( $slug ) . '/' );

    return 1 === $page ? $base : trailingslashit( $base ) . 'page/' . $page . '/';
}

function make_editorial_craft_has_content( string $craft, string $language = '' ): bool {
    $craft = sanitize_key( $craft );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();

    $query = new WP_Query(
        array(
            'post_type' => 'post',
            'post_status' => 'publish',
            'posts_per_page' => 1,
            'fields' => 'ids',
            'no_found_rows' => true,
            'ignore_sticky_posts' => true,
            'meta_query' => array(
                array( 'key' => '_make_language', 'value' => $language ),
            ),
            'tax_query' => array(
                array(
                    'taxonomy' => 'make_craft',
                    'field' => 'slug',
                    'terms' => array( $craft ),
                ),
            ),
        )
    );

    return ! empty( $query->posts );
}

function make_editorial_craft_cards( string $language = '', bool $include_empty = true ): array {
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $cards = array();

    foreach ( make_editorial_craft_config() as $id => $craft ) {
        $has_content = make_editorial_craft_has_content( (string) $id, $language );
        if ( ! $include_empty && ! $has_content ) { continue; }

        $cards[] = array(
            'id' => (string) $id,
            'label' => (string) $craft[ $language ]['label'],
            'description' => (string) $craft[ $language ]['description'],
            'symbol' => (string) $craft['symbol'],
            'has_content' => $has_content,
            'url' => $has_content ? make_editorial_craft_url( (string) $id, $language ) : '',
        );
    }

    return $cards;
}

function make_editorial_craft_section_url( string $craft, string $section, string $language = '', int $page = 1 ): string {
    $craft_config = make_editorial_craft_config();
    $section_config = make_editorial_section_config();
    $craft = sanitize_key( $craft );
    $section = sanitize_key( $section );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $page = max( 1, $page );

    if ( ! isset( $craft_config[ $craft ], $section_config[ $section ] ) ) {
        return make_editorial_craft_url( $craft, $language, $page );
    }

    $craft_slug = sanitize_title( (string) $craft_config[ $craft ][ $language ]['slug'] );
    $section_slug = sanitize_title( (string) $section_config[ $section ][ $language ]['slug'] );
    $base = 'en' === $language
        ? home_url( '/en/articles/craft/' . rawurlencode( $craft_slug ) . '/' . rawurlencode( $section_slug ) . '/' )
        : home_url( '/articulos/tecnica/' . rawurlencode( $craft_slug ) . '/' . rawurlencode( $section_slug ) . '/' );

    return 1 === $page ? $base : trailingslashit( $base ) . 'page/' . $page . '/';
}

function make_current_editorial_craft_section(): string {
    $slug = sanitize_title( (string) get_query_var( 'make_craft_section' ) );
    if ( '' === $slug ) { return ''; }

    $language = make_current_language();
    foreach ( make_editorial_section_config() as $section => $localized ) {
        if ( $slug === sanitize_title( (string) $localized[ $language ]['slug'] ) ) {
            return (string) $section;
        }
    }
    return '';
}

function make_editorial_sections_for_craft( string $craft, string $language = '' ): array {
    $craft = sanitize_key( $craft );
    $language = in_array( $language, array( 'es', 'en' ), true ) ? $language : make_current_language();
    $sections = array();

    foreach ( make_editorial_section_config() as $id => $localized ) {
        $cfg = $localized[ $language ];
        $term = get_category_by_slug( $cfg['slug'] );
        if ( ! $term instanceof WP_Term ) { continue; }

        $query = new WP_Query(
            array(
                'post_type' => 'post',
                'post_status' => 'publish',
                'posts_per_page' => 1,
                'fields' => 'ids',
                'ignore_sticky_posts' => true,
                'meta_query' => array(
                    array( 'key' => '_make_language', 'value' => $language ),
                ),
                'tax_query' => array(
                    array(
                        'taxonomy' => 'make_craft',
                        'field' => 'slug',
                        'terms' => array( $craft ),
                    ),
                ),
                'cat' => (int) $term->term_id,
            )
        );

        $count = (int) $query->found_posts;
        if ( $count < 1 ) { continue; }

        $sections[] = array(
            'id' => (string) $id,
            'label' => (string) $cfg['label'],
            'description' => (string) $cfg['description'],
            'count' => $count,
            'url' => make_editorial_craft_section_url( $craft, (string) $id, $language ),
        );
    }

    return $sections;
}

function make_article_craft( int $post_id ): string {
    $slugs = wp_get_post_terms( $post_id, 'make_craft', array( 'fields' => 'slugs' ) );
    if ( ! is_wp_error( $slugs ) && ! empty( $slugs ) ) {
        $slug = sanitize_key( (string) reset( $slugs ) );
        if ( isset( make_editorial_craft_config()[ $slug ] ) ) { return $slug; }
    }
    return 'cross-stitch';
}

function make_article_craft_url( int $post_id, string $language = '' ): string {
    return make_editorial_craft_url( make_article_craft( $post_id ), $language );
}

function make_editorial_craft_art_html( string $craft, string $class = '' ): string {
    $config = make_editorial_craft_config();
    $craft = isset( $config[ $craft ] ) ? $craft : 'cross-stitch';
    $symbol = (string) $config[ $craft ]['symbol'];
    $classes = trim( 'make-craft-art make-craft-art--' . sanitize_html_class( $craft ) . ' ' . $class );

    return '<span class="' . esc_attr( $classes ) . '" aria-hidden="true"><span class="make-craft-art-grid"></span><span class="make-craft-art-symbol">' . esc_html( $symbol ) . '</span></span>';
}

function make_editorial_craft_routes(): void {
    add_rewrite_rule( '^articulos/tecnica/([a-z0-9-]+)/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=es&make_craft_slug=$matches[1]&make_craft_section=$matches[2]', 'top' );
    add_rewrite_rule( '^articulos/tecnica/([a-z0-9-]+)/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&make_craft_slug=$matches[1]&make_craft_section=$matches[2]&paged=$matches[3]', 'top' );
    add_rewrite_rule( '^articulos/tecnica/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=es&make_craft_slug=$matches[1]', 'top' );
    add_rewrite_rule( '^articulos/tecnica/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=es&make_craft_slug=$matches[1]&paged=$matches[2]', 'top' );
    add_rewrite_rule( '^en/articles/craft/([a-z0-9-]+)/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=en&make_craft_slug=$matches[1]&make_craft_section=$matches[2]', 'top' );
    add_rewrite_rule( '^en/articles/craft/([a-z0-9-]+)/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&make_craft_slug=$matches[1]&make_craft_section=$matches[2]&paged=$matches[3]', 'top' );
    add_rewrite_rule( '^en/articles/craft/([a-z0-9-]+)/?$', 'index.php?make_journal=1&make_lang=en&make_craft_slug=$matches[1]', 'top' );
    add_rewrite_rule( '^en/articles/craft/([a-z0-9-]+)/page/([0-9]+)/?$', 'index.php?make_journal=1&make_lang=en&make_craft_slug=$matches[1]&paged=$matches[2]', 'top' );
}
add_action( 'init', 'make_editorial_craft_routes', 19 );

function make_editorial_craft_query_vars( array $vars ): array {
    $vars[] = 'make_craft';
    $vars[] = 'make_craft_slug';
    $vars[] = 'make_craft_section';
    return $vars;
}
add_filter( 'query_vars', 'make_editorial_craft_query_vars', 20 );

function make_editorial_craft_main_query( WP_Query $query ): void {
    if ( is_admin() || ! $query->is_main_query() || (int) get_query_var( 'make_journal' ) !== 1 ) { return; }

    $craft = make_current_editorial_craft();
    if ( '' === $craft ) { return; }

    $query->set(
        'tax_query',
        array(
            array(
                'taxonomy' => 'make_craft',
                'field' => 'slug',
                'terms' => array( $craft ),
            ),
        )
    );

    $section = make_current_editorial_craft_section();
    if ( '' !== $section ) {
        $config = make_editorial_section_config();
        if ( isset( $config[ $section ][ make_current_language() ]['slug'] ) ) {
            $query->set( 'category_name', (string) $config[ $section ][ make_current_language() ]['slug'] );
        }
    }
}
add_action( 'pre_get_posts', 'make_editorial_craft_main_query', 21 );

function make_editorial_breadcrumb_items( int $post_id = 0 ): array {
    $language = make_current_language();
    $items = array(
        array( 'label' => make_t( 'Inicio', 'Home' ), 'url' => make_home_url( $language ) ),
        array( 'label' => make_t( 'Artículos', 'Articles' ), 'url' => make_journal_url( $language ) ),
    );

    $craft = '';
    if ( $post_id > 0 ) {
        $craft = make_article_craft( $post_id );
    } elseif ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $craft = make_current_editorial_craft();
        if ( '' === $craft && function_exists( 'make_current_stitch_theme' ) && '' !== make_current_stitch_theme() ) {
            $craft = 'cross-stitch';
        }
    }

    if ( '' !== $craft && isset( make_editorial_craft_config()[ $craft ] ) ) {
        $cfg = make_editorial_craft_config()[ $craft ][ $language ];
        $items[] = array( 'label' => (string) $cfg['label'], 'url' => make_editorial_craft_url( $craft, $language ) );
    }

    if ( 0 === $post_id && '' !== $craft ) {
        $section = make_current_editorial_craft_section();
        $sections = make_editorial_section_config();
        if ( '' !== $section && isset( $sections[ $section ][ $language ]['label'] ) ) {
            $items[] = array( 'label' => (string) $sections[ $section ][ $language ]['label'], 'url' => '' );
        }
    }

    if ( $post_id > 0 ) {
        $items[] = array( 'label' => get_the_title( $post_id ), 'url' => '' );
    } elseif ( function_exists( 'make_current_stitch_theme' ) ) {
        $theme = make_current_stitch_theme();
        $themes = function_exists( 'make_stitch_theme_config' ) ? make_stitch_theme_config() : array();
        if ( '' !== $theme && isset( $themes[ $theme ][ $language ]['label'] ) ) {
            $items[] = array( 'label' => (string) $themes[ $theme ][ $language ]['label'], 'url' => '' );
        }
    }

    return $items;
}

function make_editorial_breadcrumbs_html( int $post_id = 0 ): string {
    $items = make_editorial_breadcrumb_items( $post_id );
    if ( count( $items ) < 2 ) { return ''; }

    $parts = array();
    foreach ( $items as $index => $item ) {
        $label = esc_html( (string) $item['label'] );
        if ( ! empty( $item['url'] ) && $index < count( $items ) - 1 ) {
            $parts[] = '<li><a href="' . esc_url( (string) $item['url'] ) . '">' . $label . '</a></li>';
        } else {
            $parts[] = '<li aria-current="page"><span>' . $label . '</span></li>';
        }
    }

    return '<nav class="editorial-breadcrumbs" aria-label="' . esc_attr( make_t( 'Migas de pan', 'Breadcrumbs' ) ) . '"><ol>' . implode( '', $parts ) . '</ol></nav>';
}

function make_editorial_breadcrumb_schema(): void {
    if ( ! is_singular( 'post' ) && (int) get_query_var( 'make_journal' ) !== 1 ) { return; }

    $post_id = is_singular( 'post' ) ? get_queried_object_id() : 0;
    $items = make_editorial_breadcrumb_items( $post_id );
    if ( count( $items ) < 2 ) { return; }

    $schema_items = array();
    foreach ( $items as $index => $item ) {
        $url = (string) ( $item['url'] ?? '' );
        if ( '' === $url ) {
            if ( $post_id > 0 ) {
                $url = get_permalink( $post_id );
            } else {
                $craft = make_current_editorial_craft();
                if ( '' !== $craft ) {
                    $section = make_current_editorial_craft_section();
                    $url = '' !== $section ? make_editorial_craft_section_url( $craft, $section ) : make_editorial_craft_url( $craft );
                } elseif ( function_exists( 'make_current_stitch_theme' ) && '' !== make_current_stitch_theme() ) {
                    $url = make_stitch_theme_url( make_current_stitch_theme() );
                } else {
                    $url = make_journal_url();
                }
            }
        }

        $schema_items[] = array(
            '@type' => 'ListItem',
            'position' => $index + 1,
            'name' => (string) $item['label'],
            'item' => $url,
        );
    }

    echo '<script type="application/ld+json">' . wp_json_encode(
        array(
            '@context' => 'https://schema.org',
            '@type' => 'BreadcrumbList',
            'itemListElement' => $schema_items,
        ),
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
    ) . '</script>' . "\n";
}
add_action( 'wp_head', 'make_editorial_breadcrumb_schema', 7 );

function make_article_commerce_config( int $post_id ): array {
    $value = get_post_meta( $post_id, '_make_commerce', true );
    return is_array( $value ) ? $value : array();
}

function make_article_product_technique_terms( string $craft ): array {
    $craft = sanitize_key( $craft );
    $map = array(
        'cross-stitch' => array( 'cross-stitch', 'cross-stitch-patterns', 'punto-de-cruz' ),
        'c2c-crochet' => array( 'c2c-crochet', 'c2c-crochet-patterns', 'corner-to-corner-crochet' ),
        'tapestry-crochet' => array( 'tapestry-crochet', 'tapestry-crochet-patterns' ),
        'latch-hook' => array( 'latch-hook', 'latch-hook-patterns' ),
    );
    $candidate_slugs = $map[ $craft ] ?? array( $craft );
    $terms = array();

    if ( ! post_type_exists( 'product' ) ) { return $terms; }

    foreach ( get_object_taxonomies( 'product', 'names' ) as $taxonomy ) {
        if ( 'product_collection' === $taxonomy || ! taxonomy_exists( $taxonomy ) ) { continue; }
        foreach ( $candidate_slugs as $slug ) {
            $term = get_term_by( 'slug', $slug, $taxonomy );
            if ( $term instanceof WP_Term ) {
                $terms[ $taxonomy . ':' . $term->term_id ] = $term;
            }
        }
    }

    return array_values( $terms );
}

function make_article_product_tax_query( string $craft ): array {
    $terms = make_article_product_technique_terms( $craft );
    if ( empty( $terms ) ) { return array(); }

    $tax_query = array( 'relation' => 'OR' );
    foreach ( $terms as $term ) {
        if ( ! $term instanceof WP_Term ) { continue; }
        $tax_query[] = array(
            'taxonomy' => $term->taxonomy,
            'field' => 'term_id',
            'terms' => array( (int) $term->term_id ),
        );
    }

    return count( $tax_query ) > 1 ? $tax_query : array();
}

function make_article_shop_product_ids( int $post_id, int $limit = 4 ): array {
    if ( ! class_exists( 'WooCommerce' ) ) { return array(); }

    $limit = max( 1, $limit );
    $commerce = make_article_commerce_config( $post_id );
    $ids = array();

    foreach ( (array) ( $commerce['product_skus'] ?? array() ) as $sku ) {
        $product_id = function_exists( 'wc_get_product_id_by_sku' ) ? (int) wc_get_product_id_by_sku( sanitize_text_field( (string) $sku ) ) : 0;
        if ( $product_id > 0 && 'publish' === get_post_status( $product_id ) ) { $ids[] = $product_id; }
        if ( count( $ids ) >= $limit ) { return array_slice( array_values( array_unique( $ids ) ), 0, $limit ); }
    }

    $craft = make_article_craft( $post_id );
    $tax_query = make_article_product_tax_query( $craft );
    if ( empty( $tax_query ) ) { return array_slice( array_values( array_unique( $ids ) ), 0, $limit ); }

    $query = new WP_Query(
        array(
            'post_type' => 'product',
            'post_status' => 'publish',
            'posts_per_page' => $limit,
            'fields' => 'ids',
            'post__not_in' => $ids,
            'no_found_rows' => true,
            'orderby' => array( 'menu_order' => 'ASC', 'date' => 'DESC' ),
            'tax_query' => $tax_query,
        )
    );

    $ids = array_merge( $ids, array_map( 'intval', $query->posts ) );
    return array_slice( array_values( array_unique( $ids ) ), 0, $limit );
}

function make_article_collection_terms( int $post_id, int $limit = 4 ): array {
    if ( ! taxonomy_exists( 'product_collection' ) ) { return array(); }

    $limit = max( 1, $limit );
    $commerce = make_article_commerce_config( $post_id );
    $terms = array();

    foreach ( (array) ( $commerce['collection_slugs'] ?? array() ) as $slug ) {
        $term = get_term_by( 'slug', sanitize_title( (string) $slug ), 'product_collection' );
        if ( $term instanceof WP_Term && (int) $term->count > 0 ) { $terms[ $term->term_id ] = $term; }
        if ( count( $terms ) >= $limit ) { return array_values( $terms ); }
    }

    foreach ( make_article_shop_product_ids( $post_id, 12 ) as $product_id ) {
        $product_terms = wp_get_post_terms( $product_id, 'product_collection' );
        if ( is_wp_error( $product_terms ) ) { continue; }
        foreach ( $product_terms as $term ) {
            if ( $term instanceof WP_Term && (int) $term->count > 0 ) { $terms[ $term->term_id ] = $term; }
            if ( count( $terms ) >= $limit ) { break 2; }
        }
    }

    return array_values( $terms );
}

function make_article_shop_url( int $post_id ): string {
    $language = make_current_language();
    $commerce = make_article_commerce_config( $post_id );

    if ( taxonomy_exists( 'product_collection' ) && function_exists( 'make_store_term_url' ) ) {
        foreach ( (array) ( $commerce['collection_slugs'] ?? array() ) as $slug ) {
            $term = get_term_by( 'slug', sanitize_title( (string) $slug ), 'product_collection' );
            if ( $term instanceof WP_Term && (int) $term->count > 0 ) {
                return make_store_term_url( $term, $language );
            }
        }
    }

    foreach ( make_article_product_technique_terms( make_article_craft( $post_id ) ) as $term ) {
        if ( ! $term instanceof WP_Term ) { continue; }
        if ( 'product_cat' === $term->taxonomy && function_exists( 'make_store_term_url' ) ) {
            return make_store_term_url( $term, $language );
        }
        $taxonomy = get_taxonomy( $term->taxonomy );
        if ( $taxonomy && ! empty( $taxonomy->public ) ) {
            $url = get_term_link( $term );
            if ( ! is_wp_error( $url ) ) { return $url; }
        }
    }

    return make_shop_url( $language );
}

function make_article_product_name( int $product_id ): string {
    if ( 'es' === make_current_language() ) {
        $localized = trim( (string) get_post_meta( $product_id, '_drielo_title_es', true ) );
        if ( '' !== $localized ) { return $localized; }
    }
    return get_the_title( $product_id );
}

function make_article_commerce_products_html( int $post_id ): string {
    $ids = make_article_shop_product_ids( $post_id, 4 );
    if ( empty( $ids ) ) { return ''; }

    $craft = make_article_craft( $post_id );
    $config = make_editorial_craft_config();
    $craft_label = $config[ $craft ][ make_current_language() ]['label'] ?? '';

    $cards = array();
    foreach ( $ids as $product_id ) {
        $product = function_exists( 'wc_get_product' ) ? wc_get_product( $product_id ) : null;
        if ( ! $product instanceof WC_Product ) { continue; }

        $image = '';
        $image_id = $product->get_image_id();
        if ( $image_id && function_exists( 'make_static_attachment_image_html' ) ) {
            $image = make_static_attachment_image_html( $image_id, 'make-store-card', 'article-commerce-product-image' );
        }

        $cards[] = '<a class="article-commerce-product" href="' . esc_url( make_product_url( $product_id, make_current_language() ) ) . '">'
            . '<span class="article-commerce-product-media">' . $image . '</span>'
            . '<span class="article-commerce-product-copy"><strong>' . esc_html( make_article_product_name( $product_id ) ) . '</strong>'
            . '<small>' . wp_kses_post( $product->get_price_html() ) . '</small></span></a>';
    }

    if ( empty( $cards ) ) { return ''; }

    return '<aside class="article-commerce-inline" aria-label="' . esc_attr( make_t( 'Patrones relacionados', 'Related patterns' ) ) . '">'
        . '<div class="article-commerce-inline-head"><span class="section-kicker">' . esc_html( make_t( 'Patrones para esta técnica', 'Patterns for this technique' ) ) . '</span>'
        . '<h3>' . esc_html( sprintf( make_t( 'Pon en práctica lo aprendido con %s', 'Put it into practice with %s' ), $craft_label ) ) . '</h3></div>'
        . '<div class="article-commerce-products">' . implode( '', $cards ) . '</div>'
        . '<a class="article-commerce-link" href="' . esc_url( make_article_shop_url( $post_id ) ) . '">' . esc_html( make_t( 'Ver patrones', 'View patterns' ) ) . ' →</a>'
        . '</aside>';
}

function make_article_commerce_collections_html( int $post_id ): string {
    $terms = make_article_collection_terms( $post_id, 4 );
    if ( empty( $terms ) ) { return ''; }

    $craft = make_article_craft( $post_id );
    $config = make_editorial_craft_config();
    $craft_label = $config[ $craft ][ make_current_language() ]['label'] ?? '';

    $cards = array();
    foreach ( $terms as $term ) {
        if ( ! $term instanceof WP_Term ) { continue; }

        $label = $term->name;
        if ( 'es' === make_current_language() ) {
            $localized = trim( (string) get_term_meta( $term->term_id, 'drielo_name_es', true ) );
            if ( '' !== $localized ) { $label = $localized; }
        }

        $url = function_exists( 'make_store_term_url' ) ? make_store_term_url( $term, make_current_language() ) : get_term_link( $term );
        if ( is_wp_error( $url ) ) { continue; }

        $cards[] = '<a class="article-collection-card" href="' . esc_url( $url ) . '"><span>'
            . '<strong>' . esc_html( $label ) . '</strong>'
            . '<small>' . esc_html( sprintf( make_t( '%d patrones', '%d patterns' ), (int) $term->count ) ) . '</small>'
            . '</span><i aria-hidden="true">→</i></a>';
    }

    if ( empty( $cards ) ) { return ''; }

    return '<section class="article-commerce-collections narrow" aria-labelledby="article-commerce-collections-title">'
        . '<header><span class="section-kicker">' . esc_html( make_t( 'De la guía al proyecto', 'From guide to project' ) ) . '</span>'
        . '<h2 id="article-commerce-collections-title">' . esc_html( sprintf( make_t( 'Explora colecciones de %s', 'Explore %s collections' ), $craft_label ) ) . '</h2>'
        . '<p>' . esc_html( make_t( 'Diseños relacionados para seguir creando sin salir de esta técnica.', 'Related designs so you can keep making with the same technique.' ) ) . '</p></header>'
        . '<div class="article-collection-grid">' . implode( '', $cards ) . '</div>'
        . '</section>';
}

function make_article_insert_commerce( string $content ): string {
    if ( is_admin() || ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) { return $content; }

    $module = make_article_commerce_products_html( get_the_ID() );
    if ( '' === $module ) { return $content; }

    $offset = 0;
    $insert_at = false;
    for ( $i = 0; $i < 5; $i++ ) {
        $position = stripos( $content, '</p>', $offset );
        if ( false === $position ) { break; }
        $insert_at = $position + 4;
        $offset = $insert_at;
    }

    if ( false === $insert_at ) { return $content . $module; }
    return substr( $content, 0, $insert_at ) . $module . substr( $content, $insert_at );
}
add_filter( 'the_content', 'make_article_insert_commerce', 12 );

function make_editorial_craft_robots( array $robots ): array {
    if ( (int) get_query_var( 'make_journal' ) === 1 ) {
        $craft = make_current_editorial_craft();
        if ( '' !== $craft && ! make_editorial_craft_has_content( $craft, make_current_language() ) ) {
            $robots['noindex'] = true;
            $robots['follow'] = true;
        } elseif ( '' !== $craft ) {
            unset( $robots['noindex'] );
            $robots['follow'] = true;
        }
    }
    return $robots;
}
add_filter( 'wp_robots', 'make_editorial_craft_robots', 25 );
