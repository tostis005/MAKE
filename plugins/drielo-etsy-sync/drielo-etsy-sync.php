<?php
/**
 * Plugin Name: Drielo Etsy Sync
 * Description: Centraliza la selección y sincronización de productos WooCommerce con Etsy, incluidos productos digitales, imágenes y PDFs.
 * Version: 1.2.0
 * Author: Drielo
 * Requires Plugins: woocommerce
 * Requires PHP: 8.0
 * Text Domain: drielo-etsy-sync
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class Drielo_Etsy_Sync {
    const VERSION = '1.2.0';
    const OPTION_SETTINGS = 'drielo_etsy_settings';
    const OPTION_TOKENS   = 'drielo_etsy_tokens';

    const META_ENABLED       = '_drielo_etsy_enabled';
    const META_TARGET_STATE  = '_drielo_etsy_target_state';
    const META_LISTING_ID    = '_drielo_etsy_listing_id';
    const META_REMOTE_STATE  = '_drielo_etsy_remote_state';
    const META_LAST_SYNC     = '_drielo_etsy_last_sync';
    const META_LAST_ERROR    = '_drielo_etsy_last_error';
    const META_ASSET_HASH    = '_drielo_etsy_asset_hash';
    const META_CONTENT_HASH  = '_drielo_etsy_content_hash';

    private static $instance = null;

    public static function instance() {
        if ( null === self::$instance ) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action( 'admin_menu', [ $this, 'admin_menu' ] );
        add_action( 'admin_enqueue_scripts', [ $this, 'admin_assets' ] );
        add_action( 'admin_init', [ $this, 'maybe_handle_oauth_callback' ] );
        add_action( 'template_redirect', [ $this, 'maybe_handle_oauth_callback' ] );

        add_action( 'admin_post_drielo_etsy_save_products', [ $this, 'handle_save_products' ] );
        add_action( 'admin_post_drielo_etsy_sync_products', [ $this, 'handle_sync_products' ] );
        add_action( 'admin_post_drielo_etsy_overwrite_products', [ $this, 'handle_overwrite_products' ] );
        add_action( 'admin_post_drielo_etsy_save_settings', [ $this, 'handle_save_settings' ] );
        add_action( 'admin_post_drielo_etsy_connect', [ $this, 'handle_connect' ] );
        add_action( 'admin_post_drielo_etsy_disconnect', [ $this, 'handle_disconnect' ] );
    }

    public function admin_menu() {
        add_menu_page(
            'Drielo',
            'Drielo',
            'manage_woocommerce',
            'drielo-etsy',
            [ $this, 'render_products_page' ],
            'dashicons-store',
            56
        );

        add_submenu_page(
            'drielo-etsy',
            'Productos Etsy',
            'Productos Etsy',
            'manage_woocommerce',
            'drielo-etsy',
            [ $this, 'render_products_page' ]
        );

        add_submenu_page(
            'drielo-etsy',
            'Configuración Etsy',
            'Configuración',
            'manage_woocommerce',
            'drielo-etsy-settings',
            [ $this, 'render_settings_page' ]
        );
    }

    public function admin_assets( $hook ) {
        if ( strpos( $hook, 'drielo-etsy' ) === false ) {
            return;
        }
        wp_enqueue_style( 'drielo-etsy-admin', plugin_dir_url( __FILE__ ) . 'assets/admin.css', [], self::VERSION );
        wp_enqueue_script( 'drielo-etsy-admin', plugin_dir_url( __FILE__ ) . 'assets/admin.js', [ 'jquery' ], self::VERSION, true );
    }

    private function require_capability() {
        if ( ! current_user_can( 'manage_woocommerce' ) ) {
            wp_die( esc_html__( 'No tienes permisos para gestionar esta integración.', 'drielo-etsy-sync' ) );
        }
    }

    private function settings() {
        $defaults = [
            'api_key'          => '',
            'shared_secret'    => '',
            'shop_id'          => '',
            'shop_name'        => '',
            'taxonomy_id'      => 6343,
            'who_made'         => 'i_did',
            'when_made'        => '2020_2026',
            'quantity'         => 999,
            'default_language' => 'en-US',
            'sync_images'       => 1,
            'sync_files'        => 1,
            'sync_tags'         => 1,
            'sync_pdf_previews' => 1,
            'auto_taxonomy'     => 1,
            'auto_renew'        => 1,
            'ai_disclosure'     => 1,
        ];
        $settings = wp_parse_args( get_option( self::OPTION_SETTINGS, [] ), $defaults );
        if ( empty( $settings['taxonomy_id'] ) ) {
            $settings['taxonomy_id'] = 6343;
        }
        return $settings;
    }

    private function tokens() {
        return wp_parse_args( get_option( self::OPTION_TOKENS, [] ), [
            'access_token'  => '',
            'refresh_token' => '',
            'expires_at'    => 0,
            'scope'         => '',
            'user_id'       => '',
        ] );
    }

    private function is_connected() {
        $settings = $this->settings();
        $tokens   = $this->tokens();
        return ! empty( $settings['api_key'] ) && ! empty( $settings['shared_secret'] ) && ! empty( $tokens['refresh_token'] );
    }


    private function ensure_shop_identity() {
        $settings = $this->settings();
        if ( ! empty( $settings['shop_id'] ) ) {
            return $settings;
        }

        $tokens  = $this->tokens();
        $user_id = preg_replace( '/\D+/', '', (string) ( $tokens['user_id'] ?? '' ) );
        if ( ! $user_id && ! empty( $tokens['access_token'] ) && strpos( $tokens['access_token'], '.' ) !== false ) {
            $user_id = preg_replace( '/\D+/', '', (string) strtok( $tokens['access_token'], '.' ) );
        }
        if ( ! $user_id ) {
            return $settings;
        }

        $shop = $this->etsy_request( 'GET', '/v3/application/users/' . rawurlencode( $user_id ) . '/shops', [], false );
        if ( ! is_wp_error( $shop ) && ! empty( $shop['shop_id'] ) ) {
            $settings['shop_id']   = (string) absint( $shop['shop_id'] );
            $settings['shop_name'] = sanitize_text_field( $shop['shop_name'] ?? '' );
            update_option( self::OPTION_SETTINGS, $settings, false );
        }

        return $settings;
    }

    public function render_products_page() {
        $this->require_capability();
        if ( ! class_exists( 'WooCommerce' ) ) {
            echo '<div class="wrap"><h1>Drielo · Etsy</h1><div class="notice notice-error"><p>WooCommerce debe estar activo.</p></div></div>';
            return;
        }

        $paged      = max( 1, absint( $_GET['paged'] ?? 1 ) );
        $search     = sanitize_text_field( wp_unslash( $_GET['s'] ?? '' ) );
        $collection = sanitize_title( wp_unslash( $_GET['collection'] ?? '' ) );
        $technique  = sanitize_title( wp_unslash( $_GET['technique'] ?? '' ) );
        $limit      = 50;

        $collection_terms = taxonomy_exists( 'product_collection' )
            ? get_terms( [ 'taxonomy' => 'product_collection', 'hide_empty' => false, 'orderby' => 'name' ] )
            : [];
        $technique_terms = taxonomy_exists( 'pa_technique' )
            ? get_terms( [ 'taxonomy' => 'pa_technique', 'hide_empty' => false, 'orderby' => 'name' ] )
            : [];
        if ( is_wp_error( $collection_terms ) ) { $collection_terms = []; }
        if ( is_wp_error( $technique_terms ) ) { $technique_terms = []; }

        $query_args = [
            'post_type'      => 'product',
            'post_status'    => [ 'publish', 'draft', 'private', 'pending' ],
            'posts_per_page' => $limit,
            'paged'          => $paged,
            'orderby'        => 'date',
            'order'          => 'DESC',
            'fields'         => 'ids',
        ];

        $tax_query = [];
        if ( $collection && taxonomy_exists( 'product_collection' ) ) {
            $tax_query[] = [ 'taxonomy' => 'product_collection', 'field' => 'slug', 'terms' => [ $collection ] ];
        }
        if ( $technique && taxonomy_exists( 'pa_technique' ) ) {
            $tax_query[] = [ 'taxonomy' => 'pa_technique', 'field' => 'slug', 'terms' => [ $technique ] ];
        }
        if ( $tax_query ) {
            if ( count( $tax_query ) > 1 ) {
                array_unshift( $tax_query, [ 'relation' => 'AND' ] );
            }
            $query_args['tax_query'] = $tax_query;
        }

        if ( $search ) {
            $title_query = new WP_Query( [
                'post_type'      => 'product',
                'post_status'    => [ 'publish', 'draft', 'private', 'pending' ],
                'posts_per_page' => -1,
                'fields'         => 'ids',
                's'              => $search,
                'no_found_rows'  => true,
            ] );
            $sku_ids = get_posts( [
                'post_type'      => 'product',
                'post_status'    => [ 'publish', 'draft', 'private', 'pending' ],
                'posts_per_page' => -1,
                'fields'         => 'ids',
                'meta_query'     => [
                    [ 'key' => '_sku', 'value' => $search, 'compare' => 'LIKE' ],
                ],
            ] );
            $search_ids = array_values( array_unique( array_map( 'absint', array_merge( (array) $title_query->posts, (array) $sku_ids ) ) ) );
            $query_args['post__in'] = $search_ids ?: [ 0 ];
        }

        $query = new WP_Query( $query_args );
        $products = [];
        foreach ( (array) $query->posts as $product_id ) {
            $product = wc_get_product( $product_id );
            if ( $product ) { $products[] = $product; }
        }
        $total_pages = max( 1, (int) $query->max_num_pages );

        $notice = sanitize_text_field( wp_unslash( $_GET['drielo_notice'] ?? '' ) );
        ?>
        <div class="wrap drielo-wrap">
            <div class="drielo-header">
                <div>
                    <h1>Drielo · Etsy</h1>
                    <p>Filtra el catálogo, activa los productos que quieras gestionar y usa la sincronización segura por defecto. La sobrescritura completa solo se ejecuta sobre filas marcadas explícitamente.</p>
                </div>
                <div class="drielo-connection <?php echo $this->is_connected() ? 'is-connected' : 'is-disconnected'; ?>">
                    <span class="drielo-dot"></span>
                    <?php echo $this->is_connected() ? 'Etsy conectado' : 'Etsy sin conectar'; ?>
                </div>
            </div>

            <?php if ( $notice ) : ?>
                <div class="notice notice-success is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div>
            <?php endif; ?>

            <?php if ( ! $this->is_connected() ) : ?>
                <div class="notice notice-warning"><p>Configura las credenciales de Etsy y conecta la tienda antes de sincronizar. <a href="<?php echo esc_url( admin_url( 'admin.php?page=drielo-etsy-settings' ) ); ?>">Ir a Configuración</a>.</p></div>
            <?php endif; ?>

            <div class="drielo-sync-policy">
                <strong>Sincronización segura:</strong> si el listing ya existe, no reemplaza título, descripción, precio, tags, categoría, imágenes ni PDF. Solo crea listings que falten y aplica el objetivo Borrador/Publicado.
                <br /><strong>Sobrescribir seleccionados:</strong> vuelve a enviar toda la información de Drielo y los assets, por lo que puede reemplazar cambios manuales hechos directamente en Etsy.
            </div>

            <form method="get" class="drielo-search-form drielo-filter-form">
                <input type="hidden" name="page" value="drielo-etsy" />
                <input type="search" name="s" value="<?php echo esc_attr( $search ); ?>" placeholder="Buscar producto o SKU…" />
                <select name="collection">
                    <option value="">Todas las colecciones</option>
                    <?php foreach ( $collection_terms as $term ) : ?>
                        <option value="<?php echo esc_attr( $term->slug ); ?>" <?php selected( $collection, $term->slug ); ?>><?php echo esc_html( $term->name ); ?></option>
                    <?php endforeach; ?>
                </select>
                <select name="technique">
                    <option value="">Todos los tipos de trabajo</option>
                    <?php foreach ( $technique_terms as $term ) : ?>
                        <option value="<?php echo esc_attr( $term->slug ); ?>" <?php selected( $technique, $term->slug ); ?>><?php echo esc_html( $term->name ); ?></option>
                    <?php endforeach; ?>
                </select>
                <button class="button button-primary">Filtrar</button>
                <?php if ( $search || $collection || $technique ) : ?><a class="button" href="<?php echo esc_url( admin_url( 'admin.php?page=drielo-etsy' ) ); ?>">Limpiar</a><?php endif; ?>
            </form>

            <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" id="drielo-products-form">
                <?php wp_nonce_field( 'drielo_etsy_products', 'drielo_nonce' ); ?>

                <div class="drielo-toolbar">
                    <div class="drielo-sync-actions">
                        <button type="submit" class="button button-primary" name="action" value="drielo_etsy_save_products">Guardar selección</button>
                        <button type="submit" class="button button-secondary" name="action" value="drielo_etsy_sync_products" <?php disabled( ! $this->is_connected() ); ?>>Sincronizar seguro</button>
                        <button type="submit" class="button drielo-overwrite-button" name="action" value="drielo_etsy_overwrite_products" data-confirm-overwrite <?php disabled( ! $this->is_connected() ); ?>>Sobrescribir seleccionados desde Drielo</button>
                    </div>
                    <div class="drielo-bulk-target">
                        <label for="bulk-target">Cambiar objetivo de seleccionados:</label>
                        <select id="bulk-target">
                            <option value="">— Sin cambios —</option>
                            <option value="draft">Borrador</option>
                            <option value="active">Publicado</option>
                        </select>
                        <button type="button" class="button" id="apply-bulk-target">Aplicar</button>
                    </div>
                </div>

                <div class="drielo-table-card">
                    <table class="widefat fixed striped drielo-table">
                        <thead>
                            <tr>
                                <td class="check-column"><input type="checkbox" id="drielo-select-all" /></td>
                                <th class="drielo-preview-column">Vista</th>
                                <th>Producto</th>
                                <th>SKU</th>
                                <th>Publicar en Etsy</th>
                                <th>Objetivo</th>
                                <th>Estado Etsy</th>
                                <th>Sync</th>
                                <th>PDF</th>
                                <th>Última sync</th>
                                <th>Listing</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php if ( empty( $products ) ) : ?>
                            <tr><td colspan="11">No se han encontrado productos con estos filtros.</td></tr>
                        <?php else : ?>
                            <?php foreach ( $products as $product ) :
                                $id = $product->get_id();
                                $enabled = 'yes' === get_post_meta( $id, self::META_ENABLED, true );
                                $target = get_post_meta( $id, self::META_TARGET_STATE, true ) ?: 'draft';
                                $remote_state = get_post_meta( $id, self::META_REMOTE_STATE, true );
                                $listing_id = get_post_meta( $id, self::META_LISTING_ID, true );
                                $last_sync = get_post_meta( $id, self::META_LAST_SYNC, true );
                                $last_error = get_post_meta( $id, self::META_LAST_ERROR, true );
                                $saved_content_hash = (string) get_post_meta( $id, self::META_CONTENT_HASH, true );
                                $saved_asset_hash = (string) get_post_meta( $id, self::META_ASSET_HASH, true );
                                $current_content_hash = $this->product_content_hash( $product );
                                $current_asset_hash = $this->product_asset_hash( $product );
                                $downloads = $product->get_downloads();
                                $pdf_count = 0;
                                foreach ( $downloads as $download ) {
                                    if ( preg_match( '/\.pdf(?:\?.*)?$/i', (string) $download->get_file() ) ) { $pdf_count++; }
                                }

                                $collection_names = taxonomy_exists( 'product_collection' )
                                    ? wp_get_post_terms( $id, 'product_collection', [ 'fields' => 'names' ] )
                                    : [];
                                $technique_names = taxonomy_exists( 'pa_technique' )
                                    ? wp_get_post_terms( $id, 'pa_technique', [ 'fields' => 'names' ] )
                                    : [];
                                if ( is_wp_error( $collection_names ) ) { $collection_names = []; }
                                if ( is_wp_error( $technique_names ) ) { $technique_names = []; }

                                if ( ! $listing_id ) {
                                    $sync_label = 'Nuevo';
                                    $sync_class = 'sync-new';
                                    $sync_help = 'Se creará completo al sincronizar.';
                                } elseif ( ! $saved_content_hash ) {
                                    $sync_label = 'Protegido';
                                    $sync_class = 'sync-protected';
                                    $sync_help = 'Listing existente sin referencia de sobrescritura. La sync segura no tocará su contenido.';
                                } elseif ( ! hash_equals( $saved_content_hash, $current_content_hash ) || ! $saved_asset_hash || ! hash_equals( $saved_asset_hash, $current_asset_hash ) ) {
                                    $sync_label = 'Cambios en Drielo';
                                    $sync_class = 'sync-pending';
                                    $sync_help = 'Hay cambios locales. Usa Sobrescribir seleccionados solo si quieres enviarlos a Etsy.';
                                } else {
                                    $sync_label = 'Al día';
                                    $sync_class = 'sync-clean';
                                    $sync_help = 'No se detectan cambios locales desde la última sobrescritura.';
                                }
                                ?>
                                <tr class="<?php echo $last_error ? 'has-error' : ''; ?>">
                                    <th class="check-column"><input type="checkbox" class="drielo-row-select" name="selected_ids[]" value="<?php echo esc_attr( $id ); ?>" /></th>
                                    <td class="drielo-preview-cell"><?php echo $product->get_image( [ 72, 90 ], [ 'loading' => 'lazy' ] ); ?></td>
                                    <td class="drielo-product-cell">
                                        <div>
                                            <strong><a href="<?php echo esc_url( get_edit_post_link( $id ) ); ?>"><?php echo esc_html( $product->get_name() ); ?></a></strong>
                                            <small>#<?php echo esc_html( $id ); ?></small>
                                            <?php if ( $collection_names ) : ?><small>Colección: <?php echo esc_html( implode( ', ', $collection_names ) ); ?></small><?php endif; ?>
                                            <?php if ( $technique_names ) : ?><small>Tipo: <?php echo esc_html( implode( ', ', $technique_names ) ); ?></small><?php endif; ?>
                                            <?php if ( $last_error ) : ?><span class="drielo-error" title="<?php echo esc_attr( $last_error ); ?>">Error: <?php echo esc_html( wp_trim_words( $last_error, 14 ) ); ?></span><?php endif; ?>
                                        </div>
                                    </td>
                                    <td><?php echo esc_html( $product->get_sku() ?: '—' ); ?></td>
                                    <td>
                                        <label class="drielo-switch">
                                            <input type="checkbox" class="drielo-enabled" name="products[<?php echo esc_attr( $id ); ?>][enabled]" value="yes" <?php checked( $enabled ); ?> />
                                            <span></span>
                                        </label>
                                    </td>
                                    <td>
                                        <select class="drielo-target" name="products[<?php echo esc_attr( $id ); ?>][target]">
                                            <option value="draft" <?php selected( $target, 'draft' ); ?>>Borrador</option>
                                            <option value="active" <?php selected( $target, 'active' ); ?>>Publicado</option>
                                        </select>
                                    </td>
                                    <td><?php echo $this->status_badge( $remote_state, $listing_id, $last_error ); ?></td>
                                    <td><span class="drielo-sync-state <?php echo esc_attr( $sync_class ); ?>" title="<?php echo esc_attr( $sync_help ); ?>"><?php echo esc_html( $sync_label ); ?></span></td>
                                    <td><?php echo $pdf_count ? '<span class="drielo-ok">' . esc_html( $pdf_count ) . ' PDF</span>' : '<span class="drielo-muted">Sin PDF</span>'; ?></td>
                                    <td><?php echo $last_sync ? esc_html( wp_date( 'd/m/Y H:i', strtotime( $last_sync ) ) ) : '—'; ?></td>
                                    <td>
                                        <?php if ( $listing_id ) : ?>
                                            <code><?php echo esc_html( $listing_id ); ?></code>
                                            <a class="drielo-external" href="<?php echo esc_url( 'https://www.etsy.com/listing/' . rawurlencode( $listing_id ) ); ?>" target="_blank" rel="noopener">Ver ↗</a>
                                        <?php else : ?>—<?php endif; ?>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                        </tbody>
                    </table>
                </div>

                <div class="drielo-toolbar drielo-toolbar-bottom">
                    <button type="submit" class="button button-primary" name="action" value="drielo_etsy_save_products">Guardar selección</button>
                    <button type="submit" class="button button-secondary" name="action" value="drielo_etsy_sync_products" <?php disabled( ! $this->is_connected() ); ?>>Sincronizar seguro</button>
                    <button type="submit" class="button drielo-overwrite-button" name="action" value="drielo_etsy_overwrite_products" data-confirm-overwrite <?php disabled( ! $this->is_connected() ); ?>>Sobrescribir seleccionados desde Drielo</button>
                </div>
            </form>

            <?php
            if ( $total_pages > 1 ) {
                $base = add_query_arg( [
                    'page'       => 'drielo-etsy',
                    's'          => $search,
                    'collection' => $collection,
                    'technique'  => $technique,
                    'paged'      => '%#%',
                ], admin_url( 'admin.php' ) );
                echo '<div class="tablenav"><div class="tablenav-pages">' . wp_kses_post( paginate_links( [
                    'base'      => $base,
                    'format'    => '',
                    'current'   => $paged,
                    'total'     => $total_pages,
                    'prev_text' => '‹',
                    'next_text' => '›',
                ] ) ) . '</div></div>';
            }
            ?>
        </div>
        <?php
    }

    private function status_badge( $state, $listing_id, $error ) {
        if ( $error ) {
            return '<span class="drielo-status status-error">Error</span>';
        }
        if ( ! $listing_id ) {
            return '<span class="drielo-status status-none">No sincronizado</span>';
        }
        $labels = [
            'active'   => [ 'Publicado', 'status-active' ],
            'draft'    => [ 'Borrador', 'status-draft' ],
            'inactive' => [ 'Inactivo', 'status-inactive' ],
            'expired'  => [ 'Caducado', 'status-inactive' ],
            'sold_out' => [ 'Agotado', 'status-inactive' ],
        ];
        $label = $labels[ $state ] ?? [ ucfirst( (string) $state ?: 'Sin estado' ), 'status-none' ];
        return '<span class="drielo-status ' . esc_attr( $label[1] ) . '">' . esc_html( $label[0] ) . '</span>';
    }

    public function render_settings_page() {
        $this->require_capability();
        $settings = $this->settings();
        $tokens   = $this->tokens();
        $callback = home_url( '/etsy/callback/' );
        $notice = sanitize_text_field( wp_unslash( $_GET['drielo_notice'] ?? '' ) );
        $error  = sanitize_text_field( wp_unslash( $_GET['drielo_error'] ?? '' ) );
        ?>
        <div class="wrap drielo-wrap drielo-settings">
            <div class="drielo-header">
                <div><h1>Drielo · Configuración Etsy</h1><p>Conecta tu tienda de Etsy y define los valores por defecto para los patrones digitales.</p></div>
                <div class="drielo-connection <?php echo $this->is_connected() ? 'is-connected' : 'is-disconnected'; ?>"><span class="drielo-dot"></span><?php echo $this->is_connected() ? 'Etsy conectado' : 'Etsy sin conectar'; ?></div>
            </div>
            <?php if ( $notice ) : ?><div class="notice notice-success is-dismissible"><p><?php echo esc_html( $notice ); ?></p></div><?php endif; ?>
            <?php if ( $error ) : ?><div class="notice notice-error is-dismissible"><p><?php echo esc_html( $error ); ?></p></div><?php endif; ?>

            <div class="drielo-settings-grid">
                <div class="drielo-card">
                    <h2>1. Credenciales de la app Etsy</h2>
                    <p>Crea una app en Etsy Developers y pega aquí el <strong>Keystring</strong> y el <strong>Shared Secret</strong>. La URL de callback debe registrarse exactamente como aparece abajo.</p>
                    <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                        <?php wp_nonce_field( 'drielo_etsy_settings', 'drielo_nonce' ); ?>
                        <input type="hidden" name="action" value="drielo_etsy_save_settings" />
                        <table class="form-table" role="presentation">
                            <tr><th><label for="api_key">API Key / Keystring</label></th><td><input class="regular-text" type="text" id="api_key" name="settings[api_key]" value="<?php echo esc_attr( $settings['api_key'] ); ?>" autocomplete="off" /></td></tr>
                            <tr><th><label for="shared_secret">Shared Secret</label></th><td><input class="regular-text" type="password" id="shared_secret" name="settings[shared_secret]" value="" placeholder="<?php echo $settings['shared_secret'] ? '••••••••••••' : ''; ?>" autocomplete="new-password" /><p class="description">Déjalo vacío para conservar el secreto ya guardado.</p></td></tr>
                            <tr><th>Callback URL</th><td><div class="drielo-copy-row"><code id="drielo-callback-url"><?php echo esc_html( $callback ); ?></code><button type="button" class="button" data-copy="#drielo-callback-url">Copiar</button></div></td></tr>
                            <tr><th><label for="shop_id">Shop ID</label></th><td><input class="regular-text" type="text" id="shop_id" name="settings[shop_id]" value="<?php echo esc_attr( $settings['shop_id'] ); ?>" /><p class="description">Normalmente se detecta automáticamente al conectar Etsy; puedes fijarlo manualmente si lo necesitas.</p></td></tr>
                        </table>

                        <h2>2. Valores por defecto para patrones</h2>
                        <table class="form-table" role="presentation">
                            <tr><th><label for="taxonomy_id">Taxonomy ID de respaldo</label></th><td><input type="number" class="small-text" id="taxonomy_id" name="settings[taxonomy_id]" value="<?php echo esc_attr( $settings['taxonomy_id'] ); ?>" min="1" /><p class="description">Solo se usa si Etsy no permite resolver automáticamente una categoría específica para la técnica del patrón.</p><label><input type="checkbox" name="settings[auto_taxonomy]" value="1" <?php checked( ! empty( $settings['auto_taxonomy'] ) ); ?> /> Elegir automáticamente la categoría Etsy según la técnica (punto de cruz, C2C, tapestry o latch hook)</label></td></tr>
                            <tr><th><label for="quantity">Cantidad</label></th><td><input type="number" class="small-text" id="quantity" name="settings[quantity]" value="<?php echo esc_attr( $settings['quantity'] ); ?>" min="1" max="999" /></td></tr>
                            <tr><th>Autoría / IA</th><td><strong>Diseñado por Drielo</strong><p class="description">Etsy clasifica los diseños digitales asistidos por IA dentro de “Designed by a seller”. La API pública no expone un campo separado para “generador de IA”, así que el plugin envía Drielo como autor y añade automáticamente la declaración de uso de IA en la descripción.</p></td></tr>
                            <tr><th><label for="when_made">Cuándo se hizo</label></th><td><select id="when_made" name="settings[when_made]"><option value="2020_2026" <?php selected( $settings['when_made'], '2020_2026' ); ?>>2020–2026</option><option value="made_to_order" <?php selected( $settings['when_made'], 'made_to_order' ); ?>>Hecho bajo pedido</option></select></td></tr>
                            <tr><th><label for="default_language">Idioma Etsy</label></th><td><input class="small-text" type="text" id="default_language" name="settings[default_language]" value="<?php echo esc_attr( $settings['default_language'] ); ?>" /></td></tr>
                            <tr><th>Sincronizar</th><td>
                                <label><input type="checkbox" name="settings[sync_images]" value="1" <?php checked( ! empty( $settings['sync_images'] ) ); ?> /> Imagen destacada + galería</label><br />
                                <label><input type="checkbox" name="settings[sync_pdf_previews]" value="1" <?php checked( ! empty( $settings['sync_pdf_previews'] ) ); ?> /> Crear imágenes extra desde el PDF (ficha, colores y recortes parciales de gráficos)</label><br />
                                <label><input type="checkbox" name="settings[sync_files]" value="1" <?php checked( ! empty( $settings['sync_files'] ) ); ?> /> Archivos descargables/PDF</label><br />
                                <label><input type="checkbox" name="settings[sync_tags]" value="1" <?php checked( ! empty( $settings['sync_tags'] ) ); ?> /> Tags específicos para Etsy</label><br />
                                <label><input type="checkbox" name="settings[auto_renew]" value="1" <?php checked( ! empty( $settings['auto_renew'] ) ); ?> /> Renovación automática del listing al caducar</label><br />
                                <label><input type="checkbox" name="settings[ai_disclosure]" value="1" <?php checked( ! empty( $settings['ai_disclosure'] ) ); ?> /> Añadir declaración de uso de IA a la descripción</label>
                            </td></tr>
                        </table>
                        <?php submit_button( 'Guardar configuración' ); ?>
                    </form>
                </div>

                <div class="drielo-card drielo-connect-card">
                    <h2>Conexión con Etsy</h2>
                    <?php if ( $this->is_connected() ) : ?>
                        <div class="drielo-connected-panel">
                            <span class="dashicons dashicons-yes-alt"></span>
                            <div><strong>Conectado</strong><p><?php echo esc_html( $settings['shop_name'] ? $settings['shop_name'] . ' · ' : '' ); ?>Shop ID: <?php echo esc_html( $settings['shop_id'] ?: '—' ); ?></p><p>Permisos: <?php echo esc_html( $tokens['scope'] ?: 'listings_r listings_w' ); ?></p></div>
                        </div>
                        <p>El token de acceso se renueva automáticamente usando el refresh token.</p>
                        <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                            <?php wp_nonce_field( 'drielo_etsy_disconnect', 'drielo_nonce' ); ?>
                            <input type="hidden" name="action" value="drielo_etsy_disconnect" />
                            <button class="button">Desconectar Etsy</button>
                        </form>
                    <?php else : ?>
                        <p>Guarda primero el Keystring y Shared Secret. Después conecta Etsy mediante OAuth.</p>
                        <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
                            <?php wp_nonce_field( 'drielo_etsy_connect', 'drielo_nonce' ); ?>
                            <input type="hidden" name="action" value="drielo_etsy_connect" />
                            <button class="button button-primary button-hero" <?php disabled( empty( $settings['api_key'] ) || empty( $settings['shared_secret'] ) ); ?>>Conectar con Etsy</button>
                        </form>
                    <?php endif; ?>
                    <hr />
                    <h3>Qué se sincroniza</h3>
                    <ul class="drielo-check-list"><li>Título específico para Etsy</li><li>Descripción estructurada con párrafos y viñetas</li><li>Precio EUR de la web y SKU</li><li>Categoría automática según técnica</li><li>Imagen destacada, galería y previews seguros del PDF</li><li>PDFs/archivos descargables</li><li>Tags específicos para Etsy</li><li>Producto digital, renovación automática y declaración de IA</li><li>Estado Borrador / Publicado</li></ul>
                </div>
            </div>
        </div>
        <?php
    }

    public function handle_save_settings() {
        $this->require_capability();
        check_admin_referer( 'drielo_etsy_settings', 'drielo_nonce' );
        $input = isset( $_POST['settings'] ) ? (array) wp_unslash( $_POST['settings'] ) : [];
        $current = $this->settings();
        $settings = [
            'api_key'          => sanitize_text_field( $input['api_key'] ?? '' ),
            'shared_secret'    => sanitize_text_field( $input['shared_secret'] ?? '' ) ?: ( $current['shared_secret'] ?? '' ),
            'shop_id'          => preg_replace( '/\D+/', '', (string) ( $input['shop_id'] ?? '' ) ),
            'shop_name'        => $current['shop_name'] ?? '',
            'taxonomy_id'      => absint( $input['taxonomy_id'] ?? 0 ),
            'who_made'         => in_array( $input['who_made'] ?? '', [ 'i_did', 'collective', 'someone_else' ], true ) ? $input['who_made'] : 'i_did',
            'when_made'        => in_array( $input['when_made'] ?? '', [ '2020_2026', 'made_to_order' ], true ) ? $input['when_made'] : '2020_2026',
            'quantity'         => min( 999, max( 1, absint( $input['quantity'] ?? 999 ) ) ),
            'default_language' => sanitize_text_field( $input['default_language'] ?? 'en-US' ),
            'sync_images'       => empty( $input['sync_images'] ) ? 0 : 1,
            'sync_files'        => empty( $input['sync_files'] ) ? 0 : 1,
            'sync_tags'         => empty( $input['sync_tags'] ) ? 0 : 1,
            'sync_pdf_previews' => empty( $input['sync_pdf_previews'] ) ? 0 : 1,
            'auto_taxonomy'     => empty( $input['auto_taxonomy'] ) ? 0 : 1,
            'auto_renew'        => empty( $input['auto_renew'] ) ? 0 : 1,
            'ai_disclosure'     => empty( $input['ai_disclosure'] ) ? 0 : 1,
        ];
        update_option( self::OPTION_SETTINGS, $settings, false );
        wp_safe_redirect( add_query_arg( 'drielo_notice', rawurlencode( 'Configuración guardada.' ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
        exit;
    }

    public function handle_save_products() {
        $this->require_capability();
        check_admin_referer( 'drielo_etsy_products', 'drielo_nonce' );
        $products = isset( $_POST['products'] ) ? (array) wp_unslash( $_POST['products'] ) : [];
        foreach ( $products as $id => $row ) {
            $id = absint( $id );
            if ( ! $id || ! wc_get_product( $id ) ) {
                continue;
            }
            $enabled = ! empty( $row['enabled'] ) && 'yes' === $row['enabled'];
            $target  = ( $row['target'] ?? 'draft' ) === 'active' ? 'active' : 'draft';
            update_post_meta( $id, self::META_ENABLED, $enabled ? 'yes' : 'no' );
            update_post_meta( $id, self::META_TARGET_STATE, $target );
        }
        wp_safe_redirect( add_query_arg( 'drielo_notice', rawurlencode( 'Selección guardada. Los productos activados conservarán este estado hasta que lo cambies.' ), wp_get_referer() ?: admin_url( 'admin.php?page=drielo-etsy' ) ) );
        exit;
    }

    public function handle_sync_products() {
        $this->handle_sync_products_mode( false );
    }

    public function handle_overwrite_products() {
        $this->handle_sync_products_mode( true );
    }

    private function handle_sync_products_mode( bool $overwrite ) {
        $this->require_capability();
        check_admin_referer( 'drielo_etsy_products', 'drielo_nonce' );

        $products = isset( $_POST['products'] ) ? (array) wp_unslash( $_POST['products'] ) : [];
        foreach ( $products as $id => $row ) {
            $id = absint( $id );
            if ( ! $id || ! wc_get_product( $id ) ) {
                continue;
            }
            $enabled = ! empty( $row['enabled'] ) && 'yes' === $row['enabled'];
            $target  = ( $row['target'] ?? 'draft' ) === 'active' ? 'active' : 'draft';
            update_post_meta( $id, self::META_ENABLED, $enabled ? 'yes' : 'no' );
            update_post_meta( $id, self::META_TARGET_STATE, $target );
        }

        $row_selection = array_values( array_unique( array_filter( array_map( 'absint', (array) ( $_POST['selected_ids'] ?? [] ) ) ) ) );
        if ( $overwrite && empty( $row_selection ) ) {
            wp_safe_redirect( add_query_arg(
                'drielo_notice',
                rawurlencode( 'No se ha sobrescrito nada. Marca primero una o más filas: la sobrescritura nunca se aplica a todo el catálogo automáticamente.' ),
                wp_get_referer() ?: admin_url( 'admin.php?page=drielo-etsy' )
            ) );
            exit;
        }

        if ( $row_selection ) {
            $selected = $row_selection;
        } else {
            $selected = get_posts( [
                'post_type'      => 'product',
                'post_status'    => [ 'publish', 'draft', 'private', 'pending' ],
                'posts_per_page' => -1,
                'fields'         => 'ids',
                'meta_key'       => self::META_ENABLED,
                'meta_value'     => 'yes',
                'orderby'        => 'ID',
                'order'          => 'ASC',
            ] );
        }

        $selected = array_values( array_unique( array_filter( array_map( 'absint', (array) $selected ) ) ) );
        $selected = array_values( array_filter( $selected, static function( $product_id ) {
            return 'yes' === get_post_meta( $product_id, self::META_ENABLED, true );
        } ) );

        if ( empty( $selected ) ) {
            wp_safe_redirect( add_query_arg(
                'drielo_notice',
                rawurlencode( 'No hay productos activados para Etsy dentro de la selección.' ),
                wp_get_referer() ?: admin_url( 'admin.php?page=drielo-etsy' )
            ) );
            exit;
        }

        $ok = 0;
        $failed = 0;
        foreach ( $selected as $product_id ) {
            $result = $this->sync_product( $product_id, $overwrite );
            if ( is_wp_error( $result ) ) {
                $failed++;
            } else {
                $ok++;
            }
        }

        $message = $overwrite
            ? sprintf( 'Sobrescritura terminada: %d actualizados desde Drielo, %d con error.', $ok, $failed )
            : sprintf( 'Sincronización segura terminada: %d correctos, %d con error. Los listings existentes conservaron sus datos de Etsy.', $ok, $failed );

        wp_safe_redirect( add_query_arg( 'drielo_notice', rawurlencode( $message ), wp_get_referer() ?: admin_url( 'admin.php?page=drielo-etsy' ) ) );
        exit;
    }

    public function handle_connect() {
        $this->require_capability();
        check_admin_referer( 'drielo_etsy_connect', 'drielo_nonce' );
        $settings = $this->settings();
        if ( empty( $settings['api_key'] ) || empty( $settings['shared_secret'] ) ) {
            wp_safe_redirect( add_query_arg( 'drielo_error', rawurlencode( 'Guarda primero el Keystring y Shared Secret.' ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
            exit;
        }

        $verifier = $this->base64url_encode( random_bytes( 64 ) );
        if ( strlen( $verifier ) > 128 ) {
            $verifier = substr( $verifier, 0, 128 );
        }
        $challenge = $this->base64url_encode( hash( 'sha256', $verifier, true ) );
        $state = wp_generate_password( 40, false, false );
        set_transient( 'drielo_etsy_oauth_' . get_current_user_id(), [ 'verifier' => $verifier, 'state' => $state ], 15 * MINUTE_IN_SECONDS );

        $callback = home_url( '/etsy/callback/' );
        $url = add_query_arg( [
            'response_type'         => 'code',
            'client_id'             => $settings['api_key'],
            'redirect_uri'          => $callback,
            'scope'                 => 'listings_r listings_w',
            'state'                 => $state,
            'code_challenge'        => $challenge,
            'code_challenge_method' => 'S256',
        ], 'https://www.etsy.com/oauth/connect' );
        wp_redirect( $url );
        exit;
    }

    public function maybe_handle_oauth_callback() {
        $request_path  = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ), PHP_URL_PATH ) : '';
        $callback_path = (string) wp_parse_url( home_url( '/etsy/callback/' ), PHP_URL_PATH );
        $is_clean_callback = trailingslashit( $request_path ) === trailingslashit( $callback_path );

        if ( ! $is_clean_callback && ( empty( $_GET['drielo_etsy_oauth'] ) || '1' !== (string) $_GET['drielo_etsy_oauth'] ) ) {
            return;
        }
        $this->require_capability();
        $settings = $this->settings();
        $flow = get_transient( 'drielo_etsy_oauth_' . get_current_user_id() );
        delete_transient( 'drielo_etsy_oauth_' . get_current_user_id() );

        $error = sanitize_text_field( wp_unslash( $_GET['error_description'] ?? $_GET['error'] ?? '' ) );
        if ( $error ) {
            wp_safe_redirect( add_query_arg( 'drielo_error', rawurlencode( $error ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
            exit;
        }
        $state = sanitize_text_field( wp_unslash( $_GET['state'] ?? '' ) );
        $code  = sanitize_text_field( wp_unslash( $_GET['code'] ?? '' ) );
        if ( ! is_array( $flow ) || empty( $flow['state'] ) || ! hash_equals( $flow['state'], $state ) || ! $code ) {
            wp_safe_redirect( add_query_arg( 'drielo_error', rawurlencode( 'La respuesta OAuth de Etsy no es válida o ha caducado.' ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
            exit;
        }

        $response = wp_remote_post( 'https://api.etsy.com/v3/public/oauth/token', [
            'timeout' => 30,
            'headers' => [ 'Content-Type' => 'application/x-www-form-urlencoded; charset=utf-8' ],
            'body'    => [
                'grant_type'    => 'authorization_code',
                'client_id'     => $settings['api_key'],
                'redirect_uri'  => home_url( '/etsy/callback/' ),
                'code'          => $code,
                'code_verifier' => $flow['verifier'],
            ],
        ] );
        if ( is_wp_error( $response ) ) {
            $this->oauth_fail( $response->get_error_message() );
        }
        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( wp_remote_retrieve_response_code( $response ) >= 300 || empty( $data['access_token'] ) ) {
            $this->oauth_fail( $data['error_description'] ?? $data['error'] ?? 'Etsy no devolvió un access token válido.' );
        }

        $user_id = '';
        if ( strpos( $data['access_token'], '.' ) !== false ) {
            $user_id = strtok( $data['access_token'], '.' );
        }
        update_option( self::OPTION_TOKENS, [
            'access_token'  => sanitize_text_field( $data['access_token'] ),
            'refresh_token' => sanitize_text_field( $data['refresh_token'] ?? '' ),
            'expires_at'    => time() + absint( $data['expires_in'] ?? 3600 ),
            'scope'         => sanitize_text_field( $data['scope'] ?? '' ),
            'user_id'       => preg_replace( '/\D+/', '', (string) $user_id ),
        ], false );

        if ( $user_id ) {
            $shop = $this->etsy_request( 'GET', '/v3/application/users/' . rawurlencode( $user_id ) . '/shops', [], false );
            if ( ! is_wp_error( $shop ) && ! empty( $shop['shop_id'] ) ) {
                $settings['shop_id']   = (string) $shop['shop_id'];
                $settings['shop_name'] = sanitize_text_field( $shop['shop_name'] ?? '' );
                update_option( self::OPTION_SETTINGS, $settings, false );
            }
        }

        wp_safe_redirect( add_query_arg( 'drielo_notice', rawurlencode( 'Etsy conectado correctamente.' ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
        exit;
    }

    private function oauth_fail( $message ) {
        wp_safe_redirect( add_query_arg( 'drielo_error', rawurlencode( sanitize_text_field( $message ) ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
        exit;
    }

    public function handle_disconnect() {
        $this->require_capability();
        check_admin_referer( 'drielo_etsy_disconnect', 'drielo_nonce' );
        delete_option( self::OPTION_TOKENS );
        wp_safe_redirect( add_query_arg( 'drielo_notice', rawurlencode( 'Etsy desconectado.' ), admin_url( 'admin.php?page=drielo-etsy-settings' ) ) );
        exit;
    }

    private function base64url_encode( $value ) {
        return rtrim( strtr( base64_encode( $value ), '+/', '-_' ), '=' );
    }

    private function get_access_token() {
        $tokens = $this->tokens();
        if ( empty( $tokens['refresh_token'] ) ) {
            return new WP_Error( 'etsy_not_connected', 'Etsy no está conectado.' );
        }
        if ( ! empty( $tokens['access_token'] ) && (int) $tokens['expires_at'] > time() + 120 ) {
            return $tokens['access_token'];
        }
        $settings = $this->settings();
        $response = wp_remote_post( 'https://api.etsy.com/v3/public/oauth/token', [
            'timeout' => 30,
            'headers' => [ 'Content-Type' => 'application/x-www-form-urlencoded; charset=utf-8' ],
            'body'    => [
                'grant_type'    => 'refresh_token',
                'client_id'     => $settings['api_key'],
                'refresh_token' => $tokens['refresh_token'],
            ],
        ] );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $data = json_decode( wp_remote_retrieve_body( $response ), true );
        if ( wp_remote_retrieve_response_code( $response ) >= 300 || empty( $data['access_token'] ) ) {
            return new WP_Error( 'etsy_refresh_failed', $data['error_description'] ?? $data['error'] ?? 'No se pudo renovar el token de Etsy.' );
        }
        $tokens['access_token']  = sanitize_text_field( $data['access_token'] );
        $tokens['refresh_token'] = sanitize_text_field( $data['refresh_token'] ?? $tokens['refresh_token'] );
        $tokens['expires_at']    = time() + absint( $data['expires_in'] ?? 3600 );
        if ( ! empty( $data['scope'] ) ) {
            $tokens['scope'] = sanitize_text_field( $data['scope'] );
        }
        update_option( self::OPTION_TOKENS, $tokens, false );
        return $tokens['access_token'];
    }

    private function etsy_request( $method, $path, $body = [], $needs_oauth = true ) {
        $settings = $this->settings();
        if ( empty( $settings['api_key'] ) || empty( $settings['shared_secret'] ) ) {
            return new WP_Error( 'etsy_credentials', 'Faltan el Keystring o Shared Secret de Etsy.' );
        }
        $headers = [
            'x-api-key' => $settings['api_key'] . ':' . $settings['shared_secret'],
            'Accept'    => 'application/json',
        ];
        if ( $needs_oauth ) {
            $token = $this->get_access_token();
            if ( is_wp_error( $token ) ) {
                return $token;
            }
            $headers['Authorization'] = 'Bearer ' . $token;
        }

        $args = [ 'method' => strtoupper( $method ), 'timeout' => 60, 'headers' => $headers ];
        if ( ! empty( $body ) ) {
            $headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8';
            $args['headers'] = $headers;
            $args['body'] = http_build_query( $body, '', '&', PHP_QUERY_RFC3986 );
        }
        $response = wp_remote_request( 'https://api.etsy.com' . $path, $args );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $raw  = wp_remote_retrieve_body( $response );
        $data = $raw !== '' ? json_decode( $raw, true ) : [];
        if ( $code < 200 || $code >= 300 ) {
            $message = is_array( $data ) ? ( $data['error'] ?? $data['message'] ?? $raw ) : $raw;
            return new WP_Error( 'etsy_http_' . $code, 'Etsy (' . $code . '): ' . wp_strip_all_tags( (string) $message ) );
        }
        return is_array( $data ) ? $data : [];
    }

    private function etsy_request_json( $method, $path, $body ) {
        $settings = $this->settings();
        if ( empty( $settings['api_key'] ) || empty( $settings['shared_secret'] ) ) {
            return new WP_Error( 'etsy_credentials', 'Faltan el Keystring o Shared Secret de Etsy.' );
        }
        $token = $this->get_access_token();
        if ( is_wp_error( $token ) ) {
            return $token;
        }
        $response = wp_remote_request( 'https://api.etsy.com' . $path, [
            'method'  => strtoupper( $method ),
            'timeout' => 60,
            'headers' => [
                'x-api-key'     => $settings['api_key'] . ':' . $settings['shared_secret'],
                'Authorization' => 'Bearer ' . $token,
                'Accept'        => 'application/json',
                'Content-Type'  => 'application/json; charset=utf-8',
            ],
            'body' => wp_json_encode( $body ),
        ] );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $raw  = wp_remote_retrieve_body( $response );
        $data = $raw !== '' ? json_decode( $raw, true ) : [];
        if ( $code < 200 || $code >= 300 ) {
            return new WP_Error( 'etsy_http_' . $code, 'Etsy (' . $code . '): ' . wp_strip_all_tags( (string) ( $data['error'] ?? $data['message'] ?? $raw ) ) );
        }
        return is_array( $data ) ? $data : [];
    }

    private function etsy_upload_file( $path, $fields, $binary_path, $field_name, $mime, $filename ) {
        $settings = $this->settings();
        $token = $this->get_access_token();
        if ( is_wp_error( $token ) ) {
            return $token;
        }
        if ( ! file_exists( $binary_path ) || ! is_readable( $binary_path ) ) {
            return new WP_Error( 'file_missing', 'No se puede leer el archivo a subir: ' . basename( $binary_path ) );
        }
        $boundary = '----DrieloEtsy' . wp_generate_password( 24, false, false );
        $eol = "\r\n";
        $body = '';
        foreach ( $fields as $name => $value ) {
            $body .= '--' . $boundary . $eol;
            $body .= 'Content-Disposition: form-data; name="' . $name . '"' . $eol . $eol;
            $body .= (string) $value . $eol;
        }
        $body .= '--' . $boundary . $eol;
        $body .= 'Content-Disposition: form-data; name="' . $field_name . '"; filename="' . sanitize_file_name( $filename ) . '"' . $eol;
        $body .= 'Content-Type: ' . $mime . $eol . $eol;
        $body .= file_get_contents( $binary_path ) . $eol;
        $body .= '--' . $boundary . '--' . $eol;

        $response = wp_remote_post( 'https://api.etsy.com' . $path, [
            'timeout' => 120,
            'headers' => [
                'x-api-key'     => $settings['api_key'] . ':' . $settings['shared_secret'],
                'Authorization' => 'Bearer ' . $token,
                'Accept'        => 'application/json',
                'Content-Type'  => 'multipart/form-data; boundary=' . $boundary,
            ],
            'body' => $body,
        ] );
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        $code = wp_remote_retrieve_response_code( $response );
        $raw  = wp_remote_retrieve_body( $response );
        $data = json_decode( $raw, true );
        if ( $code < 200 || $code >= 300 ) {
            return new WP_Error( 'etsy_upload_' . $code, 'Etsy (' . $code . '): ' . wp_strip_all_tags( (string) ( $data['error'] ?? $data['message'] ?? $raw ) ) );
        }
        return is_array( $data ) ? $data : [];
    }

    private function sync_product( $product_id, bool $overwrite = false ) {
        $product = wc_get_product( $product_id );
        if ( ! $product ) {
            return new WP_Error( 'invalid_product', 'Producto no válido.' );
        }

        $settings = $this->ensure_shop_identity();
        if ( empty( $settings['shop_id'] ) ) {
            return $this->record_error( $product_id, new WP_Error( 'shop_id', 'Falta el Shop ID de Etsy.' ) );
        }

        $taxonomy_id = $this->resolve_taxonomy_id( $product );
        if ( $taxonomy_id <= 0 ) {
            return $this->record_error( $product_id, new WP_Error( 'taxonomy_id', 'No se pudo resolver una categoría de Etsy para este producto.' ) );
        }

        $listing_id  = absint( get_post_meta( $product_id, self::META_LISTING_ID, true ) );
        $is_new      = ! $listing_id;
        $target      = get_post_meta( $product_id, self::META_TARGET_STATE, true ) === 'active' ? 'active' : 'draft';
        $payload     = $this->listing_payload( $product, $taxonomy_id );
        $content_hash = $this->product_content_hash( $product );

        update_post_meta( $product_id, '_drielo_etsy_taxonomy_id', $taxonomy_id );

        if ( $is_new ) {
            $create = $this->etsy_request( 'POST', '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings', $payload );
            if ( is_wp_error( $create ) ) {
                return $this->record_error( $product_id, $create );
            }
            $listing_id = absint( $create['listing_id'] ?? 0 );
            if ( ! $listing_id ) {
                return $this->record_error( $product_id, new WP_Error( 'missing_listing_id', 'Etsy creó la respuesta sin listing_id.' ) );
            }
            $remote_state = sanitize_text_field( $create['state'] ?? 'draft' );
            update_post_meta( $product_id, self::META_LISTING_ID, $listing_id );
            update_post_meta( $product_id, self::META_REMOTE_STATE, $remote_state );
        } elseif ( $overwrite ) {
            $update = $this->etsy_request( 'PATCH', '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ), $payload );
            if ( is_wp_error( $update ) ) {
                return $this->record_error( $product_id, $update );
            }
            $remote_state = sanitize_text_field( $update['state'] ?? ( get_post_meta( $product_id, self::META_REMOTE_STATE, true ) ?: 'draft' ) );
        } else {
            // Safe mode deliberately reads Etsy but does not push managed
            // listing fields back. Manual Etsy edits therefore survive.
            $remote = $this->etsy_request( 'GET', '/v3/application/listings/' . rawurlencode( $listing_id ) );
            if ( is_wp_error( $remote ) ) {
                return $this->record_error( $product_id, $remote );
            }
            $remote_state = sanitize_text_field( $remote['state'] ?? ( get_post_meta( $product_id, self::META_REMOTE_STATE, true ) ?: 'draft' ) );
        }

        if ( ( $is_new || $overwrite ) && $product->get_sku() ) {
            $inventory_result = $this->sync_inventory( $product, $listing_id );
            if ( is_wp_error( $inventory_result ) ) {
                return $this->record_error( $product_id, $inventory_result );
            }
        }

        if ( $is_new || $overwrite ) {
            $asset_hash = $this->product_asset_hash( $product );
            if ( ! empty( $settings['sync_images'] ) ) {
                $image_result = $this->sync_images( $product, $listing_id );
                if ( is_wp_error( $image_result ) ) {
                    return $this->record_error( $product_id, $image_result );
                }
            }
            if ( ! empty( $settings['sync_files'] ) ) {
                $file_result = $this->sync_downloads( $product, $listing_id );
                if ( is_wp_error( $file_result ) ) {
                    return $this->record_error( $product_id, $file_result );
                }
            }
            update_post_meta( $product_id, self::META_ASSET_HASH, $asset_hash );
            update_post_meta( $product_id, self::META_CONTENT_HASH, $content_hash );
        }

        if ( 'active' === $target && 'active' !== $remote_state ) {
            $state_result = $this->etsy_request( 'PATCH', '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ), [ 'state' => 'active', 'type' => 'download' ] );
            if ( is_wp_error( $state_result ) ) {
                return $this->record_error( $product_id, $state_result );
            }
            $remote_state = sanitize_text_field( $state_result['state'] ?? 'active' );
        } elseif ( 'draft' === $target && 'active' === $remote_state ) {
            $state_result = $this->etsy_request( 'PATCH', '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ), [ 'state' => 'inactive', 'type' => 'download' ] );
            if ( is_wp_error( $state_result ) ) {
                return $this->record_error( $product_id, $state_result );
            }
            $remote_state = sanitize_text_field( $state_result['state'] ?? 'inactive' );
        }

        update_post_meta( $product_id, self::META_REMOTE_STATE, $remote_state );
        update_post_meta( $product_id, self::META_LAST_SYNC, current_time( 'mysql' ) );
        delete_post_meta( $product_id, self::META_LAST_ERROR );
        return true;
    }

    private function listing_payload( WC_Product $product, int $taxonomy_id ) {
        $settings    = $this->settings();
        $description = $this->formatted_etsy_description( $product );
        $title       = $this->etsy_title( $product );
        $price       = $this->etsy_price_eur( $product );

        $payload = [
            'quantity'          => (int) $settings['quantity'],
            'title'             => $title,
            'description'       => $description,
            'price'             => number_format( $price, 2, '.', '' ),
            'who_made'          => 'i_did',
            'when_made'         => $settings['when_made'],
            'taxonomy_id'       => $taxonomy_id,
            'is_supply'         => 'true',
            'type'              => 'download',
            'is_customizable'   => 'false',
            'should_auto_renew' => ! empty( $settings['auto_renew'] ) ? 'true' : 'false',
        ];

        if ( ! empty( $settings['sync_tags'] ) ) {
            $tags = $this->etsy_tags( $product );
            if ( $tags ) {
                $payload['tags'] = $tags;
            }
        }

        return $payload;
    }

    private function listing_language(): string {
        $language = strtolower( (string) ( $this->settings()['default_language'] ?? 'en-US' ) );
        return str_starts_with( $language, 'es' ) ? 'es' : 'en';
    }

    private function etsy_title( WC_Product $product ): string {
        $language = $this->listing_language();
        $title = trim( (string) get_post_meta( $product->get_id(), '_drielo_etsy_title_' . $language, true ) );
        if ( '' === $title ) {
            $title = trim( (string) get_post_meta( $product->get_id(), '_drielo_title_' . $language, true ) );
        }
        if ( '' === $title ) {
            $title = $product->get_name();
        }

        $title = trim( wp_strip_all_tags( html_entity_decode( $title, ENT_QUOTES, 'UTF-8' ) ) );
        return function_exists( 'mb_substr' ) ? mb_substr( $title, 0, 140 ) : substr( $title, 0, 140 );
    }

    private function formatted_etsy_description( WC_Product $product ): string {
        $language = $this->listing_language();
        $html = trim( (string) get_post_meta( $product->get_id(), '_drielo_description_' . $language, true ) );
        if ( '' === $html ) {
            $html = $product->get_description() ?: $product->get_short_description();
        }

        $description = $this->html_to_etsy_text( $html );
        if ( '' === $description ) {
            $description = $this->etsy_title( $product );
        }

        $settings = $this->settings();
        if ( ! empty( $settings['ai_disclosure'] ) ) {
            $disclosure = 'es' === $language
                ? "DECLARACIÓN DE IA\nEste diseño se creó con ayuda de un generador de imágenes con IA y después fue preparado, editado y convertido por Drielo en un patrón digital para manualidades."
                : "AI DISCLOSURE\nThis design was created with the assistance of an AI image generator and then prepared, edited and converted by Drielo into a digital craft pattern.";
            $description = rtrim( $description ) . "\n\n" . $disclosure;
        }

        return $description;
    }

    private function html_to_etsy_text( string $html ): string {
        $text = preg_replace( '#<\s*br\s*/?\s*>#i', "\n", $html );
        $text = preg_replace( '#<\s*li\b[^>]*>#i', "\n• ", (string) $text );
        $text = preg_replace( '#</\s*li\s*>#i', "\n", (string) $text );
        $text = preg_replace( '#</\s*(p|div|h[1-6]|ul|ol)\s*>#i', "\n\n", (string) $text );
        $text = preg_replace( '#<\s*h[1-6]\b[^>]*>#i', "\n\n", (string) $text );
        $text = wp_strip_all_tags( (string) $text );
        $text = html_entity_decode( $text, ENT_QUOTES | ENT_HTML5, 'UTF-8' );
        $text = str_replace( [ "\r\n", "\r", "\xC2\xA0" ], [ "\n", "\n", ' ' ], $text );

        $lines = preg_split( '/\n/u', $text );
        $clean = [];
        foreach ( (array) $lines as $line ) {
            $line = trim( preg_replace( '/[ \t]+/u', ' ', (string) $line ) );
            $clean[] = $line;
        }

        $text = implode( "\n", $clean );
        $text = preg_replace( "/\n{3,}/u", "\n\n", $text );
        return trim( (string) $text );
    }

    private function etsy_tags( WC_Product $product ): array {
        $language = $this->listing_language();
        $tags = get_post_meta( $product->get_id(), '_drielo_etsy_tags_' . $language, true );
        if ( ! is_array( $tags ) || ! $tags ) {
            $tags = wp_get_post_terms( $product->get_id(), 'product_tag', [ 'fields' => 'names' ] );
        }
        if ( is_wp_error( $tags ) ) {
            return [];
        }

        $clean = [];
        foreach ( (array) $tags as $tag ) {
            $tag = trim( wp_strip_all_tags( html_entity_decode( (string) $tag, ENT_QUOTES, 'UTF-8' ) ) );
            $tag = function_exists( 'mb_substr' ) ? mb_substr( $tag, 0, 20 ) : substr( $tag, 0, 20 );
            if ( '' !== $tag && ! in_array( $tag, $clean, true ) ) {
                $clean[] = $tag;
            }
            if ( count( $clean ) >= 13 ) {
                break;
            }
        }
        return $clean;
    }

    private function etsy_price_eur( WC_Product $product ): float {
        $raw = (float) $product->get_price( 'edit' );
        if ( $raw <= 0 ) {
            $raw = (float) $product->get_regular_price( 'edit' );
        }
        if ( $raw <= 0 ) {
            $raw = 0.01;
        }

        $rate = function_exists( 'make_store_usd_eur_rate' )
            ? (float) make_store_usd_eur_rate()
            : (float) get_option( 'drielo_usd_eur_rate_fallback', 0.871743 );
        if ( $rate <= 0.5 || $rate >= 1.5 ) {
            $rate = 0.871743;
        }

        return round( max( 0.01, $raw * $rate ), 2 );
    }

    private function product_technique( WC_Product $product ): string {
        $technique = sanitize_key( (string) get_post_meta( $product->get_id(), '_drielo_technique', true ) );
        if ( '' !== $technique ) {
            return $technique;
        }
        $terms = wp_get_post_terms( $product->get_id(), 'pa_technique', [ 'fields' => 'slugs' ] );
        return ! is_wp_error( $terms ) && ! empty( $terms ) ? sanitize_key( (string) $terms[0] ) : '';
    }

    private function resolve_taxonomy_id( WC_Product $product ): int {
        $settings = $this->settings();
        $fallback = absint( $settings['taxonomy_id'] ?? 0 );
        if ( empty( $settings['auto_taxonomy'] ) ) {
            return $fallback;
        }

        $technique = $this->product_technique( $product );
        if ( '' === $technique ) {
            return $fallback;
        }

        $cached_id = absint( get_transient( 'drielo_etsy_taxonomy_' . $technique ) );
        if ( $cached_id > 0 ) {
            return $cached_id;
        }

        $nodes = get_transient( 'drielo_etsy_seller_taxonomy_v1' );
        if ( ! is_array( $nodes ) || ! $nodes ) {
            $response = $this->etsy_request( 'GET', '/v3/application/seller-taxonomy/nodes', [], false );
            if ( is_wp_error( $response ) ) {
                return $fallback;
            }
            $nodes = isset( $response['results'] ) && is_array( $response['results'] ) ? $response['results'] : $response;
            if ( ! is_array( $nodes ) || ! $nodes ) {
                return $fallback;
            }
            set_transient( 'drielo_etsy_seller_taxonomy_v1', $nodes, 12 * HOUR_IN_SECONDS );
        }

        $profiles = [
            'cross-stitch'     => [ 'anchors' => [ 'cross stitch' ], 'boost' => [ 'pattern' => 30, 'needlecraft' => 8, 'sewing' => 3 ] ],
            'c2c-crochet'      => [ 'anchors' => [ 'crochet' ], 'boost' => [ 'pattern' => 30, 'yarn' => 3 ] ],
            'tapestry-crochet' => [ 'anchors' => [ 'crochet' ], 'boost' => [ 'pattern' => 30, 'yarn' => 3 ] ],
            'latch-hook'       => [ 'anchors' => [ 'latch hook', 'rug' ], 'boost' => [ 'pattern' => 30, 'rug' => 10 ] ],
        ];
        if ( ! isset( $profiles[ $technique ] ) ) {
            return $fallback;
        }

        $flat = [];
        $walk = static function( $items, array $trail = [] ) use ( &$walk, &$flat ): void {
            foreach ( (array) $items as $node ) {
                if ( ! is_array( $node ) ) {
                    continue;
                }
                $name = trim( (string) ( $node['name'] ?? '' ) );
                $path = array_merge( $trail, [ $name ] );
                $flat[] = [
                    'id'       => absint( $node['id'] ?? 0 ),
                    'path'     => strtolower( implode( ' > ', array_filter( $path ) ) ),
                    'depth'    => count( $path ),
                    'has_kids' => ! empty( $node['children'] ),
                ];
                if ( ! empty( $node['children'] ) && is_array( $node['children'] ) ) {
                    $walk( $node['children'], $path );
                }
            }
        };
        $walk( $nodes );

        $profile = $profiles[ $technique ];
        $best_id = 0;
        $best_score = -1;
        foreach ( $flat as $node ) {
            if ( empty( $node['id'] ) || false === strpos( $node['path'], 'pattern' ) ) {
                continue;
            }
            $anchor_score = 0;
            foreach ( $profile['anchors'] as $anchor ) {
                if ( false !== strpos( $node['path'], $anchor ) ) {
                    $anchor_score = max( $anchor_score, 100 + strlen( $anchor ) );
                }
            }
            if ( 0 === $anchor_score ) {
                continue;
            }

            $score = $anchor_score + (int) $node['depth'];
            foreach ( $profile['boost'] as $term => $points ) {
                if ( false !== strpos( $node['path'], $term ) ) {
                    $score += (int) $points;
                }
            }
            if ( empty( $node['has_kids'] ) ) {
                $score += 8;
            }
            if ( $score > $best_score ) {
                $best_score = $score;
                $best_id = (int) $node['id'];
            }
        }

        if ( $best_id > 0 ) {
            set_transient( 'drielo_etsy_taxonomy_' . $technique, $best_id, DAY_IN_SECONDS );
            return $best_id;
        }

        return $fallback;
    }

    private function sync_inventory( WC_Product $product, $listing_id ) {
        $settings = $this->settings();
        $price = $this->etsy_price_eur( $product );
        $payload = [
            'products' => [
                [
                    'sku' => (string) $product->get_sku(),
                    'offerings' => [
                        [
                            'quantity'   => (int) $settings['quantity'],
                            'is_enabled' => true,
                            'price'      => (float) number_format( max( 0.01, $price ), 2, '.', '' ),
                        ],
                    ],
                    'property_values' => [],
                ],
            ],
            'price_on_property'    => [],
            'quantity_on_property' => [],
            'sku_on_property'      => [],
        ];
        return $this->etsy_request_json( 'PUT', '/v3/application/listings/' . rawurlencode( $listing_id ) . '/inventory', $payload );
    }

    private function product_content_hash( WC_Product $product ): string {
        $settings = $this->settings();
        $data = [
            'sku'            => (string) $product->get_sku(),
            'title'          => $this->etsy_title( $product ),
            'description'    => $this->formatted_etsy_description( $product ),
            'price_eur'      => number_format( $this->etsy_price_eur( $product ), 2, '.', '' ),
            'tags'           => $this->etsy_tags( $product ),
            'technique'      => $this->product_technique( $product ),
            'quantity'       => (int) $settings['quantity'],
            'language'       => $this->listing_language(),
            'when_made'      => (string) $settings['when_made'],
            'auto_renew'     => ! empty( $settings['auto_renew'] ),
            'ai_disclosure'  => ! empty( $settings['ai_disclosure'] ),
            'auto_taxonomy'  => ! empty( $settings['auto_taxonomy'] ),
        ];
        return hash( 'sha256', wp_json_encode( $data ) );
    }

    private function product_asset_hash( WC_Product $product ) {
        $data = [
            'plugin_version' => self::VERSION,
            'image'          => $product->get_image_id(),
            'gallery'        => $product->get_gallery_image_ids(),
            'downloads'      => [],
        ];

        foreach ( $product->get_downloads() as $download ) {
            $source = $download->get_file();
            $item = [ $download->get_name(), $source ];
            $path = preg_match( '#^https?://#i', $source ) ? $this->local_path_from_url( $source ) : $source;
            if ( $path && is_file( $path ) ) {
                $item[] = (int) filesize( $path );
                $item[] = (int) filemtime( $path );
            }
            $data['downloads'][] = $item;
        }

        return hash( 'sha256', wp_json_encode( $data ) );
    }

    private function sync_images( WC_Product $product, $listing_id ) {
        $settings = $this->settings();
        $ids = array_values( array_filter( array_unique( array_merge( [ $product->get_image_id() ], $product->get_gallery_image_ids() ) ) ) );
        if ( empty( $ids ) ) {
            return new WP_Error( 'no_images', 'El producto no tiene imágenes; Etsy necesita al menos una para publicar.' );
        }

        $rank = 1;
        foreach ( array_slice( $ids, 0, 14 ) as $attachment_id ) {
            $path = get_attached_file( $attachment_id );
            $cleanup = false;
            if ( ! $path || ! file_exists( $path ) ) {
                $url = wp_get_attachment_url( $attachment_id );
                if ( ! $url ) {
                    continue;
                }
                $local = $this->local_path_from_url( $url );
                if ( $local ) {
                    $path = $local;
                } else {
                    $path = $this->download_to_temp( $url );
                    if ( is_wp_error( $path ) ) {
                        return $path;
                    }
                    $cleanup = true;
                }
            }

            $mime = get_post_mime_type( $attachment_id ) ?: 'image/jpeg';
            $name = basename( $path );
            $result = $this->etsy_upload_file(
                '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ) . '/images',
                [ 'rank' => $rank, 'overwrite' => 'true', 'is_watermarked' => 'false', 'alt_text' => $product->get_name() ],
                $path,
                'image',
                $mime,
                $name
            );
            if ( $cleanup ) {
                @unlink( $path );
            }
            if ( is_wp_error( $result ) ) {
                return $result;
            }
            $rank++;
        }

        if ( ! empty( $settings['sync_pdf_previews'] ) && $rank <= 20 && ! $this->has_generated_pdf_gallery( $product->get_gallery_image_ids() ) ) {
            foreach ( $this->generate_pdf_preview_images( $product ) as $preview ) {
                if ( $rank > 20 ) {
                    break;
                }
                $result = $this->etsy_upload_file(
                    '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ) . '/images',
                    [ 'rank' => $rank, 'overwrite' => 'true', 'is_watermarked' => 'false', 'alt_text' => $preview['alt'] ],
                    $preview['path'],
                    'image',
                    'image/jpeg',
                    $preview['name']
                );
                @unlink( $preview['path'] );
                if ( is_wp_error( $result ) ) {
                    return $result;
                }
                $rank++;
            }
        }

        return true;
    }

    private function has_generated_pdf_gallery( array $attachment_ids ): bool {
        foreach ( $attachment_ids as $attachment_id ) {
            $source = (string) get_post_meta( absint( $attachment_id ), '_drielo_source_asset', true );
            if ( false !== strpos( basename( $source ), '-etsy-' ) ) {
                return true;
            }
        }
        return false;
    }

    private function generate_pdf_preview_images( WC_Product $product ): array {
        if ( ! class_exists( 'Imagick' ) ) {
            return [];
        }

        $pdf = $this->local_product_pdf( $product );
        if ( '' === $pdf ) {
            return [];
        }

        $specs = [
            [ 'page' => 1,  'slug' => 'finished-design', 'alt' => $product->get_name() . ' finished design preview', 'partial' => false ],
            [ 'page' => 2,  'slug' => 'pattern-facts',   'alt' => $product->get_name() . ' pattern facts', 'partial' => false ],
            [ 'page' => 3,  'slug' => 'colour-key',     'alt' => $product->get_name() . ' colour key preview', 'partial' => false ],
            [ 'page' => 7,  'slug' => 'colour-chart',   'alt' => $product->get_name() . ' partial colour chart preview', 'partial' => true ],
            [ 'page' => 11, 'slug' => 'symbol-chart',   'alt' => $product->get_name() . ' partial black and white symbol chart preview', 'partial' => true ],
            [ 'page' => 15, 'slug' => 'print-guide',    'alt' => $product->get_name() . ' print and craft guide', 'partial' => false ],
        ];

        $previews = [];
        foreach ( $specs as $spec ) {
            $image = null;
            try {
                $image = new Imagick();
                $image->setResolution( 130, 130 );
                $image->readImage( $pdf . '[' . (int) $spec['page'] . ']' );
                $image->setIteratorIndex( 0 );
                $image->setImageBackgroundColor( 'white' );
                if ( defined( 'Imagick::ALPHACHANNEL_REMOVE' ) ) {
                    $image->setImageAlphaChannel( Imagick::ALPHACHANNEL_REMOVE );
                }
                $image = $image->mergeImageLayers( Imagick::LAYERMETHOD_FLATTEN );

                if ( ! empty( $spec['partial'] ) ) {
                    $width  = (int) $image->getImageWidth();
                    $height = (int) $image->getImageHeight();
                    $crop_w = max( 1, (int) round( $width * 0.86 ) );
                    $crop_h = max( 1, (int) round( $height * 0.56 ) );
                    $x = max( 0, (int) floor( ( $width - $crop_w ) / 2 ) );
                    $y = max( 0, (int) floor( $height * 0.08 ) );
                    $image->cropImage( $crop_w, min( $crop_h, $height - $y ), $x, $y );
                    $image->setImagePage( 0, 0, 0, 0 );
                }

                $image->setImageFormat( 'jpeg' );
                $image->setImageCompressionQuality( 86 );
                $image->thumbnailImage( 1600, 2000, true, true );

                $tmp = wp_tempnam( 'drielo-etsy-' . $spec['slug'] );
                if ( ! $tmp ) {
                    $image->clear();
                    continue;
                }
                $jpg = $tmp . '.jpg';
                @unlink( $tmp );
                if ( ! $image->writeImage( $jpg ) || ! is_file( $jpg ) || filesize( $jpg ) < 10000 ) {
                    @unlink( $jpg );
                    $image->clear();
                    continue;
                }

                $previews[] = [
                    'path' => $jpg,
                    'name' => sanitize_file_name( $product->get_sku() . '-' . $spec['slug'] . '.jpg' ),
                    'alt'  => (string) $spec['alt'],
                ];
                $image->clear();
                $image->destroy();
            } catch ( Throwable $e ) {
                if ( $image instanceof Imagick ) {
                    $image->clear();
                    $image->destroy();
                }
                continue;
            }
        }

        return $previews;
    }

    private function local_product_pdf( WC_Product $product ): string {
        foreach ( $product->get_downloads() as $download ) {
            $source = (string) $download->get_file();
            $path = $source;
            if ( preg_match( '#^https?://#i', $source ) ) {
                $path = $this->local_path_from_url( $source );
            } elseif ( ! is_file( $path ) ) {
                $upload_dir = wp_upload_dir();
                $candidate = trailingslashit( $upload_dir['basedir'] ) . ltrim( $source, '/\\' );
                $path = is_file( $candidate ) ? $candidate : '';
            }
            if ( $path && is_file( $path ) && 'pdf' === strtolower( (string) pathinfo( $path, PATHINFO_EXTENSION ) ) ) {
                return $path;
            }
        }
        return '';
    }

    private function sync_downloads( WC_Product $product, $listing_id ) {
        $settings = $this->settings();
        $downloads = $product->get_downloads();
        $old_files = $this->etsy_request( 'GET', '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ) . '/files' );
        if ( is_wp_error( $old_files ) ) {
            $old_files = [ 'results' => [] ];
        }
        if ( empty( $downloads ) ) {
            return new WP_Error( 'no_downloads', 'El producto no tiene archivos descargables asociados en WooCommerce.' );
        }
        $count = 0;
        foreach ( $downloads as $download ) {
            if ( $count >= 5 ) {
                break;
            }
            $source = $download->get_file();
            $path = $source;
            $cleanup = false;
            if ( preg_match( '#^https?://#i', $source ) ) {
                $local_path = $this->local_path_from_url( $source );
                if ( $local_path ) {
                    $path = $local_path;
                } else {
                    $path = $this->download_to_temp( $source );
                    if ( is_wp_error( $path ) ) {
                        return $path;
                    }
                    $cleanup = true;
                }
            } elseif ( ! file_exists( $path ) ) {
                $upload_dir = wp_upload_dir();
                $candidate = trailingslashit( $upload_dir['basedir'] ) . ltrim( $source, '/\\' );
                if ( file_exists( $candidate ) ) {
                    $path = $candidate;
                }
            }
            if ( ! file_exists( $path ) ) {
                return new WP_Error( 'download_missing', 'No se encuentra el archivo descargable: ' . basename( $source ) );
            }
            $filename = $download->get_name();
            if ( ! preg_match( '/\.[A-Za-z0-9]{2,5}$/', $filename ) ) {
                $filename = basename( parse_url( $source, PHP_URL_PATH ) ?: $path );
            }
            $mime = function_exists( 'mime_content_type' ) ? mime_content_type( $path ) : 'application/octet-stream';
            $result = $this->etsy_upload_file(
                '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ) . '/files',
                [ 'name' => sanitize_file_name( $filename ), 'rank' => $count + 1 ],
                $path,
                'file',
                $mime ?: 'application/octet-stream',
                $filename
            );
            if ( $cleanup ) {
                @unlink( $path );
            }
            if ( is_wp_error( $result ) ) {
                return $result;
            }
            $count++;
        }
        if ( 0 === $count ) {
            return new WP_Error( 'no_valid_downloads', 'No se encontró ningún archivo válido para subir a Etsy.' );
        }
        if ( ! empty( $old_files['results'] ) ) {
            foreach ( $old_files['results'] as $old_file ) {
                $old_id = absint( $old_file['listing_file_id'] ?? 0 );
                if ( $old_id ) {
                    $this->etsy_request( 'DELETE', '/v3/application/shops/' . rawurlencode( $settings['shop_id'] ) . '/listings/' . rawurlencode( $listing_id ) . '/files/' . rawurlencode( $old_id ) );
                }
            }
        }
        return true;
    }

    private function local_path_from_url( $url ) {
        $upload_dir = wp_upload_dir();
        if ( ! empty( $upload_dir['error'] ) || empty( $upload_dir['baseurl'] ) || empty( $upload_dir['basedir'] ) ) {
            return '';
        }

        $url_parts  = wp_parse_url( $url );
        $base_parts = wp_parse_url( $upload_dir['baseurl'] );
        if ( empty( $url_parts['path'] ) || empty( $base_parts['path'] ) ) {
            return '';
        }

        $url_host  = strtolower( (string) ( $url_parts['host'] ?? '' ) );
        $base_host = strtolower( (string) ( $base_parts['host'] ?? '' ) );
        if ( $url_host && $base_host && $url_host !== $base_host ) {
            return '';
        }

        $url_path  = rawurldecode( (string) $url_parts['path'] );
        $base_path = untrailingslashit( rawurldecode( (string) $base_parts['path'] ) );
        if ( $url_path !== $base_path && 0 !== strpos( $url_path, $base_path . '/' ) ) {
            return '';
        }

        $relative = ltrim( substr( $url_path, strlen( $base_path ) ), "/\\");
        if ( '' === $relative ) {
            return '';
        }

        $candidate      = trailingslashit( $upload_dir['basedir'] ) . $relative;
        $base_real      = realpath( $upload_dir['basedir'] );
        $candidate_real = realpath( $candidate );
        if ( false === $base_real || false === $candidate_real ) {
            return '';
        }

        $base_real      = trailingslashit( wp_normalize_path( $base_real ) );
        $candidate_real = wp_normalize_path( $candidate_real );
        if ( 0 !== strpos( $candidate_real, $base_real ) || ! is_file( $candidate_real ) || ! is_readable( $candidate_real ) ) {
            return '';
        }

        return $candidate_real;
    }

    private function download_to_temp( $url ) {
        require_once ABSPATH . 'wp-admin/includes/file.php';
        $tmp = download_url( $url, 120 );
        if ( is_wp_error( $tmp ) ) {
            return new WP_Error( 'download_failed', 'No se pudo obtener el archivo desde WooCommerce: ' . $tmp->get_error_message() );
        }
        return $tmp;
    }

    private function record_error( $product_id, WP_Error $error ) {
        update_post_meta( $product_id, self::META_LAST_ERROR, $error->get_error_message() );
        update_post_meta( $product_id, self::META_LAST_SYNC, current_time( 'mysql' ) );
        return $error;
    }
}

add_action( 'plugins_loaded', static function() {
    if ( class_exists( 'WooCommerce' ) ) {
        Drielo_Etsy_Sync::instance();
    } else {
        add_action( 'admin_notices', static function() {
            echo '<div class="notice notice-error"><p><strong>Drielo Etsy Sync:</strong> requiere WooCommerce activo.</p></div>';
        } );
    }
} );
