=== Drielo Etsy Sync ===
Contributors: Drielo
Requires at least: 6.4
Requires PHP: 8.0
Requires Plugins: woocommerce
Stable tag: 1.0.0

Panel central para seleccionar y sincronizar productos WooCommerce con Etsy mediante Etsy Open API v3.

== Funciones ==
* Menú Drielo en WP Admin.
* Tabla central de productos con selección, objetivo Borrador/Publicado, estado Etsy, PDF, última sincronización y listing ID.
* OAuth 2.0 PKCE con renovación automática de token.
* Creación/actualización de listings digitales.
* Sincronización de título, descripción, precio, SKU y tags.
* Subida de imagen destacada + galería.
* Subida de hasta 5 archivos descargables por listing.
* Registro de errores por producto.

== Instalación ==
1. Instalar y activar WooCommerce.
2. Subir e instalar este ZIP desde Plugins > Añadir plugin > Subir plugin.
3. Abrir Drielo > Configuración.
4. Crear una app en Etsy Developers e introducir Keystring y Shared Secret.
5. Registrar como Redirect URI la Callback URL mostrada por el plugin.
6. Guardar y pulsar Conectar con Etsy.
7. Introducir un Taxonomy ID válido para la categoría de patrones.
8. Ir a Drielo > Productos Etsy, marcar los productos y sincronizarlos.

== Nota ==
Etsy no permite devolver un listing ya publicado al estado draft. Si un listing activo se cambia al objetivo Borrador, el plugin lo deja inactive.
\n\n= 1.0.3 =\n* Corrige la sincronizaci󮠤e PDFs protegidos: usa el archivo local de WordPress cuando la URL de WooCommerce apunta a uploads y conserva la descarga HTTP como fallback.\n