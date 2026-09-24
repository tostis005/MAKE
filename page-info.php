<?php
$key = make_info_page_key();
if ( '' === $key ) {
    status_header( 404 );
    get_template_part( '404' );
    return;
}
get_header();

$email = make_contact_recipient();
$is_en = make_is_english();
$sent  = isset( $_GET['sent'] ) && '1' === sanitize_text_field( (string) wp_unslash( $_GET['sent'] ) );
$error = isset( $_GET['contact_error'] ) ? sanitize_key( (string) wp_unslash( $_GET['contact_error'] ) ) : '';

$intro = array(
    'contact' => $is_en
        ? 'Questions about an order, a download or one of our patterns? Send us a message and we will get back to you by email.'
        : '¿Tienes alguna duda sobre un pedido, una descarga o uno de nuestros patrones? Escríbenos y te responderemos por correo.',
    'privacy' => $is_en
        ? 'How Drielo handles personal data when you browse the site, buy a digital pattern or contact us.'
        : 'Cómo trata Drielo los datos personales cuando navegas por la web, compras un patrón digital o nos escribes.',
    'refunds' => $is_en
        ? 'Clear rules for digital downloads, technical problems and refund requests.'
        : 'Reglas claras para descargas digitales, incidencias técnicas y solicitudes de reembolso.',
    'terms' => $is_en
        ? 'The basic conditions that apply when using Drielo and purchasing our digital patterns.'
        : 'Las condiciones básicas aplicables al uso de Drielo y a la compra de nuestros patrones digitales.',
);
?>
<section class="info-page">
  <div class="container">
    <header class="info-hero">
      <span class="section-kicker"><?php echo esc_html( $is_en ? 'Drielo · information' : 'Drielo · información' ); ?></span>
      <h1><?php echo esc_html( make_info_page_title( $key ) ); ?></h1>
      <p><?php echo esc_html( $intro[ $key ] ); ?></p>
    </header>

    <?php if ( 'contact' === $key ) : ?>
      <div class="info-shell info-shell--contact">
        <section class="info-card">
          <?php if ( $sent ) : ?>
            <p class="contact-alert contact-alert--success"><?php echo esc_html( $is_en ? 'Message received. Thank you — we will reply by email as soon as possible.' : 'Mensaje recibido. Gracias — te responderemos por correo lo antes posible.' ); ?></p>
          <?php elseif ( $error ) : ?>
            <p class="contact-alert contact-alert--error"><?php echo esc_html( 'rate' === $error ? ( $is_en ? 'Too many attempts. Please try again later.' : 'Se han realizado demasiados intentos. Prueba de nuevo más tarde.' ) : ( $is_en ? 'Please check the form and try again.' : 'Revisa los datos del formulario y vuelve a intentarlo.' ) ); ?></p>
          <?php endif; ?>

          <form class="contact-form" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
            <input type="hidden" name="action" value="make_contact">
            <input type="hidden" name="contact_language" value="<?php echo esc_attr( $is_en ? 'en' : 'es' ); ?>">
            <input type="hidden" name="started_at" value="<?php echo esc_attr( (string) time() ); ?>">
            <?php wp_nonce_field( 'make_contact_form', 'make_contact_nonce' ); ?>

            <div class="make-contact-trap" aria-hidden="true">
              <label for="company"><?php echo esc_html( $is_en ? 'Company' : 'Empresa' ); ?></label>
              <input id="company" type="text" name="company" value="" tabindex="-1" autocomplete="off">
            </div>

            <div class="contact-field">
              <label for="contact_name"><?php echo esc_html( $is_en ? 'Name' : 'Nombre' ); ?></label>
              <input id="contact_name" name="contact_name" type="text" autocomplete="name" maxlength="120" required>
            </div>

            <div class="contact-field">
              <label for="contact_email"><?php echo esc_html( $is_en ? 'Email' : 'Correo electrónico' ); ?></label>
              <input id="contact_email" name="contact_email" type="email" autocomplete="email" maxlength="190" required>
            </div>

            <div class="contact-field">
              <label for="contact_message"><?php echo esc_html( $is_en ? 'Message' : 'Mensaje' ); ?></label>
              <textarea id="contact_message" name="contact_message" minlength="10" maxlength="5000" required></textarea>
            </div>

            <label class="contact-consent">
              <input type="checkbox" name="privacy_accept" value="1" required>
              <span><?php echo wp_kses_post( $is_en
                  ? 'I have read the <a href="' . esc_url( make_privacy_url( 'en' ) ) . '">privacy policy</a> and agree that my data is used to respond to this request.'
                  : 'He leído la <a href="' . esc_url( make_privacy_url( 'es' ) ) . '">política de privacidad</a> y acepto que mis datos se utilicen para responder a esta solicitud.' ); ?></span>
            </label>

            <button class="button button-primary contact-submit" type="submit"><?php echo esc_html( $is_en ? 'Send message' : 'Enviar mensaje' ); ?></button>
          </form>
        </section>
      </div>

    <?php else : ?>
      <div class="info-shell">
        <article class="info-card legal-copy">
          <?php if ( 'privacy' === $key ) : ?>
            <?php if ( $is_en ) : ?>
              <h2>1. Who is responsible for your data?</h2>
              <p>Drielo is responsible for the personal data processed through this website. For privacy questions or requests, contact <a href="mailto:<?php echo esc_attr( $email ); ?>"><?php echo esc_html( antispambot( $email ) ); ?></a>.</p>
              <h2>2. Data we may process</h2>
              <p>Depending on how you use the site, we may process identification and contact data, order and billing information, messages you send us, and technical information needed for security and site operation.</p>
              <h2>3. Why we use it</h2>
              <ul><li>To process purchases, deliver digital files and provide customer support.</li><li>To respond to contact requests.</li><li>To comply with accounting, tax or other legal obligations that apply to the store.</li><li>To prevent abuse, fraud and security incidents.</li></ul>
              <h2>4. Legal bases</h2>
              <p>Processing may be based on performance of a contract, compliance with a legal obligation, your consent where required, or Drielo's legitimate interests in operating and protecting the service, depending on the purpose.</p>
              <h2>5. Service providers and payments</h2>
              <p>Data may be handled by providers that are necessary to run the store, such as hosting, email, WordPress/WooCommerce infrastructure and the payment provider chosen at checkout. Payment credentials are handled according to the payment provider's own systems and policies.</p>
              <h2>6. International transfers</h2>
              <p>Some providers may process data outside your country. Where data protection law requires safeguards for those transfers, the applicable contractual or legal mechanisms should be used.</p>
              <h2>7. Retention</h2>
              <p>We keep data only for as long as needed for the purpose for which it was collected and for any mandatory legal retention periods. Contact messages are reviewed and may be deleted when they are no longer needed.</p>
              <h2>8. Your rights</h2>
              <p>Where applicable, you may request access, correction, deletion, restriction, portability or objection, and you may withdraw consent where processing is based on consent. You may also lodge a complaint with the competent data protection authority.</p>
              <h2>9. Cookies and security</h2>
              <p>The site may use technical cookies that are necessary for functions such as the cart, checkout, language and session management. If non-essential cookies are activated, they should be handled using the consent required by applicable law. We apply reasonable technical and organisational measures to protect personal data.</p>
              <h2>10. Updates</h2>
              <p>This policy may be updated when the services, providers or legal requirements change. Last updated: 24 September 2026.</p>
            <?php else : ?>
              <h2>1. Responsable del tratamiento</h2>
              <p>Drielo es responsable de los datos personales tratados a través de esta web. Para cualquier consulta o ejercicio de derechos puedes escribir a <a href="mailto:<?php echo esc_attr( $email ); ?>"><?php echo esc_html( antispambot( $email ) ); ?></a>.</p>
              <h2>2. Datos que podemos tratar</h2>
              <p>Según cómo utilices la web, podemos tratar datos identificativos y de contacto, información de pedidos y facturación, los mensajes que nos envíes y datos técnicos necesarios para la seguridad y el funcionamiento del sitio.</p>
              <h2>3. Para qué utilizamos los datos</h2>
              <ul><li>Gestionar compras, entregar archivos digitales y prestar atención al cliente.</li><li>Responder a consultas enviadas mediante el formulario de contacto.</li><li>Cumplir obligaciones contables, fiscales u otras obligaciones legales aplicables a la tienda.</li><li>Prevenir abusos, fraude e incidentes de seguridad.</li></ul>
              <h2>4. Bases jurídicas</h2>
              <p>Según la finalidad, el tratamiento puede basarse en la ejecución de un contrato, el cumplimiento de una obligación legal, tu consentimiento cuando sea necesario o el interés legítimo de Drielo en operar y proteger el servicio.</p>
              <h2>5. Proveedores y pagos</h2>
              <p>Los datos pueden ser tratados por proveedores necesarios para operar la tienda, como alojamiento, correo, la infraestructura de WordPress/WooCommerce y el proveedor de pago elegido durante la compra. Los datos de pago se gestionan conforme a los sistemas y políticas del proveedor correspondiente.</p>
              <h2>6. Transferencias internacionales</h2>
              <p>Algunos proveedores pueden tratar datos fuera de tu país. Cuando la normativa de protección de datos exija garantías para esas transferencias, deberán utilizarse los mecanismos contractuales o legales aplicables.</p>
              <h2>7. Conservación</h2>
              <p>Conservamos los datos únicamente durante el tiempo necesario para la finalidad para la que se recogieron y durante los plazos legales obligatorios que correspondan. Los mensajes de contacto se revisan y pueden eliminarse cuando dejan de ser necesarios.</p>
              <h2>8. Tus derechos</h2>
              <p>Cuando resulte aplicable, puedes solicitar acceso, rectificación, supresión, limitación, portabilidad u oposición, y retirar tu consentimiento cuando el tratamiento se base en él. También puedes presentar una reclamación ante la autoridad de protección de datos competente.</p>
              <h2>9. Cookies y seguridad</h2>
              <p>La web puede utilizar cookies técnicas necesarias para funciones como el carrito, el checkout, el idioma y la gestión de sesión. Si se activan cookies no esenciales, deberán gestionarse con el consentimiento exigido por la normativa aplicable. Aplicamos medidas técnicas y organizativas razonables para proteger los datos personales.</p>
              <h2>10. Actualizaciones</h2>
              <p>Esta política puede actualizarse cuando cambien los servicios, proveedores o requisitos legales. Última actualización: 24 de septiembre de 2026.</p>
            <?php endif; ?>

          <?php elseif ( 'refunds' === $key ) : ?>
            <?php if ( $is_en ) : ?>
              <h2>Digital products</h2>
              <p>Drielo sells downloadable digital patterns. No physical item is shipped unless a product page expressly says otherwise.</p>
              <h2>Right of withdrawal</h2>
              <p>If applicable consumer law gives you a withdrawal right before digital delivery starts, that right remains available under the conditions required by law. Where the law allows the withdrawal right to end once supply of digital content begins, Drielo asks for your prior express consent to immediate access and acknowledgement of the relevant consequence before completing checkout.</p>
              <h2>When we will help or refund</h2>
              <p>Please contact us if a file is corrupted, materially different from the purchased product, cannot be accessed because of a problem on our side, or you were charged twice for the same order. We will first try to correct or replace the file; where that does not resolve the issue or the law requires it, a refund may be issued.</p>
              <h2>Change of mind</h2>
              <p>After a valid digital file has been supplied and the applicable withdrawal right has ended, we generally do not refund for a change of mind, selecting the wrong technique, or not having the materials or software needed to use the pattern. Mandatory consumer rights always prevail.</p>
              <h2>How to request help</h2>
              <p>Use the <a href="<?php echo esc_url( make_contact_url( 'en' ) ); ?>">contact form</a> and include the email used for the order and, if available, the order number.</p>
            <?php else : ?>
              <h2>Productos digitales</h2>
              <p>Drielo vende patrones digitales descargables. No se envía ningún producto físico salvo que la ficha del producto indique expresamente lo contrario.</p>
              <h2>Derecho de desistimiento</h2>
              <p>Si la normativa de consumo aplicable te reconoce un derecho de desistimiento antes de que comience la entrega digital, dicho derecho se mantiene en las condiciones previstas por la ley. Cuando la normativa permita que el derecho termine al comenzar el suministro del contenido digital, Drielo solicita antes de finalizar la compra tu consentimiento expreso al acceso inmediato y el reconocimiento de la consecuencia correspondiente.</p>
              <h2>Cuándo te ayudaremos o reembolsaremos</h2>
              <p>Escríbenos si el archivo está dañado, no corresponde materialmente con el producto comprado, no puede descargarse por un problema atribuible a Drielo o se ha producido un cobro duplicado del mismo pedido. Primero intentaremos corregir o sustituir el archivo; si eso no resuelve la incidencia o la ley lo exige, podrá realizarse un reembolso.</p>
              <h2>Cambio de opinión</h2>
              <p>Una vez suministrado correctamente el archivo digital y finalizado, cuando corresponda, el derecho de desistimiento aplicable, por regla general no se realizan reembolsos por cambio de opinión, por haber elegido una técnica distinta o por no disponer de los materiales o programas necesarios para utilizar el patrón. Los derechos imperativos del consumidor prevalecen siempre.</p>
              <h2>Cómo pedir ayuda</h2>
              <p>Utiliza el <a href="<?php echo esc_url( make_contact_url( 'es' ) ); ?>">formulario de contacto</a> e indica el correo utilizado en el pedido y, si lo tienes, el número de pedido.</p>
            <?php endif; ?>

          <?php elseif ( 'terms' === $key ) : ?>
            <?php if ( $is_en ) : ?>
              <h2>1. About Drielo</h2>
              <p>Drielo is an online store for digital craft patterns. These terms apply to use of the site and purchases made through it.</p>
              <h2>2. Digital delivery</h2>
              <p>Unless a product page says otherwise, products are digital downloads and no physical item will be sent. Access is provided using the download method shown after purchase or in your account/order communications.</p>
              <h2>3. Licence and intellectual property</h2>
              <p>Buying a pattern grants a personal, non-exclusive and non-transferable licence to use that digital file. You may make finished pieces for personal use or gifts. Commercial use of finished pieces requires express permission or a product-specific commercial licence. The pattern file, charts, graphics and instructions may not be copied, shared, uploaded, redistributed or resold.</p>
              <h2>4. Orders and prices</h2>
              <p>Prices and currencies are shown before checkout. Any taxes or payment conditions that apply to an order are displayed or calculated through the checkout process where required.</p>
              <h2>5. Customer responsibility</h2>
              <p>Please review the technique, dimensions, materials and file information on the product page before purchase and keep your order details secure.</p>
              <h2>6. Problems with an order</h2>
              <p>If a download or order has a technical problem, contact us so we can investigate. The <a href="<?php echo esc_url( make_refund_policy_url( 'en' ) ); ?>">refund policy</a> explains how digital-product issues are handled.</p>
              <h2>7. Liability and mandatory rights</h2>
              <p>Nothing in these terms excludes rights or remedies that cannot legally be excluded. Drielo is not responsible for failures caused by circumstances outside its reasonable control, subject always to mandatory law.</p>
              <h2>8. Changes</h2>
              <p>These terms may be updated for future use of the site and future purchases. The terms applicable to an order are those in force when the order is placed, subject to mandatory law.</p>
            <?php else : ?>
              <h2>1. Sobre Drielo</h2>
              <p>Drielo es una tienda online de patrones digitales para labores. Estas condiciones se aplican al uso de la web y a las compras realizadas a través de ella.</p>
              <h2>2. Entrega digital</h2>
              <p>Salvo que la ficha del producto indique lo contrario, los productos son descargas digitales y no se enviará ningún artículo físico. El acceso se facilita mediante el sistema de descarga mostrado tras la compra o en las comunicaciones del pedido y de tu cuenta.</p>
              <h2>3. Licencia y propiedad intelectual</h2>
              <p>La compra de un patrón concede una licencia personal, no exclusiva e intransferible para utilizar ese archivo digital. Puedes realizar piezas terminadas para uso personal o como regalo. El uso comercial de piezas terminadas requiere autorización expresa o una licencia comercial específica del producto. El archivo del patrón, gráficos, esquemas e instrucciones no pueden copiarse, compartirse, subirse, redistribuirse ni revenderse.</p>
              <h2>4. Pedidos y precios</h2>
              <p>Los precios y monedas se muestran antes de finalizar la compra. Los impuestos o condiciones de pago que resulten aplicables se muestran o calculan durante el proceso de checkout cuando corresponda.</p>
              <h2>5. Responsabilidad del cliente</h2>
              <p>Antes de comprar, revisa la técnica, medidas, materiales e información del archivo indicados en la ficha del producto y conserva de forma segura los datos de tu pedido.</p>
              <h2>6. Problemas con un pedido</h2>
              <p>Si una descarga o pedido presenta un problema técnico, escríbenos para que podamos revisarlo. La <a href="<?php echo esc_url( make_refund_policy_url( 'es' ) ); ?>">política de reembolso</a> explica cómo se gestionan las incidencias de productos digitales.</p>
              <h2>7. Responsabilidad y derechos imperativos</h2>
              <p>Nada de lo indicado en estas condiciones excluye derechos o remedios que legalmente no puedan excluirse. Drielo no responde de fallos causados por circunstancias fuera de su control razonable, siempre con respeto a la normativa imperativa aplicable.</p>
              <h2>8. Cambios</h2>
              <p>Estas condiciones pueden actualizarse para usos futuros de la web y compras futuras. A cada pedido se aplican las condiciones vigentes en el momento de realizarlo, sin perjuicio de la normativa imperativa.</p>
            <?php endif; ?>
          <?php endif; ?>
        </article>

        <aside class="info-card info-card--aside contact-note">
          <div class="contact-meta">
            <div class="contact-meta-item">
              <small><?php echo esc_html( $is_en ? 'Questions' : 'Consultas' ); ?></small>
              <strong><a href="<?php echo esc_url( make_contact_url() ); ?>"><?php echo esc_html( $is_en ? 'Contact Drielo' : 'Contactar con Drielo' ); ?></a></strong>
            </div>
            <div class="contact-meta-item">
              <small><?php echo esc_html( $is_en ? 'Email' : 'Correo' ); ?></small>
              <strong><a href="mailto:<?php echo esc_attr( $email ); ?>"><?php echo esc_html( antispambot( $email ) ); ?></a></strong>
            </div>
            <div class="contact-meta-item">
              <small><?php echo esc_html( $is_en ? 'Updated' : 'Actualizado' ); ?></small>
              <strong><?php echo esc_html( $is_en ? '24 September 2026' : '24 de septiembre de 2026' ); ?></strong>
            </div>
          </div>
        </aside>
      </div>
    <?php endif; ?>
  </div>
</section>
<?php get_footer(); ?>
