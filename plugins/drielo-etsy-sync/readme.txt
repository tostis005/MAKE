=== Drielo Etsy Sync ===
Contributors: Drielo
Requires at least: 6.4
Requires PHP: 8.0
Requires Plugins: woocommerce
Stable tag: 1.4.7

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
* Estado global persistente de cada ejecución, progreso en tiempo real y registro por producto.

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

= 1.4.7 =
* Mantiene C2C/Tapestry dentro de la taxonomía de patrones de crochet, evitando la categoría genérica Crochet que no admite Craft type.
* Conserva Craft type = Crochet/Ganchillo y la sección C2C Crochet.

= 1.4.6 =
* Envía tanto value_ids como values al atributo Craft type de Etsy, requerido para guardar Crochet/Ganchillo correctamente.

= 1.4.5 =
* C2C Crochet y Tapestry Crochet priorizan la categoría Etsy Crochet/Ganchillo.
* Sincroniza el atributo requerido Craft type con Crochet (Ganchillo en la interfaz española).
* C2C Crochet se asigna automáticamente a la sección de tienda “C2C Crochet”.
* La sincronización segura puede corregir categoría, tipo de artesanía y sección sin sobrescribir imágenes, PDFs ni descripción.

= 1.4.4 =
* Usa el precio de Drielo como objetivo visible en Etsy y reduce automáticamente el precio base enviado para compensar IVA/impuestos y la conversión que Etsy muestra al comprador.
* Añade un factor de calibración configurable (drielo_etsy_visible_price_factor), calibrado con la relación observada 5,99 USD -> 7,56 USD.
* Mantiene el tipo USD/EUR dinámico de Drielo como base del cálculo.

= 1.4.3 =
* Prioriza el nodo exacto Cross Stitch de Etsy (taxonomy_id 87).
* Asigna la sección de tienda Cross Stitch al final de la sincronización, cuando el listing ya tiene inventario, imágenes y PDF.
* Lee las secciones de tienda con el endpoint público de Etsy y elimina la dependencia del permiso shops_r para esta asignación.

= 1.4.2 =
* Corrige el estado de lotes para que una ejecución nueva no herede el batch_id de una anterior.
* Detecta listings eliminados/removidos en Etsy y los vuelve a crear automáticamente.
* Al sobrescribir archivos digitales, elimina primero los adjuntos antiguos y después sube los actuales para evitar el error “file already attached”.
* Usa el campo shop_section_id al actualizar la sección de tienda del listing.

= 1.4.1 =
* Prioriza la taxonomía específica de Cross Stitch / Punto de cruz al resolver la categoría de Etsy.
* Busca la sección de tienda “Cross Stitch” y la asigna automáticamente a los listings de punto de cruz.
* Solicita el permiso shops_r y añade un botón para actualizar permisos de Etsy sin desconectar primero.
* Muestra un aviso no bloqueante si no puede localizar o asignar la sección de tienda.

= 1.4.0 =
* Añade un panel persistente para saber si una sincronización está en cola, en curso, terminada, terminada con errores o sin actividad.
* Muestra progreso global y contadores de productos en cola, procesando, correctos y con error.
* Añade un registro consultable por producto con hora, detalle del resultado y listing ID.
* Actualiza el estado automáticamente mientras la ejecución está activa y conserva el resultado al volver al panel.
* Evita lanzar una segunda sincronización mientras la anterior sigue activa.


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
