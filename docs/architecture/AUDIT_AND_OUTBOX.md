# Audit log y Transactional Outbox

`policy_validation_status: DISEÑADO`. Contrato de dos mecanismos relacionados pero distintos referenciados desde múltiples documentos ya existentes (`specifications/case.schema.json` campo `notifications_sent`, `docs/architecture/AI_SCOPE_AND_GUARDRAILS.md` §6, `docs/architecture/POSTGRES_TENANT_ISOLATION.md` §6, `docs/architecture/CASE_ENGINE_CONCURRENCY.md`): el registro de auditoría append-only, y el patrón de outbox transaccional para envío confiable de mensajes. NO implica un servicio implementado.

## Parte A — Audit log

### A.1 Principio: append-only

`audit_log` registra hechos que ya ocurrieron. Un registro de auditoría que puede editarse o borrarse deja de ser evidencia — por eso la tabla no admite `DELETE` ni `UPDATE` bajo ningún rol de aplicación (`kriptome_app`), incluyendo `kriptome_maintenance` en operación normal (ver `docs/architecture/POSTGRES_TENANT_ISOLATION.md` §6, nota especial sobre esta tabla).

### A.2 Compensating events, no corrección in situ

Si un registro de auditoría resulta ser incorrecto (error de la aplicación al escribirlo, no un hecho falso del negocio), la corrección es un **evento compensatorio nuevo** que referencia al registro original — nunca una edición del registro existente:

```
audit_event_id: aud-00512
event_type: case_status_changed
...
superseded_by: null

audit_event_id: aud-00780
event_type: audit_correction
corrects: aud-00512
reason: "campo actor registrado incorrectamente por bug en el servicio X, corregido aquí"
...
```

El registro original permanece intacto y visible; el evento de corrección es público y trazable igual que cualquier otro evento — no hay "borrado silencioso con explicación aparte".

### A.3 Qué se audita como mínimo

Todo cambio de estado de un caso (cada transición de `policies/case_state_machine.yaml`, con `audit_event` ya definido por transición en esa policy), toda invocación de IA (ver `docs/architecture/AI_SCOPE_AND_GUARDRAILS.md` §6: `case_id`, `notification_intent`, `ai_input_hash` completo, resultado de `Validator`, si requirió revisión humana), todo mensaje efectivamente enviado o suprimido (`delivery_status` de `client_notification.schema.json`), toda decisión de `InboundMessage` (`routed_to`, ver `docs/architecture/EMAIL_THREAD_SECURITY.md`), y toda sesión bajo el rol `kriptome_maintenance` (`docs/architecture/POSTGRES_TENANT_ISOLATION.md` §5).

### A.4 Aislamiento por tenant

`audit_log` tiene `tenant_id` y RLS igual que cualquier otra tabla de negocio (`docs/architecture/POSTGRES_TENANT_ISOLATION.md` §6) — un operador de un tenant no ve auditoría de otro. Eventos de sistema sin tenant específico (p. ej. arranque en frío del ingestor, `docs/architecture/INGESTION_DESIGN.md` §11) usan `tenant_id = null` y son visibles solo para roles internos de operación de la plataforma, no para ningún operador de tenant.

## Parte B — Transactional Outbox

### B.1 El problema que resuelve

Escribir "el caso quedó actualizado" y "hay que enviar un correo" no puede ser dos operaciones separadas sin garantía conjunta: si la escritura del caso tiene éxito pero el envío del correo falla (o viceversa, si se envía el correo pero la transacción del caso hace rollback después), el sistema queda en un estado inconsistente — un correo enviado que no corresponde a ningún cambio confirmado, o un cambio confirmado que nunca se comunicó. El patrón *transactional outbox* resuelve esto escribiendo la intención de envío en la MISMA transacción de base de datos que el cambio de negocio, y despachando el envío real de forma asíncrona a partir de esa tabla.

### B.2 Esquema

```sql
CREATE TABLE outbox (
  outbox_id               TEXT PRIMARY KEY,
  tenant_id                TEXT NOT NULL,
  case_id                  TEXT NOT NULL REFERENCES cases(case_id),
  message_idempotency_key  TEXT NOT NULL UNIQUE,
  payload_reference        TEXT NOT NULL,   -- puntero al ClientNotification completo, no embebido aquí
  status                    TEXT NOT NULL,
  attempt_count             INTEGER NOT NULL DEFAULT 0,
  next_attempt_at           TIMESTAMPTZ,
  provider_id               TEXT,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at                   TIMESTAMPTZ
);

CREATE UNIQUE INDEX ux_outbox_idempotency ON outbox (message_idempotency_key);
```

(Mismo índice de idempotencia ya declarado en `docs/architecture/CASE_ENGINE_CONCURRENCY.md` — este documento detalla el ciclo de vida completo de esa tabla, no redefine el índice.)

### B.3 Estados (`status`)

```
pending          -- escrito en la misma transacción que el cambio de negocio, aún no despachado
sending          -- un worker tomó el registro y está intentando el envío ahora
sent             -- confirmado por el proveedor de correo -- estado terminal
failed_retryable -- falló pero puede reintentarse (timeout, error 5xx del proveedor) -- vuelve a pending tras backoff
failed_permanent -- falló de forma no recuperable (dirección inválida, rechazo definitivo) -- estado terminal, requiere atención humana
cancelled        -- la intención de envío dejó de ser válida antes de despacharse (p. ej. el caso se reabrió con información distinta que invalida el mensaje ya encolado) -- estado terminal
```

Transiciones válidas: `pending → sending → {sent | failed_retryable | failed_permanent}`, `failed_retryable → pending` (tras `next_attempt_at`), `pending → cancelled`. Nunca `sent → *` (estado terminal real) ni `sending → cancelled` directamente (una cancelación durante un envío en curso espera la resolución del intento actual, no lo interrumpe a medias).

### B.4 Idempotencia end-to-end

`message_idempotency_key` es el mismo `message_key` de `specifications/client_notification.schema.json` — "un reintento de envío con el mismo message_key no debe producir un segundo correo" (doc 03 nivel de control 7). El `UNIQUE` en Postgres garantiza que un segundo intento de insertar la misma intención de envío (p. ej. por un reintento a nivel de aplicación del cambio de negocio que la originó) falla por conflicto y se descarta, no duplica la fila del outbox — igual que la idempotencia de eventos por `event_hash` (`docs/architecture/INGESTION_DESIGN.md` §6).

### B.5 Worker de despacho

Un proceso separado (no la misma transacción de negocio) consulta `outbox WHERE status = 'pending' AND (next_attempt_at IS NULL OR next_attempt_at <= now())`, marca a `sending` (con un lock apropiado para que dos workers no despachen el mismo registro dos veces — mismo tipo de garantía de concurrencia que `docs/architecture/CASE_ENGINE_CONCURRENCY.md` ya exige para el motor de casos), intenta el envío vía el proveedor de correo, y actualiza el estado final según el resultado. Reintentos con backoff exponencial, mismo patrón ya usado en `docs/architecture/INGESTION_DESIGN.md` §5.

### B.6 Relación con `case.notifications_sent`

`specifications/case.schema.json` campo `notifications_sent`: "solo se puebla cuando el mensaje efectivamente salió por el Transactional Outbox" — es decir, se agrega el `message_key` a esa lista únicamente cuando el registro de outbox correspondiente alcanza `status=sent`, nunca en el momento de crear el registro `pending`. Esto preserva la garantía de que "una llamada de IA no equivale automáticamente a un correo" (mismo campo, mismo comentario) incluso a nivel de outbox: encolar no es enviar.

## Estado de este documento

`policy_validation_status: DISEÑADO`. No hay tabla `audit_log` ni `outbox` reales, ni worker de despacho implementado — es el contrato para cuando el motor de casos se construya.
