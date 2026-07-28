# Aislamiento multi-tenant en PostgreSQL (Row-Level Security)

`policy_validation_status: DISEÑADO`. Contrato de cómo debe aplicarse el aislamiento por `tenant_id` en la base de datos relacional del motor de casos, usando Row-Level Security (RLS) nativo de PostgreSQL. NO implica una base de datos real desplegada con estas políticas — es el diseño que cualquier implementación futura del motor de casos debe seguir. Equivalente, para Postgres, de `docs/architecture/INDEXER_ACCESS_MODEL.md` (que resuelve el mismo problema para el Indexer).

## 1. Por qué RLS y no solo "acordarse de filtrar por tenant_id en cada query"

Confiar en que cada consulta de aplicación incluya manualmente `WHERE tenant_id = ?` es un control que falla silenciosamente: un `JOIN` mal escrito, una consulta de debugging, un endpoint nuevo que un desarrollador olvida filtrar, o una librería de reporting que construye SQL dinámico pueden filtrar datos de un tenant a otro sin que ningún test lo detecte hasta que ya ocurrió en producción. RLS mueve el control de "disciplina del desarrollador en cada query" a "garantía del motor de base de datos en cada fila", igual que la Regla de seguridad #1-bis de `specifications/tenant_resolution.md` prohíbe `assert` como control de seguridad por la misma razón: un control que puede omitirse silenciosamente no es un control.

## 2. Diseño de política RLS

```sql
-- Cada tabla con datos de tenant tiene tenant_id NOT NULL, sin excepción.
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases FORCE ROW LEVEL SECURITY;  -- aplica incluso al dueño de la tabla

CREATE POLICY tenant_isolation_cases ON cases
  USING (tenant_id = current_setting('app.current_tenant_id')::text);
```

- **`FORCE ROW LEVEL SECURITY`** es obligatorio, no opcional: sin `FORCE`, el propietario de la tabla (el rol usado por migraciones/administración) queda exento de la política por defecto en PostgreSQL, lo que reabre exactamente el hueco que RLS existe para cerrar si la aplicación llega a conectarse alguna vez con ese rol.
- El valor de `app.current_tenant_id` se fija **por transacción**, nunca a nivel de conexión persistente compartida entre requests (ver §3) — una conexión reutilizada por un pool sin resetear este valor filtraría el tenant de la request anterior a la siguiente.

## 3. Contexto de tenant por transacción

```sql
BEGIN;
SET LOCAL app.current_tenant_id = 'tenant-abc-123';
-- todas las queries de esta transacción quedan filtradas por RLS
SELECT * FROM cases WHERE case_type = 'AUTH_BRUTEFORCE_SUCCESS';
COMMIT;
```

- **`SET LOCAL`** (no `SET`) es obligatorio: `SET LOCAL` revierte automáticamente al final de la transacción, incluso si la conexión vuelve a un pool y se reutiliza para otra request — `SET` persistiría el valor más allá de la transacción y filtraría datos del tenant equivocado en la siguiente consulta que use esa conexión reciclada sin fijarlo de nuevo explícitamente.
- El valor de `app.current_tenant_id` lo fija el backend a partir del `tenant_id` ya resuelto para la request/evento en curso (el mismo `tenant_id` de `specifications/tenant_resolution.schema.json` cuando se trata de procesar un evento, o el `tenant_id` de sesión autorizada del operador cuando se trata de una consulta de operador — ver distinción resolución/autorización en `specifications/tenant_resolution.md` §5) — nunca un valor aceptado directo de un parámetro HTTP.
- El equivalente al `GlobalInternalIngestorClient` del Indexer (`docs/architecture/INDEXER_ACCESS_MODEL.md`) para Postgres es un rol/proceso que necesita escribir NUEVOS registros (p. ej. crear el primer `case` para un evento recién resuelto) — ese proceso sigue fijando `app.current_tenant_id` al `tenant_id` ya resuelto antes de insertar, no opera "sin tenant"; a diferencia del Indexer, en Postgres no existe una ventana legítima de "dato sin tenant confirmado" porque un `case`/`asset`/`contact` nunca se crea sin `tenant_id` resuelto primero.

## 4. Roles separados

| Rol | Uso | RLS |
|---|---|---|
| `kriptome_app` | Rol de la aplicación en tiempo de ejecución (motor de casos, API interna). | Sujeto a RLS normalmente — cada transacción fija `app.current_tenant_id`. |
| `kriptome_migrations` | Solo para ejecutar migraciones de esquema (DDL), nunca para servir tráfico de aplicación. | No aplica RLS a nivel de fila (cambia estructura, no lee datos de negocio) pero NO debe usarse jamás para consultas de datos. |
| `kriptome_maintenance` | Tareas administrativas explícitas y auditadas (backups, reindexación, migraciones de datos entre tenants en un offboarding, soporte a un incidente de datos). | Bypassa RLS de forma explícita y auditada (ver §5) — nunca es el rol por defecto de ninguna conexión de aplicación. |

Ningún rol de aplicación (`kriptome_app`) tiene privilegio `BYPASSRLS`. Solo `kriptome_maintenance` puede tenerlo, y su uso está sujeto a §5.

## 5. Rol de mantenimiento auditado

Cualquier acceso que legítimamente necesite ver datos de más de un tenant a la vez (soporte de un incidente de datos, migración estructural, tarea de backup) usa `kriptome_maintenance` bajo estas condiciones obligatorias:

1. **Nunca es el rol de conexión por defecto de ningún servicio** — se invoca explícitamente, con una razón registrada.
2. **Toda sesión bajo este rol se audita** (ver `docs/architecture/AUDIT_AND_OUTBOX.md`, Fase 23): quién, cuándo, por qué, y qué tablas/tenants tocó.
3. **Preferencia por consultas de solo lectura** cuando el propósito es diagnóstico — escritura cross-tenant solo para migraciones de datos explícitamente planeadas y revisadas, nunca como atajo operativo de un incidente puntual.

## 6. Tablas mínimas con RLS obligatorio

Toda tabla que contenga datos vinculados a un tenant específico requiere RLS habilitado y forzado. Lista mínima (contratos de datos ya definidos en este repo que corresponderían a estas tablas):

| Tabla | Contrato de datos relacionado |
|---|---|
| `assets` | `specifications/tenant_asset_assignment.schema.json`, `specifications/asset_context.schema.json` |
| `contacts` | (registro de contactos autorizados, ver `docs/architecture/EMAIL_THREAD_SECURITY.md` §3 — schema formal pendiente) |
| `cases` | `specifications/case.schema.json` |
| `case_events` | `docs/architecture/CASE_ENGINE_CONCURRENCY.md` |
| `false_positive_rules` | (política de falsos positivos por tenant, ver `procedures/README.md` — schema formal pendiente) |
| `risk_results` | `specifications/risk_result.schema.json` |
| `outbound_messages` | `specifications/client_notification.schema.json`, `docs/architecture/AUDIT_AND_OUTBOX.md` |
| `inbound_messages` | `specifications/inbound_message.schema.json` |
| `audit_log` | `docs/architecture/AUDIT_AND_OUTBOX.md` |

`audit_log` merece una nota especial: SÍ tiene RLS por `tenant_id` para consultas normales (un operador de un tenant no debe ver auditoría de otro), pero es append-only incluso para `kriptome_maintenance` (ver `docs/architecture/AUDIT_AND_OUTBOX.md` §1 — ninguna política de RLS sustituye la prohibición de `DELETE` sobre esta tabla).

## 7. Pruebas negativas obligatorias

Una política RLS sin una prueba que confirme que efectivamente bloquea acceso cross-tenant es una política no verificada — el mismo principio de "no marcar VALIDADO sin evidencia" que aplica al resto del repo. Antes de considerar esta política implementada (no solo diseñada), se requiere al menos:

1. Con `app.current_tenant_id = 'tenant-A'`, un `SELECT * FROM cases` no debe devolver ninguna fila con `tenant_id = 'tenant-B'`, aunque existan filas de B en la tabla.
2. Con `app.current_tenant_id = 'tenant-A'`, un intento de `INSERT`/`UPDATE` que fije `tenant_id = 'tenant-B'` en la fila debe fallar (la política `WITH CHECK`, no solo `USING`, debe cubrir escritura además de lectura).
3. Una conexión que omite `SET LOCAL app.current_tenant_id` por completo (valor no fijado) no debe devolver silenciosamente "todos los tenants" ni "ningún error pero cero filas por accidente" — debe fallar de forma explícita (p. ej. `current_setting` sin segundo argumento `missing_ok` lanza error si no está fijado, que es el comportamiento deseado: fallar cerrado, no abierto).
4. Una sesión bajo `kriptome_app` (sin `BYPASSRLS`) no puede leer `audit_log` de otro tenant ni con un `JOIN` diseñado para eludir el filtro simple.

## 8. Qué NO resuelve este documento

- No define el modelo de conexión/pooling (pgbouncer u otro) en detalle — solo la obligación de que cualquier mecanismo de pooling usado sea compatible con `SET LOCAL` por transacción (algunos modos de pooling agresivo de conexión rompen esta garantía si no se configuran correctamente; verificar esto es un requisito de implementación, no un detalle resuelto aquí).
- No define backups/continuidad — ver `docs/architecture/CAPACITY_AND_CONTINUITY.md` (Fase 26).

## 9. Estado de este documento

`policy_validation_status: DISEÑADO`. No hay base de datos real desplegada con estas políticas, ni pruebas negativas de §7 ejecutadas contra un Postgres real — es el contrato que la implementación del motor de casos debe cumplir y probar cuando se construya.
