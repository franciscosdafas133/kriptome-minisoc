# Seguridad del hilo de correo (Inbound Response Router)

`policy_validation_status: DISEÑADO`. Contrato de las verificaciones obligatorias antes de que una respuesta de correo del cliente (`specifications/inbound_message.schema.json`) se trate como entrada válida al motor de casos. NO implica un servicio de recepción de correo implementado — ver `README.md` §"Qué NO está implementado". Complementa `specifications/client_notification.schema.json` (que documenta el mecanismo de respuesta libre, "no se ofrece un menú de respuestas A/B/C") desde el lado de recepción.

## 1. Por qué esto es una superficie de riesgo real

El correo entrante es, por diseño de este sistema, la única vía de entrada de texto libre no controlado por Kriptome hacia el flujo de un caso. Un mensaje que logre pasar como "respuesta legítima" sin serlo puede: cerrar un caso indebidamente, inyectar contenido en un resumen que la IA procesa después (ver `docs/architecture/AI_SCOPE_AND_GUARDRAILS.md` §5, prompt injection), o hacer creer al sistema que el cliente confirmó una acción que nunca confirmó.

## 2. Identidad del hilo — tres señales, nunca una sola

Un mensaje entrante se asocia a un `case_id` únicamente cuando las tres señales son coherentes entre sí:

1. **`provider_thread_id`** (autoridad primaria): el identificador de hilo que asigna el proveedor de correo — no depende de que el cliente no edite el asunto.
2. **`in_reply_to`** (header RFC 5322): debe apuntar al `Message-ID` del correo de `ClientNotification` original.
3. **`references`** (header RFC 5322): cadena completa de `Message-ID`s del hilo — verificación redundante de que `in_reply_to` no fue falsificado aisladamente.

**Nunca se usa el texto del asunto (`[case_id]` escrito literalmente) como única fuente de asociación** — cualquier remitente puede escribir un `case_id` ajeno en un asunto nuevo; el asunto es una ayuda de lectura humana, no una credencial.

`reply_token`: mecanismo adicional opcional (alias de respuesta único por notificación, p. ej. `case+<token>@dominio`) que un remitente no puede adivinar ni falsificar sin haber recibido el correo original — recomendado como cuarta señal cuando el proveedor de correo lo soporta, pero su ausencia (`null`) no invalida por sí sola una verificación que ya es `verified` por las tres señales de headers.

Un hilo con inconsistencia entre estas señales (p. ej. `in_reply_to` coincide pero `provider_thread_id` no) es `thread_verification_status=partial_match`, no `verified` — no se resuelve el conflicto a favor de la señal que "sí coincide", se trata como inconsistencia y va a revisión humana.

## 3. Identidad del remitente — contacto autorizado, no solo dirección de correo

`from_address` es evidencia, no autoridad (mismo patrón que `agent.labels.client_code` en `specifications/tenant_resolution.md`). La verificación compara contra el registro de contactos autorizados del tenant (fuera de alcance de este repo el registro en sí, pero el contrato de verificación es este):

- **`authorized_contact`**: la dirección remitente coincide con un contacto registrado y activo para ESE `tenant_id` específico (el mismo tenant del `case_id` resuelto por el hilo, no cualquier tenant). Es el único estado que permite procesamiento automático.
- **`unregistered_sender`**: dirección no registrada como contacto de ningún tenant, o registrada para un tenant distinto al del caso — nunca se asume que "algún contacto válido" es suficiente, tiene que ser un contacto del tenant correcto.
- **`domain_mismatch`**: el dominio del remitente no coincide con el dominio esperado del tenant (señal de alerta, no bloqueo automático — puede ser un contacto legítimo usando correo personal, pero requiere revisión).
- **`spoofing_suspected`**: fallos de autenticación de correo (SPF/DKIM/DMARC, cuando el proveedor los expone) o headers inconsistentes con el remitente declarado.
- **`verification_pending`**: estado transitorio mientras se ejecutan las comprobaciones — nunca se procesa un mensaje en este estado como si ya estuviera verificado.

## 4. Adjuntos — cuarentena antes que confianza

Ningún adjunto (`inbound_message.attachments[]`) se reenvía, se abre automáticamente, ni se usa como insumo para ninguna decisión (incluida una decisión de un operador humano sin advertencia) antes de completar `quarantine_status=clean`. `pending_scan` y `scan_error` se tratan igual de restrictivo que `malicious` para efectos de qué se puede hacer con el archivo — la ausencia de confirmación de limpieza no es equivalente a limpieza.

## 5. Correo reenviado (`forwarded_indicator`)

Un mensaje reenviado (`Fwd:`, headers de reenvío) desde un contacto autorizado **no** tiene la misma garantía de autenticidad que una respuesta directa: el contenido puede originarse en un tercero no verificado, y el remitente autorizado solo está retransmitiendo. Cuando `forwarded_indicator=true`, el mensaje va a `human_review_queue` aunque `sender_verification_status=authorized_contact` y `thread_verification_status=verified` — la combinación de "reenviado" con "acción sensible solicitada" nunca se procesa automáticamente.

## 6. Buzón comprometido (`compromised_mailbox_suspected`)

Un contacto autorizado no deja de serlo instantáneamente cuando su buzón es comprometido — por eso este es un campo separado, no un cuarto valor de `sender_verification_status`. Señales típicas: patrón de envío anómalo (hora, frecuencia, volumen), estilo/contenido inconsistente con mensajes previos del mismo contacto, o el mensaje llega desde una IP de origen (cuando el proveedor la expone) que coincide con una IP de mala reputación conocida (`enrichment_result.schema.json`).

**Regla dura**: cuando `compromised_mailbox_suspected=true`, ninguna acción sensible (cierre de caso, confirmación de una acción de contención, cualquier cosa que dispare `out_of_band_confirmation_required=true` en la notificación original) se ejecuta basada en este mensaje sin verificación por un canal alterno (llamada telefónica al contacto, mismo patrón que `client_notification.schema.json` `recipient_level=secundario_por_canal_alterno` para buzón comprometido del lado de envío) — el problema es simétrico en ambas direcciones del hilo.

## 7. Contactos no registrados que responden

Un `unregistered_sender` que responde en un hilo con `thread_verification_status=verified` (headers correctos, pero la persona que responde no es un contacto conocido — p. ej. reenvío interno del cliente a un colega que responde directamente) va a `human_review_queue`, nunca se descarta en silencio ni se procesa como si fuera el contacto original. El operador humano decide si vale la pena registrar a esa persona como contacto adicional del tenant o tratar la respuesta como no autorizada.

## 8. `routed_to` — la única salida automática

Un `InboundMessage` solo se enruta a `case_engine` (procesamiento automático como entrada al caso) cuando **las cuatro condiciones** se cumplen simultáneamente:

```
sender_verification_status == authorized_contact
AND thread_verification_status == verified
AND compromised_mailbox_suspected == false
AND forwarded_indicator == false
```

Cualquier otra combinación va a `human_review_queue` o `quarantine` (spoofing/malware detectado) — nunca hay una ruta automática parcial ("procesar pero marcar para revisar después").

## 9. Relación con controles de prompt injection

Ver `docs/architecture/AI_SCOPE_AND_GUARDRAILS.md` §5. El contenido de un `InboundMessage` que sí llega a `case_engine` (las cuatro condiciones de §8 cumplidas) puede eventualmente pasar por un intent `summarize_for_operator` — pero incluso verificado como remitente/hilo legítimo, el contenido del cuerpo del mensaje se trata siempre como dato delimitado, nunca como instrucción de control del sistema. Verificar la identidad del remitente resuelve "¿quién escribió esto?", no "¿es seguro tratar este texto como instrucciones?" — son dos problemas distintos y este documento solo resuelve el primero.

## 10. Known limitations

- No existe hoy un proveedor de correo integrado; los mecanismos de `reply_token` y verificación SPF/DKIM/DMARC dependen de capacidades específicas del proveedor elegido, no implementadas ni decididas en este repo.
- El registro de "contactos autorizados por tenant" (fuente de verdad para `sender_verification_status`) es un contrato asumido, no un schema formalizado en este repo todavía — queda como hueco de diseño explícito, no se inventa su estructura aquí.

## 11. Estado de este documento

`policy_validation_status: DISEÑADO`. No hay Inbound Response Router implementado, ni pruebas reales de verificación de hilo/remitente contra un proveedor de correo real.
