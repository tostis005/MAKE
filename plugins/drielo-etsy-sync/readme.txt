=== Drielo Etsy Sync ===
Contributors: Drielo
Requires at least: 6.4
Requires PHP: 8.0
Requires Plugins: woocommerce
Stable tag: 1.3.0

Panel central para seleccionar y sincronizar productos WooCommerce con Etsy mediante Etsy Open API v3.

== Funciones ==
* Menú Drielo en WP Admin.
* Tabla central de productos con selección, objetivo Borrador/Publicado, estado Etsy, PDF, última sincronización y listing ID.
* OAuth 2.0 PKCE con renovación automática de token.
* Creación y actualización de listings digitales.
* Precio EUR sincronizado con la misma conversión USD/EUR usada por Drielo.
* Descripciones de Etsy con párrafos, títulos y viñetas legibles.
* Títulos y tags específicos de Etsy cuando están disponibles.
* Categoría Etsy resuelta automáticamente según la técnica del patrón.
* Configuración automática como descarga digital y renovación automática.
* Declaración de uso de IA añadida automáticamente a la descripción.
* Imagen destacada y galería de WooCommerce.
* Subida de hasta 5 archivos descargables por listing.
* Registro de errores por producto.

== Instalación ==
1. Instalar y activar WooCommerce.
2. Desplegar el plugin desde el repositorio Drielo.
3. Abrir Drielo > Configuración.
4. Crear una app en Etsy Developers e introducir Keystring y Shared Secret.
5. Registrar como Redirect URI la Callback URL mostrada por el plugin.
6. Guardar y pulsar Conectar con Etsy.
7. Mantener activada la categoría automática; el Taxonomy ID manual queda como respaldo.
8. Ir a Drielo > Productos Etsy, marcar los productos y sincronizarlos.

== Nota ==
Etsy no permite devolver un listing ya publicado al estado draft. Si un listing activo se cambia al objetivo Borrador, el plugin lo deja inactive.

== Changelog ==

= 1.3.0 =
* Procesa las sincronizaciones en segundo plano, un producto por tarea, para evitar timeouts y errores críticos al seleccionar varios artículos.
* Etsy recibe exclusivamente la imagen destacada y la galería que ya existen en WooCommerce.
* El sincronizador deja de renderizar o extraer imágenes desde los PDFs.
* El importador deja de generar automáticamente previews de Etsy desde PDFs.
* Se eliminan del catálogo las galerías PDF heredadas creadas por la versión anterior.


= 1.2.0 =
* Añade filtros por colección y tipo de trabajo en la tabla de sincronización.
* Muestra una miniatura más grande para identificar rápidamente cada producto.
* La sincronización normal pasa a ser segura: no sobrescribe datos ni assets de listings ya existentes.
* Añade una acción separada “Sobrescribir seleccionados desde Drielo”, limitada a filas marcadas y con confirmación.
* Muestra si cada producto es nuevo, está protegido, tiene cambios locales pendientes o está al día.


= 1.1.0 =
* Sincroniza el precio EUR de Drielo también en inventario.
* Conserva párrafos, títulos y viñetas en la descripción de Etsy.
* Usa títulos y tags específicos de Etsy cuando existen.
* Resuelve automáticamente la taxonomía de Etsy según la técnica del patrón.
* Configura descarga digital, supply creativo, no personalizable y renovación automática.
* Añade automáticamente la declaración de uso de IA.
* Genera previews seguros del PDF sin exponer los gráficos completos.

= 1.0.3 =
* Corrige la sincronización de PDFs protegidos usando el archivo local de WordPress cuando la URL apunta a uploads.

= 1.0.2 =
* Versión base del sincronizador Drielo/Etsy.
