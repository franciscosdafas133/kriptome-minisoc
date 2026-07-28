# Concurrencia del motor de casos

**Estado: DISEÑADO.** El motor de casos (`Transactional Case Engine`, ver `docs/architecture/ARCHITECTURE_CANONICAL.md`) no está implementado. Este documento fija el diseño de concurrencia que cualquier implementación futura debe respetar, para que "case_fingerprint agrupa eventos en un caso" no se convierta en una condición de carrera cuando dos eventos del mismo fingerprint llegan casi al mismo tiempo (frecuente: es exactamente lo que pasa durante un ataque de fuerza bruta).

## Requisitos obligatorios

1. **`event_hash` UNIQUE.** Ningún evento se procesa dos veces — ver `specifications/event_identity.schema.json`. La inserción del evento en el `Idempotent Event Store` debe ser idempotente: insertar dos veces el mismo `event_hash` no debe producir dos filas ni dos efectos.
2. **Inserción idempotente.** El motor debe poder recibir el mismo evento más de una vez (reintentos de red, replay tras un fallo del ingestor) sin duplicar trabajo. Un `INSERT ... ON CONFLICT (event_hash) DO NOTHING` (o equivalente) es la forma típica, pero la garantía debe existir independientemente del motor de base de datos elegido.
3. **Transacciones.** La secuencia "verificar si existe un caso activo con este fingerprint" + "crear o actualizar ese caso" + "registrar el evento" debe ejecutarse dentro de una única transacción — nunca como pasos separados que otro proceso concurrente pueda intercalar.
4. **Unique constraint para caso activo.** Ver modelo sugerido más abajo — evita que dos eventos casi simultáneos con el mismo fingerprint abran dos casos distintos.
5. **`fingerprint_hash` + `fingerprint_version`.** El fingerprint se calcula según la política del `case_type` (`policies/case_types/*.yaml`, campo `fingerprint_fields`). `fingerprint_hash` es el hash resultante; `fingerprint_version` permite cambiar el algoritmo/campos de fingerprint en el futuro sin invalidar silenciosamente los casos ya abiertos con la versión anterior (mismo principio que `event_hash_version`).
6. **Optimistic locking o advisory lock.** Para el paso "actualizar el caso existente" (agregar evento, evaluar cambio material, recalcular prioridad), se necesita un mecanismo que evite que dos actualizaciones concurrentes se pisen. Dos estrategias válidas:
   - **Optimistic locking**: una columna de versión en el caso; la actualización falla si la versión no coincide con la leída, y el proceso reintenta.
   - **Advisory lock** (PostgreSQL: `pg_advisory_xact_lock`, tomado sobre un hash del fingerprint): serializa las actualizaciones concurrentes al mismo caso sin bloquear el resto de la tabla.
7. **`case_events` UNIQUE.** Cada evento se asocia a lo sumo una vez a un caso (constraint sobre `(case_id, event_hash)` o equivalente) — evita que un reintento de la transacción del punto 3 duplique la asociación evento-caso.
8. **Transactional outbox.** Ver `docs/architecture/AUDIT_AND_OUTBOX.md` — cualquier efecto secundario que salga de la transacción del caso (notificar al cliente, disparar una llamada de IA) se registra en la misma transacción como un registro de outbox, nunca se ejecuta directamente dentro de la transacción de negocio.
9. **`message_idempotency_key` UNIQUE.** Evita que un reintento de envío (outbox) produzca un segundo correo — ver doc 03 nivel de control 7 y `specifications/client_notification.schema.json` (`message_key`).

## Modelo de datos sugerido (diseño, no una migración lista para ejecutar)

```sql
-- Deduplicación de eventos
CREATE UNIQUE INDEX ux_events_event_hash ON events (event_hash);

-- Un solo caso "activo" por fingerprint -- ver nota sobre "caso activo" abajo
CREATE UNIQUE INDEX ux_cases_active_fingerprint
  ON cases (tenant_id, fingerprint_hash, fingerprint_version)
  WHERE status NOT IN ('closed');

-- Cada evento se asocia a lo sumo una vez a un caso
CREATE UNIQUE INDEX ux_case_events_unique ON case_events (case_id, event_hash);

-- Idempotencia de mensajes salientes
CREATE UNIQUE INDEX ux_outbox_idempotency ON outbox (message_idempotency_key);
```

### Nota honesta sobre "cómo se representa un caso activo"

**No se afirma que esta restricción funcione en PostgreSQL sin más contexto.** El índice único parcial (`WHERE status NOT IN ('closed')`) es la pieza que hace que la unicidad aplique solo mientras el caso está abierto — permitiendo que, tras cerrar un caso, un nuevo evento con el mismo fingerprint abra legítimamente un caso *nuevo* (no reabra automáticamente el cerrado; la reapertura es una transición explícita, ver `policies/case_state_machine.yaml`). Esto depende de:

- Que `status` sea una columna con los valores exactos de `policies/case_state_machine.yaml` (ver Fase 9 de esta corrección) — si el motor usa nombres de estado distintos, el `WHERE` debe ajustarse.
- Que la base de datos soporte índices parciales (PostgreSQL sí; no todos los motores relacionales lo hacen igual).
- Que la lógica de aplicación respete la transacción del punto 3 arriba — el índice único evita la corrupción de datos, pero no reemplaza la necesidad de una transacción bien diseñada (dos transacciones concurrentes pueden ambas intentar insertar y una fallará por el constraint, pero la aplicación debe manejar ese fallo con un reintento que relea el caso existente, no con un error no controlado).

**Este modelo se marca `DISEÑADO`, no `VALIDADO-XML` ni ningún estado de implementación** (ver `specifications/validation_statuses.md`) — no se ha creado ninguna base de datos real que lo ejecute.
