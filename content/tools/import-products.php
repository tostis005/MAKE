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
        if ( '' !== $source_revision && hash_equals( $known_revision, $source_revision ) ) {
            return $attachment_id;
        }
        $known_hash = (string) get_post_meta( $attachment_id, '_drielo_source_hash', true );
        if ( '' === $source_revision && $source_hash && hash_equals( $known_hash, $source_hash ) ) {
            return $attachment_id;
        }

        $attached_file = get_attached_file( $attachment_id );
        if ( $attached_file ) {
            wp_mkdir_p( dirname( $attached_file ) );
            if ( ! copy( $path, $attached_file ) ) {
                throw new RuntimeException( 'Could not refresh existing product image: ' . $source_key );
            }
            $metadata = wp_generate_attachment_metadata( $attachment_id, $attached_file );
            if ( is_array( $metadata ) ) {
                wp_update_attachment_metadata( $attachment_id, $metadata );
            }
            wp_update_post(
                array(
                    'ID'         => $attachment_id,
                    'post_title' => $title,
                )
            );
            update_post_meta( $attachment_id, '_drielo_source_hash', $source_hash );
            if ( '' !== $source_revision ) { update_post_meta( $attachment_id, '_drielo_source_revision', $source_revision ); }
            return $attachment_id;
        }
    }

    $filename = wp_basename( $path );
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

function drielo_install_download( string $source_path, string $filename ): array {
    if ( ! is_file( $source_path ) || filesize( $source_path ) < 1000 ) { return array(); }

    $uploads = wp_upload_dir();
    if ( ! empty( $uploads['error'] ) ) { throw new RuntimeException( (string) $uploads['error'] ); }

    $relative = 'woocommerce_uploads/drielo';
    $dir = trailingslashit( $uploads['basedir'] ) . $relative;
    if ( ! wp_mkdir_p( $dir ) ) { throw new RuntimeException( 'Could not create protected downloads directory' ); }

    $destination = trailingslashit( $dir ) . $filename;
    if ( ! copy( $source_path, $destination ) ) { throw new RuntimeException( 'Could not copy downloadable PDF' ); }
    @chmod( $destination, 0644 );

    $deny = trailingslashit( dirname( $dir ) ) . '.htaccess';
    if ( ! is_file( $deny ) ) {
        @file_put_contents( $deny, "deny from all\n" );
    }

    $url = trailingslashit( $uploads['baseurl'] ) . $relative . '/' . rawurlencode( $filename );
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
    $category_ids[ $slug ] = drielo_term( 'product_cat', (string) $cat['name'], $slug, $parent );
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

$created = 0;
$updated = 0;
$pending = 0;

foreach ( (array) ( $catalog['products'] ?? array() ) as $row ) {
    $sku = sanitize_text_field( (string) $row['sku'] );
    $existing_id = wc_get_product_id_by_sku( $sku );
    $product = $existing_id ? wc_get_product( $existing_id ) : new WC_Product_Simple();
    if ( ! $product instanceof WC_Product_Simple ) {
        fwrite( STDERR, "Skipping $sku: product exists with unsupported type\n" );
        continue;
    }

    $product->set_name( (string) $row['title'] );
    $product->set_slug( sanitize_title( (string) $row['slug'] ) );
    $product->set_sku( $sku );
    $product->set_status( 'publish' );
    $product->set_catalog_visibility( 'visible' );
    $product->set_regular_price( number_format( (float) ( $row['price'] ?? 4.99 ), 2, '.', '' ) );
    $product->set_virtual( true );
    $product->set_downloadable( true );
    $product->set_sold_individually( true );
    $product->set_manage_stock( false );
    $product->set_short_description( (string) $row['short_description'] );
    $product->set_description( (string) $row['description'] );
    $product->set_purchase_note( 'Your digital PDF will be available from the order confirmation and My Account > Downloads after payment is complete.' );

    $attribute_specs = array(
        'Pattern size'  => (string) ( $row['grid'] ?? '' ),
        'DMC colours'   => (string) ( $row['colours'] ?? '' ),
        'Skill level'   => (string) ( $row['skill'] ?? '' ),
        'Stitch type'   => (string) ( $row['stitch_type'] ?? '' ),
        'Total stitches'=> number_format_i18n( absint( $row['stitches'] ?? 0 ) ),
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
    $product->set_attributes( $attributes );

    $cats = array();
    foreach ( (array) ( $row['categories'] ?? array() ) as $slug ) {
        $slug = sanitize_title( (string) $slug );
        if ( isset( $category_ids[ $slug ] ) ) { $cats[] = (int) $category_ids[ $slug ]; }
    }
    $product->set_category_ids( array_values( array_unique( $cats ) ) );

    $gallery_ids = array();
    $gallery_revision = sanitize_text_field( (string) ( $row['gallery_revision'] ?? '' ) );
    foreach ( (array) ( $row['gallery'] ?? array() ) as $index => $asset ) {
        $id = drielo_media_from_file(
            rtrim( $source, '/' ) . '/' . $asset,
            (string) $asset,
            (string) $row['title'] . ' - preview ' . ( $index + 1 ),
            $gallery_revision
        );
        if ( ! $id ) { continue; }
        if ( 0 === $index ) { $product->set_image_id( $id ); }
        else { $gallery_ids[] = $id; }
    }
    $product->set_gallery_image_ids( $gallery_ids );

    $download_rel = (string) ( $row['download'] ?? '' );
    $download_abs = $download_rel ? rtrim( $source, '/' ) . '/' . $download_rel : '';
    $prepared_downloads = array();
    if ( $download_abs && is_file( $download_abs ) && filesize( $download_abs ) > 1000 ) {
        $prepared_downloads = drielo_install_download( $download_abs, wp_basename( $download_abs ) );
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
    update_post_meta( $id, '_drielo_stitch_count', absint( $row['stitches'] ?? 0 ) );
    update_post_meta( $id, '_drielo_grid', sanitize_text_field( (string) ( $row['grid'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_skill', sanitize_text_field( (string) ( $row['skill'] ?? '' ) ) );
    update_post_meta( $id, '_drielo_stitch_type', sanitize_text_field( (string) ( $row['stitch_type'] ?? '' ) ) );
    update_post_meta( $id, '_make_seo_title', sanitize_text_field( (string) ( $row['seo_title'] ?? '' ) ) );
    update_post_meta( $id, '_make_meta_description', sanitize_text_field( (string) ( $row['meta_description'] ?? '' ) ) );

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

    $collection_slug = sanitize_title( (string) ( $row['collection'] ?? '' ) );
    if ( $collection_slug && isset( $collections[ $collection_slug ] ) ) {
        wp_set_object_terms( $id, array( (int) $collections[ $collection_slug ] ), 'product_collection', false );
    }

    $tag_names = array_map(
        static fn( $tag ) => ucwords( str_replace( '-', ' ', sanitize_title( (string) $tag ) ) ),
        (array) ( $row['tags'] ?? array() )
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
