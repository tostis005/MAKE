<?php
/**
 * Idempotent JSON -> WordPress importer for MAKE editorial articles.
 *
 * Usage:
 * php import-articles.php <wp-root> <articles-root>
 *   [--language=es|en|all] [--from=1] [--to=999999]
 *   [--status=publish|draft|review|json] [--force=0|1]
 */
if ( PHP_SAPI !== 'cli' ) { fwrite( STDERR, "CLI only.\n" ); exit( 1 ); }
if ( $argc < 3 ) { fwrite( STDERR, "Usage: php import-articles.php <wp-root> <articles-root> [options]\n" ); exit( 1 ); }

$wp_root = rtrim( $argv[1], '/' );
$articles_root = rtrim( $argv[2], '/' );
$options = array( 'language'=>'all', 'from'=>1, 'to'=>PHP_INT_MAX, 'status'=>'json', 'force'=>'0' );

foreach ( array_slice( $argv, 3 ) as $arg ) {
    if ( 0 !== strpos( $arg, '--' ) || false === strpos( $arg, '=' ) ) { continue; }
    list( $key, $value ) = explode( '=', substr( $arg, 2 ), 2 );
    $key = str_replace( '-', '_', $key );
    if ( array_key_exists( $key, $options ) ) { $options[ $key ] = $value; }
}
$options['from'] = max( 1, (int) $options['from'] );
$options['to'] = max( $options['from'], (int) $options['to'] );
$options['force'] = in_array( strtolower( (string) $options['force'] ), array( '1','true','yes','on' ), true );

if ( ! in_array( $options['language'], array( 'es','en','all' ), true ) ) { throw new RuntimeException( 'Invalid language option.' ); }
if ( ! in_array( $options['status'], array( 'publish','draft','review','json' ), true ) ) { throw new RuntimeException( 'Invalid status option.' ); }

$wp_load = $wp_root . '/wp-load.php';
if ( ! is_readable( $wp_load ) ) { fwrite( STDERR, "Cannot read {$wp_load}\n" ); exit( 1 ); }
if ( ! is_dir( $articles_root ) ) { fwrite( STDERR, "Articles directory not found: {$articles_root}\n" ); exit( 1 ); }
require_once $wp_load;

function make_import_required_string( $data, $key, $file ) {
    if ( ! isset( $data[$key] ) || ! is_string( $data[$key] ) || '' === trim( $data[$key] ) ) {
        throw new RuntimeException( "Missing or invalid {$key} in {$file}" );
    }
    return trim( $data[$key] );
}
function make_import_status( $json, $override ) {
    if ( 'json' !== $override ) { return 'review' === $override ? 'draft' : $override; }
    return 'publish' === $json ? 'publish' : 'draft';
}
function make_import_find_existing( $source_id, $slug, $language ) {
    $ids = get_posts( array(
        'post_type'=>'post', 'post_status'=>'any', 'posts_per_page'=>1, 'fields'=>'ids',
        'meta_key'=>'_make_source_id', 'meta_value'=>$source_id,
    ) );
    if ( ! empty( $ids ) ) { return get_post( (int) $ids[0] ); }

    $ids = get_posts( array(
        'post_type'=>'post', 'post_status'=>'any', 'posts_per_page'=>1, 'fields'=>'ids', 'name'=>$slug,
        'meta_query'=>array( array( 'key'=>'_make_language', 'value'=>$language ) ),
    ) );
    return ! empty( $ids ) ? get_post( (int) $ids[0] ) : null;
}
function make_import_section_definitions() {
    return array(
        'learn'=>array(
            'es'=>array('name'=>'Aprender','slug'=>'aprender'),
            'en'=>array('name'=>'Learn','slug'=>'learn'),
        ),
        'ideas'=>array(
            'es'=>array('name'=>'Ideas e inspiración','slug'=>'ideas'),
            'en'=>array('name'=>'Ideas & inspiration','slug'=>'inspiration'),
        ),
        'buying-guides'=>array(
            'es'=>array('name'=>'Guías de compra','slug'=>'guias-de-compra'),
            'en'=>array('name'=>'Buying guides','slug'=>'buying-guides'),
        ),
    );
}
function make_import_ensure_sections() {
    $result = array();
    foreach ( make_import_section_definitions() as $id=>$localized ) {
        foreach ( array('es','en') as $language ) {
            $cfg = $localized[$language];
            $term = get_category_by_slug( $cfg['slug'] );
            if ( ! $term instanceof WP_Term ) {
                $created = wp_insert_term( $cfg['name'], 'category', array( 'slug'=>$cfg['slug'] ) );
                if ( is_wp_error( $created ) ) { throw new RuntimeException( $created->get_error_message() ); }
                $term = get_term( (int) $created['term_id'], 'category' );
            }
            if ( ! $term instanceof WP_Term ) { throw new RuntimeException( "Could not resolve category {$cfg['slug']}" ); }
            $result[$id][$language] = (int) $term->term_id;
            update_term_meta( $term->term_id, '_make_section_id', $id );
            update_term_meta( $term->term_id, '_make_language', $language );
            if ( function_exists( 'pll_set_term_language' ) ) { pll_set_term_language( $term->term_id, $language ); }
        }
        if ( function_exists( 'pll_save_term_translations' ) ) {
            pll_save_term_translations( array(
                'es'=>$result[$id]['es'],
                'en'=>$result[$id]['en'],
            ) );
        }
    }
    return $result;
}
function make_import_dimension_terms( $taxonomy, $key ) {
    if ( empty( $taxonomy[$key] ) || ! is_array( $taxonomy[$key] ) ) { return array(); }
    $terms = array();
    if ( ! empty( $taxonomy[$key]['terms'] ) && is_array( $taxonomy[$key]['terms'] ) ) {
        $terms = $taxonomy[$key]['terms'];
    } elseif ( ! empty( $taxonomy[$key]['primary'] ) && is_string( $taxonomy[$key]['primary'] ) ) {
        $terms = array( $taxonomy[$key]['primary'] );
    }
    return array_values( array_unique( array_filter( array_map( 'sanitize_title', $terms ) ) ) );
}
function make_import_sync_dimensions( $post_id, $taxonomy ) {
    $map = array(
        'craft'        => 'make_craft',
        'topic'        => 'make_topic',
        'style'        => 'make_style',
        'skill'        => 'make_skill',
        'project_type' => 'make_project_type',
        'article_type' => 'make_article_type',
    );

    if ( empty( $taxonomy['craft'] ) ) {
        $taxonomy['craft'] = array( 'primary'=>'cross-stitch', 'terms'=>array('cross-stitch') );
    }

    foreach ( $map as $key=>$wp_taxonomy ) {
        if ( ! taxonomy_exists( $wp_taxonomy ) ) { continue; }
        $terms = make_import_dimension_terms( $taxonomy, $key );
        if ( empty( $terms ) ) {
            wp_set_object_terms( $post_id, array(), $wp_taxonomy, false );
            continue;
        }

        foreach ( $terms as $slug ) {
            if ( ! term_exists( $slug, $wp_taxonomy ) ) {
                $name = ucwords( str_replace( '-', ' ', $slug ) );
                $created = wp_insert_term( $name, $wp_taxonomy, array( 'slug'=>$slug ) );
                if ( is_wp_error( $created ) && 'term_exists' !== $created->get_error_code() ) {
                    throw new RuntimeException( $created->get_error_message() );
                }
            }
        }
        wp_set_object_terms( $post_id, $terms, $wp_taxonomy, false );
    }
}
function make_import_primary_section( $taxonomy ) {
    if ( isset( $taxonomy['section']['primary'] ) && is_string( $taxonomy['section']['primary'] ) ) {
        return $taxonomy['section']['primary'];
    }
    return 'learn';
}
function make_import_save_seo_meta( $post_id, $seo ) {
    $title = isset( $seo['title'] ) ? (string) $seo['title'] : '';
    $desc = isset( $seo['meta_description'] ) ? (string) $seo['meta_description'] : '';
    $intent = isset( $seo['search_intent'] ) ? (string) $seo['search_intent'] : '';
    update_post_meta( $post_id, '_make_seo_title', $title );
    update_post_meta( $post_id, '_make_meta_description', $desc );
    update_post_meta( $post_id, '_make_search_intent', $intent );
    if ( defined( 'WPSEO_VERSION' ) ) {
        update_post_meta( $post_id, '_yoast_wpseo_title', $title );
        update_post_meta( $post_id, '_yoast_wpseo_metadesc', $desc );
    }
    if ( defined( 'RANK_MATH_VERSION' ) ) {
        update_post_meta( $post_id, 'rank_math_title', $title );
        update_post_meta( $post_id, 'rank_math_description', $desc );
    }
}
function make_import_author_id() {
    $ids = get_users( array( 'role'=>'administrator', 'number'=>1, 'fields'=>'ID' ) );
    return $ids ? (int) $ids[0] : 1;
}
function make_import_apply_language( $post_id, $language, $group ) {
    update_post_meta( $post_id, '_make_language', $language );
    update_post_meta( $post_id, '_make_translation_group', $group );
    if ( function_exists( 'pll_set_post_language' ) ) { pll_set_post_language( $post_id, $language ); }
}
function make_import_link_translations( $groups ) {
    if ( ! function_exists( 'pll_save_post_translations' ) ) { return; }
    foreach ( array_unique( $groups ) as $group ) {
        $posts = get_posts( array(
            'post_type'=>'post', 'post_status'=>'any', 'posts_per_page'=>-1,
            'meta_key'=>'_make_translation_group', 'meta_value'=>$group,
        ) );
        $translations = array();
        foreach ( $posts as $post ) {
            $language = (string) get_post_meta( $post->ID, '_make_language', true );
            if ( in_array( $language, array('es','en'), true ) ) { $translations[$language] = (int) $post->ID; }
        }
        if ( count( $translations ) > 1 ) { pll_save_post_translations( $translations ); }
    }
}

$sections = make_import_ensure_sections();
$languages = 'all' === $options['language'] ? array('es','en') : array($options['language']);
$files = array();
foreach ( $languages as $language ) {
    $dir = $articles_root . '/' . $language;
    if ( is_dir( $dir ) ) {
        foreach ( glob( $dir . '/*.json' ) ?: array() as $file ) { $files[] = $file; }
    }
}
sort( $files, SORT_NATURAL );

$created=0; $updated=0; $skipped=0; $failed=0; $groups=array(); $author=make_import_author_id();

foreach ( $files as $file ) {
    try {
        $raw = file_get_contents( $file );
        if ( false === $raw ) { throw new RuntimeException( 'Could not read JSON.' ); }
        $data = json_decode( $raw, true, 512, JSON_THROW_ON_ERROR );
        if ( ! is_array( $data ) ) { throw new RuntimeException( 'JSON root must be an object.' ); }

        $number = isset( $data['article_number'] ) ? (int) $data['article_number'] : 0;
        if ( $number < $options['from'] || $number > $options['to'] ) { continue; }

        $source_id = make_import_required_string( $data, 'id', $file );
        $group = make_import_required_string( $data, 'translation_group', $file );
        $language = make_import_required_string( $data, 'language', $file );
        $title = make_import_required_string( $data, 'title', $file );
        $slug = make_import_required_string( $data, 'slug', $file );
        $excerpt = make_import_required_string( $data, 'excerpt', $file );
        $content_html = make_import_required_string( $data, 'content_html', $file );

        if ( ! in_array( $language, array('es','en'), true ) ) { throw new RuntimeException( 'Invalid language in JSON.' ); }

        $seo = ! empty( $data['seo'] ) && is_array( $data['seo'] ) ? $data['seo'] : array();
        $taxonomy = ! empty( $data['taxonomy'] ) && is_array( $data['taxonomy'] ) ? $data['taxonomy'] : array();
        $faq = ! empty( $data['faq'] ) && is_array( $data['faq'] ) ? $data['faq'] : array();
        $sources = ! empty( $data['sources'] ) && is_array( $data['sources'] ) ? $data['sources'] : array();
        $image = ! empty( $data['image'] ) && is_array( $data['image'] ) ? $data['image'] : array();
        $json_status = isset( $data['status'] ) ? (string) $data['status'] : 'draft';

        $hash = hash( 'sha256', $raw );
        $existing = make_import_find_existing( $source_id, $slug, $language );
        if ( $existing instanceof WP_Post && ! $options['force'] && hash_equals( $hash, (string) get_post_meta( $existing->ID, '_make_source_hash', true ) ) ) {
            make_import_sync_dimensions( (int) $existing->ID, $taxonomy );
            $groups[]=$group; ++$skipped; echo "SKIP {$language} #{$number} {$slug}\n"; continue;
        }

        $postarr = array(
            'post_type'=>'post',
            'post_title'=>$title,
            'post_name'=>$slug,
            'post_excerpt'=>$excerpt,
            'post_content'=>$content_html,
            'post_status'=>make_import_status( $json_status, $options['status'] ),
            'post_author'=>$author,
        );

        if ( $existing instanceof WP_Post ) {
            $postarr['ID']=(int)$existing->ID;
            $result=wp_update_post( wp_slash( $postarr ), true );
            ++$updated; $verb='UPDATE';
        } else {
            $result=wp_insert_post( wp_slash( $postarr ), true );
            ++$created; $verb='CREATE';
        }
        if ( is_wp_error( $result ) ) { throw new RuntimeException( $result->get_error_message() ); }

        $post_id=(int)$result;
        $section = make_import_primary_section( $taxonomy );
        if ( ! isset( $sections[$section][$language] ) ) { throw new RuntimeException( "Unknown section {$section}" ); }
        wp_set_post_categories( $post_id, array( $sections[$section][$language] ), false );
        make_import_sync_dimensions( $post_id, $taxonomy );

        update_post_meta( $post_id, '_make_source_id', $source_id );
        update_post_meta( $post_id, '_make_source_hash', $hash );
        update_post_meta( $post_id, '_make_article_number', $number );
        update_post_meta( $post_id, '_make_locale', isset($data['locale'])?(string)$data['locale']:'' );
        update_post_meta( $post_id, '_make_market_context', isset($data['market_context'])?(string)$data['market_context']:'' );
        update_post_meta( $post_id, '_make_taxonomy', $taxonomy );
        update_post_meta( $post_id, '_make_faq', $faq );
        update_post_meta( $post_id, '_make_sources', $sources );
        update_post_meta( $post_id, '_make_image_concept', isset($image['concept'])?(string)$image['concept']:'' );
        update_post_meta( $post_id, '_make_image_alt', isset($image['alt'])?(string)$image['alt']:'' );
        update_post_meta( $post_id, '_make_managed_article', 1 );

        make_import_apply_language( $post_id, $language, $group );
        make_import_save_seo_meta( $post_id, $seo );
        $groups[]=$group;

        echo "{$verb} {$language} #{$number} post_id={$post_id} {$slug}\n";
    } catch ( Throwable $e ) {
        ++$failed;
        fwrite( STDERR, 'FAIL ' . basename( $file ) . ': ' . $e->getMessage() . "\n" );
    }
}

make_import_link_translations( $groups );
echo "SUMMARY created={$created} updated={$updated} skipped={$skipped} failed={$failed}\n";
exit( 0 === $failed ? 0 : 1 );
