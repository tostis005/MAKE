<?php
/**
 * Import Drielo WooCommerce products from content/products/catalog.json.
 *
 * Usage:
 * php import-products.php /var/www/html /tmp/drielo-products
 */
if ( PHP_SAPI !== 'cli' ) { fwrite( STDERR, "CLI only\n" ); exit(2); }

$wp_root = $argv[1] ?? '';
$source  = $argv[2] ?? '';
if ( ! $wp_root || ! $source ) { fwrite( STDERR, "Usage: import-products.php WP_ROOT SOURCE_DIR\n" ); exit(2); }

$wp_load = rtrim( $wp_root, '/' ) . '/wp-load.php';
if ( ! is_file( $wp_load ) ) { fwrite( STDERR, "wp-load.php not found\n" ); exit(2); }
require $wp_load;

if ( ! class_exists( 'WooCommerce' ) || ! class_exists( 'WC_Product_Simple' ) ) {
    fwrite( STDERR, "WooCommerce is not active\n" );
    exit(3);
}

require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/media.php';

$catalog_path = rtrim( $source, '/' ) . '/catalog.json';
if ( ! is_file( $catalog_path ) ) { fwrite( STDERR, "catalog.json not found\n" ); exit(2); }
$catalog = json_decode( (string) file_get_contents( $catalog_path ), true );
if ( ! is_array( $catalog ) ) { fwrite( STDERR, "Invalid catalog.json\n" ); exit(2); }

function drielo_term( string $taxonomy, string $name, string $slug, int $parent = 0 ): int {
    $existing = get_term_by( 'slug', $slug, $taxonomy );
    if ( $existing instanceof WP_Term ) {
        if ( $name !== $existing->name || $parent !== (int) $existing->parent ) {
            wp_update_term( $existing->term_id, $taxonomy, array( 'name' => $name, 'parent' => $parent ) );
        }
        return (int) $existing->term_id;
    }

    $created = wp_insert_term( $name, $taxonomy, array( 'slug' => $slug, 'parent' => $parent ) );
    if ( is_wp_error( $created ) ) { throw new RuntimeException( $created->get_error_message() ); }
    return (int) $created['term_id'];
}

function drielo_media_from_file( string $path, string $source_key, string $title, string $source_revision = '' ): int {
    if ( ! is_file( $path ) ) { return 0; }

    $source_hash = md5_file( $path ) ?: '';
    $existing = get_posts(
        array(
            'post_type'      => 'attachment',
            'post_status'    => 'inherit',
            'posts_per_page' => 1,
            'fields'         => 'ids',
            'meta_key'       => '_drielo_source_asset',
            'meta_value'     => $source_key,
        )
    );

    if ( $existing ) {
        $attachment_id = (int) $existing[0];
        $known_revision = (string) get_post_meta( $attachment_id, '_drielo_source_revision', true );
        $known_hash = (string) get_post_meta( $attachment_id, '_drielo_source_hash', true );
        if ( '' !== $source_revision && hash_equals( $known_revision, $source_revision ) && $source_hash && hash_equals( $known_hash, $source_hash ) ) {
            return $attachment_id;
        }
        if ( '' === $source_revision && $source_hash && hash_equals( $known_hash, $source_hash ) ) {
            return $attachment_id;
        }

        // Do not overwrite an attachment at the same public URL: browsers/CDNs
        // may keep serving the previous bytes. Remove the stale attachment and
        // create a revisioned one so every changed product image gets a new URL.
        wp_delete_attachment( $attachment_id, true );
    }

    $filename = wp_basename( $path );
    if ( '' !== $source_revision ) {
        $info = pathinfo( $filename );
        $stem = sanitize_file_name( (string) ( $info['filename'] ?? $filename ) );
        $ext  = isset( $info['extension'] ) ? '.' . sanitize_file_name( (string) $info['extension'] ) : '';
        $rev  = sanitize_file_name( $source_revision );
        $filename = $stem . '-r' . $rev . $ext;
    }
    $bits = wp_upload_bits( $filename, null, (string) file_get_contents( $path ) );
    if ( ! empty( $bits['error'] ) ) { throw new RuntimeException( (string) $bits['error'] ); }

    $type = wp_check_filetype( $filename, null );
    $attachment_id = wp_insert_attachment(
        array(
            'post_mime_type' => $type['type'] ?: 'image/webp',
            'post_title'     => $title,
            'post_status'    => 'inherit',
        ),
        $bits['file']
    );
    if ( is_wp_error( $attachment_id ) ) { throw new RuntimeException( $attachment_id->get_error_message() ); }

    $metadata = wp_generate_attachment_metadata( $attachment_id, $bits['file'] );
    if ( is_array( $metadata ) ) { wp_update_attachment_metadata( $attachment_id, $metadata ); }
    update_post_meta( $attachment_id, '_drielo_source_asset', $source_key );
    update_post_meta( $attachment_id, '_drielo_source_hash', $source_hash );
    if ( '' !== $source_revision ) { update_post_meta( $attachment_id, '_drielo_source_revision', $source_revision ); }
    return (int) $attachment_id;
}

function drielo_install_download( string $source_path, string $filename, string $source_revision = '' ): array {
    if ( ! is_file( $source_path ) || filesize( $source_path ) < 1000 ) { return array(); }

    $uploads = wp_upload_dir();
    if ( ! empty( $uploads['error'] ) ) { throw new RuntimeException( (string) $uploads['error'] ); }

    $relative = 'woocommerce_uploads/drielo';
    $dir = trailingslashit( $uploads['basedir'] ) . $relative;
    if ( ! wp_mkdir_p( $dir ) ) { throw new RuntimeException( 'Could not create protected downloads directory' ); }

    $stored_filename = $filename;
    if ( '' !== $source_revision ) {
        $info = pathinfo( $filename );
        $stem = sanitize_file_name( (string) ( $info['filename'] ?? $filename ) );
        $ext  = isset( $info['extension'] ) ? '.' . sanitize_file_name( (string) $info['extension'] ) : '';
        $rev  = sanitize_file_name( $source_revision );
        $stored_filename = $stem . '-r' . $rev . $ext;
    }

    $destination = trailingslashit( $dir ) . $stored_filename;
    if ( ! copy( $source_path, $destination ) ) { throw new RuntimeException( 'Could not copy downloadable PDF' ); }
    @chmod( $destination, 0644 );

    $deny = trailingslashit( dirname( $dir ) ) . '.htaccess';
    if ( ! is_file( $deny ) ) {
        @file_put_contents( $deny, "deny from all\n" );
    }

    $url = trailingslashit( $uploads['baseurl'] ) . $relative . '/' . rawurlencode( $stored_filename );
    $download = new WC_Product_Download();
    $download->set_id( md5( $destination ) );
    $download->set_name( $filename );
    $download->set_file( $url );
    return array( $download );
}

$category_ids = array();
foreach ( (array) ( $catalog['categories'] ?? array() ) as $cat ) {
    $slug = sanitize_title( (string) $cat['slug'] );
    $parent_slug = isset( $cat['parent'] ) ? sanitize_title( (string) $cat['parent'] ) : '';
    $parent = $parent_slug && isset( $category_ids[ $parent_slug ] ) ? (int) $category_ids[ $parent_slug ] : 0;
    $term_id = drielo_term( 'product_cat', (string) $cat['name'], $slug, $parent );
    $category_ids[ $slug ] = $term_id;
    update_term_meta( $term_id, 'drielo_name_es', sanitize_text_field( (string) ( $cat['name_es'] ?? $cat['name'] ) ) );
    update_term_meta( $term_id, 'drielo_name_en', sanitize_text_field( (string) ( $cat['name_en'] ?? $cat['name'] ) ) );
}

$collections = array();
$legacy_collection_terms = array();
foreach ( (array) ( $catalog['collections'] ?? array() ) as $collection ) {
    $slug = sanitize_title( (string) $collection['slug'] );
    $name = (string) $collection['name'];

    $term = get_term_by( 'slug', $slug, 'product_collection' );
    if ( ! $term instanceof WP_Term ) {
        foreach ( (array) ( $collection['previous_slugs'] ?? array() ) as $previous_slug ) {
            $previous = get_term_by( 'slug', sanitize_title( (string) $previous_slug ), 'product_collection' );
            if ( $previous instanceof WP_Term ) {
                $updated_term = wp_update_term(
                    $previous->term_id,
                    'product_collection',
                    array( 'name' => $name, 'slug' => $slug )
                );
                if ( is_wp_error( $updated_term ) ) { throw new RuntimeException( $updated_term->get_error_message() ); }
                $term = get_term( $previous->term_id, 'product_collection' );
                break;
            }
        }
    }

    $term_id = $term instanceof WP_Term ? (int) $term->term_id : drielo_term( 'product_collection', $name, $slug );
    wp_update_term( $term_id, 'product_collection', array( 'name' => $name, 'slug' => $slug, 'description' => (string) ( $collection['description'] ?? '' ) ) );

    update_term_meta( $term_id, 'drielo_name_es', sanitize_text_field( (string) ( $collection['name_es'] ?? '' ) ) );
    update_term_meta( $term_id, 'drielo_name_en', sanitize_text_field( (string) ( $collection['name_en'] ?? $name ) ) );
    update_term_meta( $term_id, 'drielo_description_es', sanitize_text_field( (string) ( $collection['description_es'] ?? '' ) ) );
    update_term_meta( $term_id, 'drielo_description_en', sanitize_text_field( (string) ( $collection['description_en'] ?? ( $collection['description'] ?? '' ) ) ) );
    update_term_meta( $term_id, 'drielo_palette_hex', implode( ', ', (array) ( $collection['palette_hex'] ?? array() ) ) );
    update_term_meta( $term_id, 'drielo_thread_codes', 'DMC ' . implode( ', ', (array) ( $collection['thread_codes'] ?? array() ) ) );

    foreach ( (array) ( $collection['previous_slugs'] ?? array() ) as $previous_slug ) {
        $legacy = get_term_by( 'slug', sanitize_title( (string) $previous_slug ), 'product_collection' );
        if ( $legacy instanceof WP_Term && (int) $legacy->term_id !== $term_id ) {
            $legacy_collection_terms[] = (int) $legacy->term_id;
        }
    }

    $cover = (string) ( $collection['cover_asset'] ?? '' );
    if ( $cover ) {
        $cover_id = drielo_media_from_file(
            rtrim( $source, '/' ) . '/' . $cover,
            $cover,
            (string) $collection['name'] . ' collection'
        );
        if ( $cover_id ) { update_term_meta( $term_id, 'drielo_collection_cover_id', $cover_id ); }
    }

    $collections[ $slug ] = $term_id;
}

$drielo_filter_term_names = array(
    'technique' => array('cross-stitch'=>'Cross Stitch','c2c-crochet'=>'C2C Crochet','tapestry-crochet'=>'Tapestry Crochet','latch-hook'=>'Latch Hook'),
    'theme' => array('people-portraits'=>'People & Portraits','animals'=>'Animals','flowers-botanicals'=>'Flowers & Botanicals','nature-landscapes'=>'Nature & Landscapes','architecture-places'=>'Architecture & Places','fantasy-surreal'=>'Fantasy & Surreal','kids'=>'Kids','food-drink'=>'Food & Drink','abstract-geometric'=>'Abstract & Geometric','holidays-seasons'=>'Holidays & Seasons'),
    'style' => array('pop-art'=>'Pop Art','classic-art'=>'Classic Art','modern'=>'Modern','vintage'=>'Vintage','playful'=>'Playful','elegant'=>'Elegant','surreal'=>'Surreal','colorful'=>'Colorful','minimalist'=>'Minimalist','cute'=>'Cute','dark-gothic'=>'Dark & Gothic','fantasy'=>'Fantasy'),
    'project' => array('wall-art'=>'Wall Art','blanket'=>'Blanket','rug'=>'Rug','tapestry'=>'Tapestry','cushion'=>'Cushion'),
    'orientation' => array('square'=>'Square','portrait'=>'Portrait','landscape'=>'Landscape'),
    'season' => array('christmas'=>'Christmas','halloween'=>'Halloween','valentines-day'=>"Valentine's Day",'spring'=>'Spring','summer'=>'Summer','autumn'=>'Autumn','winter'=>'Winter'),
    'difficulty' => array('beginner'=>'Beginner','intermediate'=>'Intermediate','advanced'=>'Advanced'),
    'color-family' => array('neutral'=>'Neutral','warm'=>'Warm','cool'=>'Cool','green'=>'Green','blue'=>'Blue','pink'=>'Pink','multicolor'=>'Multicolor','dark'=>'Dark'),
);

$retired_product_skus = array_values( array_unique( array_filter( array_map( 'sanitize_text_field', (array) ( $catalog['retired_products'] ?? array() ) ) ) ) );
foreach ( $retired_product_skus as $retired_sku ) {
    $retired_id = wc_get_product_id_by_sku( $retired_sku );
    if ( ! $retired_id ) { continue; }

    if ( '1' !== (string) get_post_meta( $retired_id, '_drielo_managed_product', true ) ) {
        echo 'SKIPPED RETIRE unmanaged sku=' . $retired_sku . ' product_id=' . $retired_id . PHP_EOL;
        continue;
    }

    $retired_post = get_post( $retired_id );
    if ( $retired_post instanceof WP_Post && 'trash' !== $retired_post->post_status ) {
        wp_trash_post( $retired_id );
        echo 'RETIRED PRODUCT sku=' . $retired_sku . ' product_id=' . $retired_id . PHP_EOL;
    }
}

foreach ( array_values( array_unique( array_filter( array_map( 'sanitize_title', (array) ( $catalog['retired_collections'] ?? array() ) ) ) ) ) as $retired_collection_slug ) {
    $retired_term = get_term_by( 'slug', $retired_collection_slug, 'product_collection' );
    if ( ! $retired_term instanceof WP_Term ) { continue; }

    clean_term_cache( $retired_term->term_id, 'product_collection' );
    $retired_term = get_term( $retired_term->term_id, 'product_collection' );
    if ( $retired_term instanceof WP_Term && 0 === (int) $retired_term->count ) {
        $deleted = wp_delete_term( $retired_term->term_id, 'product_collection' );
        if ( ! is_wp_error( $deleted ) ) {
            echo 'RETIRED COLLECTION slug=' . $retired_collection_slug . PHP_EOL;
        }
    }
}

$created = 0;
$updated = 0;
$pending = 0;

foreach ( (array) ( $catalog['products'] ?? array() ) as $row ) {
    $sku = sanitize_text_field( (string) $row['sku'] );
    $existing_id = wc_get_product_id_by_sku( $sku );
    if ( ! $existing_id ) {
        foreach ( (array) ( $row['previous_skus'] ?? array() ) as $previous_sku ) {
            $previous_sku = sanitize_text_field( (string) $previous_sku );
            if ( '' === $previous_sku ) { continue; }
            $existing_id = wc_get_product_id_by_sku( $previous_sku );
            if ( $existing_id ) {
                echo 'MIGRATING SKU ' . $previous_sku . ' -> ' . $sku . ' product_id=' . $existing_id . PHP_EOL;
                break;
            }
        }
    }
    $product = $existing_id ? wc_get_product( $existing_id ) : new WC_Product_Simple();
    if ( ! $product instanceof WC_Product_Simple ) {
        fwrite( STDERR, "Skipping $sku: product exists with unsupported type\n" );
        continue;
    }

    $product->set_name( (string) ( $row['title_en'] ?? $row['title'] ) );
    $product->set_slug( sanitize_title( (string) $row['slug'] ) );
    $product->set_sku( $sku );
    $product->set_status( 'publish' );
    $product->set_catalog_visibility( 'visible' );
    $product->set_regular_price( number_format( (float) ( $row['price'] ?? 4.99 ), 2, '.', '' ) );
    $product->set_virtual( true );
    $product->set_downloadable( true );
    $product->set_sold_individually( true );
    $product->set_manage_stock( false );
    $product->set_short_description( (string) ( $row['short_description_en'] ?? $row['short_description'] ) );
    $product->set_description( (string) ( $row['description_en'] ?? $row['description'] ) );
    $product->set_purchase_note( (string) ( $row['purchase_note_en'] ?? 'Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.' ) );

    $attribute_specs = array(
        (string) ( $row['size_attribute_label'] ?? 'Pattern size' ) => (string) ( $row['grid'] ?? '' ),
        (string) ( $row['colour_attribute_label'] ?? 'DMC colours' ) => (string) ( $row['colours'] ?? '' ),
        'Skill level' => (string) ( $row['skill'] ?? '' ),
        (string) ( $row['type_attribute_label'] ?? 'Stitch type' ) => (string) ( $row['stitch_type'] ?? '' ),
        (string) ( $row['count_attribute_label'] ?? 'Total stitches' ) => number_format_i18n( absint( $row['stitches'] ?? 0 ) ),
    );
    $attributes = array();
    $position = 0;
    foreach ( $attribute_specs as $name => $value ) {
        if ( '' === trim( $value ) ) { continue; }
        $attribute = new WC_Product_Attribute();
        $attribute->set_id( 0 );
        $attribute->set_name( $name );
        $attribute->set_options( array( $value ) );
        $attribute->set_position( $position++ );
        $attribute->set_visible( true );
        $attribute->set_variation( false );
        $attributes[] = $attribute;
    }
    foreach ( (array) ( $row['filters'] ?? array() ) as $filter_slug => $filter_terms ) {
        $filter_slug = wc_sanitize_taxonomy_name( (string) $filter_slug );
        $taxonomy = 'pa_' . $filter_slug;
        if ( ! taxonomy_exists( $taxonomy ) ) {
            fwrite( STDERR, "WARNING $sku: missing catalog taxonomy $taxonomy\n" );
            continue;
        }

        $term_ids = array();
        foreach ( array_values( array_unique( array_filter( array_map( 'sanitize_title', (array) $filter_terms ) ) ) ) as $term_slug ) {
            $term = get_term_by( 'slug', $term_slug, $taxonomy );
            if ( ! $term instanceof WP_Term ) {
                $term_name = (string) ( $drielo_filter_term_names[ $filter_slug ][ $term_slug ] ?? ucwords( str_replace( '-', ' ', $term_slug ) ) );
                $inserted = wp_insert_term( $term_name, $taxonomy, array( 'slug' => $term_slug ) );
                if ( is_wp_error( $inserted ) ) { throw new RuntimeException( $inserted->get_error_message() ); }
                $term = get_term( (int) $inserted['term_id'], $taxonomy );
            }
            if ( $term instanceof WP_Term ) { $term_ids[] = (int) $term->term_id; }
        }

        if ( $term_ids ) {
            $attribute = new WC_Product_Attribute();
            $attribute->set_id( wc_attribute_taxonomy_id_by_name( $taxonomy ) );
            $attribute->set_name( $taxonomy );
            $attribute->set_options( $term_ids );
            $attribute->set_position( $position++ );
            $attribute->set_visible( false );
            $attribute->set_variation( false );
            $attributes[] = $attribute;
        }
    }

    $product->set_attributes( $attributes );

    $cats = array();
    foreach ( (array) ( $row['categories'] ?? array() ) as $slug ) {
        $slug = sanitize_title( (string) $slug );
        if ( isset( $category_ids[ $slug ] ) ) { $cats[] = (int) $category_ids[ $slug ]; }
    }
    $product->set_category_ids( array_values( array_unique( $cats ) ) );

    $gallery_ids = array();
    $gallery_revision = sanitize_text_field( (string) ( $row['gallery_revision'] ?? '' ) );
    $featured_asset = trim( (string) ( $row['featured_image'] ?? '' ) );
    $featured_id = 0;

    if ( '' !== $featured_asset ) {
        $featured_id = drielo_media_from_file(
            rtrim( $source, '/' ) . '/' . $featured_asset,
            $featured_asset,
            (string) $row['title'] . ' - featured',
            $gallery_revision
        );
        if ( $featured_id ) { $product->set_image_id( $featured_id ); }
    }

    foreach ( (array) ( $row['gallery'] ?? array() ) as $index => $asset ) {
        $asset = (string) $asset;
        if ( '' !== $featured_asset && $asset === $featured_asset ) { continue; }

        $id = drielo_media_from_file(
            rtrim( $source, '/' ) . '/' . $asset,
            $asset,
            (string) $row['title'] . ' - preview ' . ( $index + 1 ),
            $gallery_revision
        );
        if ( ! $id ) { continue; }

        if ( '' === $featured_asset && 0 === $index ) {
            $product->set_image_id( $id );
        } else {
            $gallery_ids[] = $id;
        }
    }
    $product->set_gallery_image_ids( array_values( array_unique( $gallery_ids ) ) );

    $download_rel = (string) ( $row['download'] ?? '' );
    $download_abs = $download_rel ? rtrim( $source, '/' ) . '/' . $download_rel : '';
    $prepared_downloads = array();
    if ( $download_abs && is_file( $download_abs ) && filesize( $download_abs ) > 1000 ) {
        $prepared_downloads = drielo_install_download( $download_abs, wp_basename( $download_abs ), $gallery_revision );
        $product->set_stock_status( 'instock' );
    } else {
        $existing_downloads = $existing_id ? $product->get_downloads() : array();
        if ( ! empty( $existing_downloads ) ) {
            $prepared_downloads = $existing_downloads;
            $product->set_stock_status( 'instock' );
        } else {
            $product->set_stock_status( 'outofstock' );
            $pending++;
        }
    }

    // WooCommerce's approved-directory validation can reject a freshly-created
    // protected upload URL before it has been registered. Save the product first
    // and persist the already-copied download metadata directly afterwards.
    $product->set_downloads( array() );
    $id = $product->save();
    if ( ! $id ) { fwrite( STDERR, "Failed to save $sku\n" ); continue; }

    update_post_meta( $id, '_drielo_managed_product', '1' );
    update_post_meta( $id, '_drielo_product_code', sanitize_text_field( (string) $row['code'] ) );
    update_post_meta( $id, '_drielo_featured_source', sanitize_text_field( $featured_asset ) );
    update_post_meta( $id, '_drielo_title_es', sanitize_text_field( (string) ( $row['title_es'] ?? $row['title'] ) ) );
    update_post_meta( $id, '_drielo_title_en', sanitize_text_field( (string) ( $row['title_en'] ?? $row['title'] ) ) );
    update_post_meta( $id, '_drielo_short_description_es', wp_kses_post( (string) ( $row['short_description_es'] ?? $row['short_description'] ) ) );
    update_post_meta( $id, '_drielo_short_description_en', wp_kses_post( (string) ( $row['short_description_en'] ?? $row['short_description'] ) ) );
    update_post_meta( $id, '_drielo_description_es', wp_kses_post( (string) ( $row['description_es'] ?? $row['description'] ) ) );
    update_post_meta( $id, '_drielo_description_en', wp_kses_post( (string) ( $row['description_en'] ?? $row['description'] ) ) );
    update_post_meta( $id, '_drielo_purchase_note_es', sanitize_text_field( (string) ( $row['purchase_note_es'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_purchase_note_en', sanitize_text_field( (string) ( $row['purchase_note_en'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_skill_es', sanitize_text_field( (string) ( $row['skill_es'] ?? $row['skill'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_skill_en', sanitize_text_field( (string) ( $row['skill_en'] ?? $row['skill'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_stitch_type_es', sanitize_text_field( (string) ( $row['stitch_type_es'] ?? $row['stitch_type'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_stitch_type_en', sanitize_text_field( (string) ( $row['stitch_type_en'] ?? $row['stitch_type'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_seo_title_es', sanitize_text_field( (string) ( $row['seo_title_es'] ?? $row['seo_title'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_seo_title_en', sanitize_text_field( (string) ( $row['seo_title_en'] ?? $row['seo_title'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_meta_description_es', sanitize_text_field( (string) ( $row['meta_description_es'] ?? $row['meta_description'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_meta_description_en', sanitize_text_field( (string) ( $row['meta_description_en'] ?? $row['meta_description'] ?? '' ) ) );

    // Etsy-ready listing copy is stored separately so the sync plugin can use
    // buyer-facing marketplace text without sacrificing the WooCommerce fields.
    $etsy_title_en = sanitize_text_field( (string) ( $row['etsy_title_en'] ?? $row['title_en'] ?? $row['title'] ?? '' ) );
    $etsy_title_es = sanitize_text_field( (string) ( $row['etsy_title_es'] ?? $row['title_es'] ?? $row['title'] ?? '' ) );
    $etsy_description_en = sanitize_textarea_field( (string) ( $row['etsy_description_en'] ?? wp_strip_all_tags( $row['description_en'] ?? $row['description'] ?? '' ) ) );
    $etsy_description_es = sanitize_textarea_field( (string) ( $row['etsy_description_es'] ?? wp_strip_all_tags( $row['description_es'] ?? $row['description'] ?? '' ) ) );
    $etsy_tags_en = array_values( array_filter( array_map( 'sanitize_text_field', (array) ( $row['etsy_tags_en'] ?? $row['tags'] ?? array() ) ) ) );
    $etsy_tags_es = array_values( array_filter( array_map( 'sanitize_text_field', (array) ( $row['etsy_tags_es'] ?? array() ) ) ) );

    update_post_meta( $id, '_drielo_etsy_title', $etsy_title_en );
    update_post_meta( $id, '_drielo_etsy_title_en', $etsy_title_en );
    update_post_meta( $id, '_drielo_etsy_title_es', $etsy_title_es );
    update_post_meta( $id, '_drielo_etsy_description', $etsy_description_en );
    update_post_meta( $id, '_drielo_etsy_description_en', $etsy_description_en );
    update_post_meta( $id, '_drielo_etsy_description_es', $etsy_description_es );
    update_post_meta( $id, '_drielo_etsy_tags', $etsy_tags_en );
    update_post_meta( $id, '_drielo_etsy_tags_en', $etsy_tags_en );
    update_post_meta( $id, '_drielo_etsy_tags_es', $etsy_tags_es );

    update_post_meta( $id, '_drielo_design_id', sanitize_text_field( (string) ( $row['design_id'] ?? $row['code'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_base_design_id', sanitize_text_field( (string) ( $row['base_design_id'] ?? $row['design_id'] ?? $row['code'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_grid_width', absint( $row['grid_width'] ?? 0 ) );
    update_post_meta( $id, '_drielo_grid_height', absint( $row['grid_height'] ?? 0 ) );
    update_post_meta( $id, '_drielo_color_count', absint( $row['color_count'] ?? $row['colours'] ?? 0 ) );
    update_post_meta( $id, '_drielo_technique', sanitize_text_field( (string) ( $row['technique'] ?? ( $row['filters']['technique'][0] ?? '' ) ) ) );
    update_post_meta( $id, '_drielo_technique_code', sanitize_text_field( (string) ( $row['technique_code'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_size_attribute_label', sanitize_text_field( (string) ( $row['size_attribute_label'] ?? 'Pattern size' ) ) );
    update_post_meta( $id, '_drielo_colour_attribute_label', sanitize_text_field( (string) ( $row['colour_attribute_label'] ?? 'DMC colours' ) ) );
    update_post_meta( $id, '_drielo_count_attribute_label', sanitize_text_field( (string) ( $row['count_attribute_label'] ?? 'Total stitches' ) ) );
    update_post_meta( $id, '_drielo_catalog_filters', wp_json_encode( (array) ( $row['filters'] ?? array() ) ) );
    update_post_meta( $id, '_drielo_stitch_count', absint( $row['stitches'] ?? 0 ) );
    update_post_meta( $id, '_drielo_grid', sanitize_text_field( (string) ( $row['grid'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_skill', sanitize_text_field( (string) ( $row['skill'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_stitch_type', sanitize_text_field( (string) ( $row['stitch_type'] ?? '' ) ) );
    update_post_meta( $id, '_make_seo_title', sanitize_text_field( (string) ( $row['seo_title_en'] ?? $row['seo_title'] ?? '' ) ) );
    update_post_meta( $id, '_make_meta_description', sanitize_text_field( (string) ( $row['meta_description_en'] ?? $row['meta_description'] ?? '' ) ) );

    if ( ! empty( $prepared_downloads ) ) {
        $download_meta = array();
        foreach ( $prepared_downloads as $download ) {
            if ( $download instanceof WC_Product_Download ) {
                $download_meta[ $download->get_id() ] = array(
                    'name' => $download->get_name(),
                    'file' => $download->get_file(),
                );
            }
        }
        update_post_meta( $id, '_downloadable_files', $download_meta );
        update_post_meta( $id, '_downloadable', 'yes' );
        delete_post_meta( $id, '_drielo_download_pending' );
    } else {
        update_post_meta( $id, '_downloadable_files', array() );
        update_post_meta( $id, '_drielo_download_pending', '1' );
    }

    foreach ( (array) ( $row['filters'] ?? array() ) as $filter_slug => $filter_terms ) {
        $taxonomy = 'pa_' . wc_sanitize_taxonomy_name( (string) $filter_slug );
        if ( taxonomy_exists( $taxonomy ) ) {
            $term_slugs = array_values( array_unique( array_filter( array_map( 'sanitize_title', (array) $filter_terms ) ) ) );
            wp_set_object_terms( $id, $term_slugs, $taxonomy, false );
        }
    }

    $collection_slug = sanitize_title( (string) ( $row['collection'] ?? '' ) );
    if ( $collection_slug && isset( $collections[ $collection_slug ] ) ) {
        wp_set_object_terms( $id, array( (int) $collections[ $collection_slug ] ), 'product_collection', false );
    }

    $tag_source = (array) ( $row['etsy_tags_en'] ?? $row['tags'] ?? array() );
    $tag_names = array_values(
        array_filter(
            array_map(
                static fn( $tag ) => sanitize_text_field( (string) $tag ),
                $tag_source
            )
        )
    );
    if ( $tag_names ) { wp_set_object_terms( $id, $tag_names, 'product_tag', false ); }

    if ( $existing_id ) { $updated++; } else { $created++; }
    echo ( $existing_id ? 'UPDATED ' : 'CREATED ' ) . $sku . ' product_id=' . $id . PHP_EOL;
}

foreach ( array_values( array_unique( $legacy_collection_terms ) ) as $legacy_term_id ) {
    $legacy_term = get_term( $legacy_term_id, 'product_collection' );
    if ( $legacy_term instanceof WP_Term && 0 === (int) $legacy_term->count ) {
        $deleted = wp_delete_term( $legacy_term_id, 'product_collection' );
        if ( ! is_wp_error( $deleted ) ) {
            echo 'DELETED LEGACY COLLECTION term_id=' . $legacy_term_id . PHP_EOL;
        }
    }
}

echo "RESULT created=$created updated=$updated download_pending=$pending" . PHP_EOL;
