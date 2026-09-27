<?php
/**
 * Repair and verify the replace-all Pop Art 60 deployment.
 *
 * Usage:
 * php repair-pop-art-60.php /var/www/html /tmp/drielo-products
 */

if ( PHP_SAPI !== 'cli' ) { fwrite( STDERR, "CLI only\n" ); exit(2); }

$wp_root = $argv[1] ?? '';
$source  = $argv[2] ?? '';
if ( ! $wp_root || ! $source ) {
    fwrite( STDERR, "Usage: php repair-pop-art-60.php WP_ROOT SOURCE_DIR\n" );
    exit(2);
}

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

function drielo_pop_media( string $path, string $source_key, string $title ): int {
    if ( ! is_file( $path ) || filesize( $path ) < 1000 ) {
        throw new RuntimeException( 'Missing Pop Art media source: ' . $source_key );
    }

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
        $id = (int) $existing[0];
        $attached = get_attached_file( $id );
        if ( $attached && is_file( $attached ) ) {
            update_post_meta( $id, '_drielo_source_hash', md5_file( $path ) ?: '' );
            return $id;
        }
        if ( $attached ) {
            wp_mkdir_p( dirname( $attached ) );
            if ( ! copy( $path, $attached ) ) {
                throw new RuntimeException( 'Unable to restore attachment file: ' . $source_key );
            }
            $dims = @getimagesize( $attached );
            if ( is_array( $dims ) ) {
                wp_update_attachment_metadata(
                    $id,
                    array(
                        'width'  => (int) $dims[0],
                        'height' => (int) $dims[1],
                        'file'   => _wp_relative_upload_path( $attached ),
                        'sizes'  => array(),
                    )
                );
            }
            update_post_meta( $id, '_drielo_source_hash', md5_file( $path ) ?: '' );
            return $id;
        }
    }

    $filename = wp_basename( $path );
    $bits = wp_upload_bits( $filename, null, (string) file_get_contents( $path ) );
    if ( ! empty( $bits['error'] ) ) {
        throw new RuntimeException( (string) $bits['error'] );
    }

    $type = wp_check_filetype( $filename, null );
    $id = wp_insert_attachment(
        array(
            'post_mime_type' => $type['type'] ?: 'image/webp',
            'post_title'     => $title,
            'post_status'    => 'inherit',
        ),
        $bits['file']
    );
    if ( is_wp_error( $id ) || ! $id ) {
        throw new RuntimeException( is_wp_error( $id ) ? $id->get_error_message() : 'Could not create media attachment' );
    }

    $dims = @getimagesize( $bits['file'] );
    if ( is_array( $dims ) ) {
        wp_update_attachment_metadata(
            $id,
            array(
                'width'  => (int) $dims[0],
                'height' => (int) $dims[1],
                'file'   => _wp_relative_upload_path( $bits['file'] ),
                'sizes'  => array(),
            )
        );
    }
    update_post_meta( $id, '_drielo_source_asset', $source_key );
    update_post_meta( $id, '_drielo_source_hash', md5_file( $path ) ?: '' );
    return (int) $id;
}

function drielo_pop_download( string $source_path, string $filename ): array {
    if ( ! is_file( $source_path ) || filesize( $source_path ) < 100000 ) {
        throw new RuntimeException( 'Missing or invalid Pop Art PDF: ' . $filename );
    }
    if ( '%PDF' !== (string) file_get_contents( $source_path, false, null, 0, 4 ) ) {
        throw new RuntimeException( 'Invalid PDF header: ' . $filename );
    }

    $uploads = wp_upload_dir();
    if ( ! empty( $uploads['error'] ) ) {
        throw new RuntimeException( (string) $uploads['error'] );
    }
    $relative = 'woocommerce_uploads/drielo';
    $dir = trailingslashit( $uploads['basedir'] ) . $relative;
    if ( ! wp_mkdir_p( $dir ) ) {
        throw new RuntimeException( 'Unable to create protected download directory' );
    }

    $destination = trailingslashit( $dir ) . $filename;
    if ( ! copy( $source_path, $destination ) ) {
        throw new RuntimeException( 'Unable to install PDF: ' . $filename );
    }
    @chmod( $destination, 0644 );

    $url = trailingslashit( $uploads['baseurl'] ) . $relative . '/' . rawurlencode( $filename );
    $download = new WC_Product_Download();
    $download->set_id( md5( $destination ) );
    $download->set_name( $filename );
    $download->set_file( $url );
    return array( $download );
}

$expected = array();
for ( $i = 1; $i <= 60; $i++ ) {
    $expected[] = sprintf( 'DRIELO-P%04d-CS', 1000 + $i );
}
$expected_map = array_fill_keys( $expected, true );

$term = get_term_by( 'slug', 'pop-art-25', 'product_collection' );
if ( ! $term instanceof WP_Term ) {
    fwrite( STDERR, "Pop Art collection term not found\n" );
    exit(4);
}

// Replace-all cleanup: no managed residue may remain in Pop Art.
$assigned_ids = get_posts(
    array(
        'post_type'      => 'product',
        'post_status'    => array( 'publish', 'draft', 'pending', 'private', 'future' ),
        'posts_per_page' => -1,
        'fields'         => 'ids',
        'no_found_rows'  => true,
        'tax_query'      => array(
            array(
                'taxonomy' => 'product_collection',
                'field'    => 'term_id',
                'terms'    => array( (int) $term->term_id ),
            ),
        ),
    )
);
foreach ( array_map( 'intval', $assigned_ids ) as $id ) {
    if ( '1' !== (string) get_post_meta( $id, '_drielo_managed_product', true ) ) { continue; }
    $product = wc_get_product( $id );
    $sku = $product instanceof WC_Product ? (string) $product->get_sku() : '';
    if ( ! isset( $expected_map[ $sku ] ) ) {
        wp_trash_post( $id );
        echo 'PURGED POP ART RESIDUE ' . $sku . ' id=' . $id . PHP_EOL;
    }
}

$verified = array();
for ( $i = 1; $i <= 60; $i++ ) {
    $base = sprintf( 'P%04d', 1000 + $i );
    $code = $base . '-CS';
    $sku  = 'DRIELO-' . $code;

    $id = wc_get_product_id_by_sku( $sku );
    if ( ! $id ) {
        throw new RuntimeException( 'Missing Pop Art product: ' . $sku );
    }
    $product = wc_get_product( $id );
    if ( ! $product instanceof WC_Product_Simple ) {
        throw new RuntimeException( 'Unexpected product type: ' . $sku );
    }

    $featured_rel = 'assets/' . $code . '-product.webp';
    $featured_id = drielo_pop_media(
        rtrim( $source, '/' ) . '/' . $featured_rel,
        $featured_rel,
        $product->get_name() . ' - featured'
    );

    $gallery_ids = array();
    foreach ( array( 'design', 'gallery-2', 'gallery-3', 'gallery-4' ) as $suffix ) {
        $rel = 'assets/' . $code . '-' . $suffix . '.webp';
        $gallery_ids[] = drielo_pop_media(
            rtrim( $source, '/' ) . '/' . $rel,
            $rel,
            $product->get_name() . ' - ' . $suffix
        );
    }

    $pdf_name = 'Drielo_' . $code . '.pdf';
    $downloads = drielo_pop_download(
        rtrim( $source, '/' ) . '/files/' . $pdf_name,
        $pdf_name
    );

    $product->set_image_id( $featured_id );
    $product->set_gallery_image_ids( array_values( array_unique( array_map( 'intval', $gallery_ids ) ) ) );
    $product->set_status( 'publish' );
    $product->set_catalog_visibility( 'visible' );
    $product->set_stock_status( 'instock' );
    $product->set_downloadable( true );
    $product->save();

    $download_meta = array();
    foreach ( $downloads as $download ) {
        $download_meta[ $download->get_id() ] = array(
            'name' => $download->get_name(),
            'file' => $download->get_file(),
        );
    }
    update_post_meta( $id, '_downloadable_files', $download_meta );
    update_post_meta( $id, '_downloadable', 'yes' );
    delete_post_meta( $id, '_drielo_download_pending' );
    wp_set_object_terms( $id, array( (int) $term->term_id ), 'product_collection', false );

    clean_post_cache( $id );
    wc_delete_product_transients( $id );
    $check = wc_get_product( $id );
    $images = $check ? 1 + count( $check->get_gallery_image_ids() ) : 0;
    $download_count = $check ? count( $check->get_downloads() ) : 0;
    $stock = $check ? $check->get_stock_status() : '';

    if ( 5 !== $images || $download_count < 1 || 'instock' !== $stock ) {
        throw new RuntimeException(
            $sku . ': repair verification failed images=' . $images .
            ' downloads=' . $download_count . ' stock=' . $stock
        );
    }

    $verified[ $sku ] = true;
    echo 'REPAIRED ' . $sku . ' id=' . $id . ' images=5 downloads=' . $download_count . ' stock=instock' . PHP_EOL;
}

clean_term_cache( (int) $term->term_id, 'product_collection' );
$term = get_term( (int) $term->term_id, 'product_collection' );
if ( ! $term instanceof WP_Term || 60 !== (int) $term->count ) {
    throw new RuntimeException( 'Pop Art collection count is not 60 after repair' );
}
if ( 60 !== count( $verified ) ) {
    throw new RuntimeException( 'Did not verify exactly 60 Pop Art products' );
}

echo 'POP_ART_REPAIR_OK=60' . PHP_EOL;
