# Migración de identificadores de tenant/cliente

**Estado: DISEÑADO.** Documenta una corrección de nomenclatura aplicada en v1.3.1 (Architectural Consistency): `client_id` dejó de usarse como término genérico porque en la práctica designaba dos cosas distintas según el archivo, lo cual habría producido implementaciones incompatibles si dos desarrolladores lo interpretaban de forma diferente.

## El problema encontrado

`client_id` aparecía en el repositorio con dos significados distintos:

1. En `REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example`, como el valor de una **label de Wazuh** (`CLI-001`) — un código legible, mutable en principio (podría renombrarse comercialmente), visible en logs y en el Manager.
2. En `specifications/tenant.schema.json` (antes de esta migración), como el **campo `tenant_id`** — descrito como "identificador estable... equivalente al client_id de agent-conf", mezclando implícitamente ambos conceptos en una sola frase.

Si dos implementaciones distintas hubieran tomado caminos diferentes sobre cuál de los dos significados es "el verdadero `client_id`", el resultado habría sido incompatible: una podría usar el código de Wazuh como clave primaria de base de datos (frágil ante un rebranding), otra podría generar un UUID interno y perder la trazabilidad con las labels operativas.

## La separación adoptada

| Campo | Qué es | Dónde vive | Mutabilidad |
|---|---|---|---|
| `tenant_id` | Identificador técnico interno, la clave primaria real del tenant | `specifications/tenant.schema.json` (campo `tenant_id`) | Inmutable una vez creado el tenant. |
| `client_code` | Código legible y operativo, el que efectivamente aparece en `agent.labels.client_code` y en reportes/logs | `specifications/tenant.schema.json` (campo `client_code`), `agent.labels.client_code` | Puede en teoría reasignarse (p. ej. si el cliente cambia de código comercial), sin que eso implique migrar el `tenant_id` ni ningún dato histórico asociado. |

Mismo patrón para el activo: `asset_id` (clave técnica) vs. `asset_code` (código legible en `agent.labels.asset_code`).

## Tabla de mapeo campo por campo

| Campo anterior | Nuevo campo | Motivo | Compatibilidad |
|---|---|---|---|
| `client_id` (label de Wazuh, `agent.conf`) | `client_code` | Es un código visible/operativo, no una clave técnica inmutable — nunca fue diseñado para serlo (un agent.conf se puede editar y redistribuir). | **Rompe compatibilidad de nombre de label.** Cualquier configuración de agente que use `<label key="client_id">` debe migrar a `<label key="client_code">`. Ver `REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example` para el ejemplo corregido. |
| `client_id` (campo implícito en `tenant.schema.json`, versión pre-v1.3.1) | `tenant_id` | Es la clave técnica real del registro de tenant. | El nombre del campo cambia de significado — antes `tenant_id` "equivalía" ambiguamente al label; ahora `tenant_id` y `client_code` son dos campos explícitos y separados en el mismo objeto `Tenant`. |
| `asset_id` (label de Wazuh) | `asset_code` | Mismo motivo que `client_code`. | Rompe compatibilidad de nombre de label; ver `REGLAS_TUNEADAS/agent-conf/kriptome-baseline_agent.conf`. |
| `criticality` (label de Wazuh) | `criticality_code` | Alinea el nombre con la convención "labels = códigos operativos" (ver `specifications/wazuh_alert_field_paths.md`). | Rompe compatibilidad de nombre de label. |
| `environment` (label de Wazuh, mencionado en comentarios previos) | `environment_code` | Idem; además ya se había separado en `environment_type`/`site_type` a nivel de `AssetContext` en la pasada anterior (v1.3.0/v1.3.1 previa) — el label operativo es un código corto, la clasificación completa vive en la CMDB. | Rompe compatibilidad de nombre de label. |
| `asset_alias` (label de Wazuh) | *(retirado de labels)* | Es un dato de negocio (nombre legible tipo "Servidor de facturación"), no un código — y es mutable/PII-adyacente. Ver Fase 6 de esta corrección. | El dato sigue existiendo, pero solo en `specifications/asset_context.schema.json` (CMDB), resuelto por backend a partir de `asset_code`. No hay label equivalente. |
| `client_name` (label de Wazuh) | *(retirado de labels)* | PII/dato mutable — ver Fase 6. | El dato sigue existiendo en `specifications/tenant.schema.json` (campo `tenant_name`), resuelto por backend a partir de `client_code`. |

## Formato de los identificadores

```json
"tenant_id": {
  "type": "string",
  "minLength": 1
}
```

```json
"client_code": {
  "type": "string",
  "pattern": "^[A-Z0-9][A-Z0-9_-]{2,31}$"
}
```

**No se impone UUID para `tenant_id`.** El formato definitivo (UUID v4, identificador secuencial de base de datos, u otro esquema) queda pendiente de una decisión formal — si el equipo la toma, debe registrarse como ADR en `docs/adr/` y este documento debe actualizarse para reflejarla. Hasta entonces, `tenant_id` acepta cualquier string no vacío a nivel de schema, precisamente para no bloquear el diseño de las demás piezas mientras esa decisión de formato madura.

## Qué NO se migró automáticamente

No se reemplazaron mecánicamente todas las apariciones de `client_id` en el repositorio. Cada aparición se revisó para decidir si representaba el código visible (→ `client_code`) o la clave interna (→ `tenant_id`):

- `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml` menciona `client_id` únicamente dentro de comentarios explicativos sobre el riesgo de aislamiento multi-tenant en correlaciones (sección "AISLAMIENTO MULTI-TENANT EN CORRELACIONES") — es prosa descriptiva, no un campo de schema; se deja como referencia histórica de ese análisis, sin renombrar, porque no es una interfaz que alguien vaya a implementar literalmente con ese nombre.
- Los `.docx` de `DOCUMENTOS/` (categoría 6-8 de precedencia, ver `DOCUMENTATION_SOURCE_OF_TRUTH.md`) no se editaron — son documentos históricos/gerenciales, no contratos implementables.
