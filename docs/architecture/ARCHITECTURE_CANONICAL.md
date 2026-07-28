# Arquitectura canónica — Kriptome MiniSOC

**Estado de este documento: DISEÑADO.** Es el flujo de referencia contra el cual debe ser consistente cualquier otro documento o artefacto del repositorio (ver `DOCUMENTATION_SOURCE_OF_TRUTH.md`, categoría 2 de precedencia). No implica que el flujo completo esté construido — cada componente tiene su estado real marcado explícitamente más abajo.

## Regla de vocabulario (obligatoria en todo documento de negocio o informe)

Nunca usar la palabra "orquestador". Usar según corresponda:
- **Kriptome App** — el sistema completo de gestión de casos, en general.
- **servicio de procesamiento** — el componente que transforma eventos en casos.
- **motor de casos** — específicamente la lógica de apertura/actualización/cierre de casos.
- **servicio de ingesta** — el componente que lee del Indexer y normaliza eventos.
- **capa Kriptome** — todo lo que no es Wazuh (para contraponer "Wazuh detecta, la capa Kriptome administra").

## Flujo canónico completo

```
Endpoint / Integration
  → Wazuh Agent or Collector
  → Wazuh Manager
  → Wazuh Indexer
  → Global Internal Ingestor
  → Event Normalization
  → Tenant Resolver
  → Idempotent Event Store
  → Deterministic Router
  → Transactional Case Engine
  → CMDB
  → Enrichment Cache
  → Deterministic Risk Engine
  → Authorized Procedure
  → Deterministic Template or Optional LLM
  → Validator
  → Human Review if Required
  → Communication Policy
  → Transactional Outbox
  → Email Provider
  → Inbound Response Router
  → Audit
```

## Estado real de cada componente

Cuatro niveles, sin ambigüedad: **diseñado** (descrito en prosa, sin contrato formal) · **con contrato** (existe un JSON Schema/YAML que define su forma exacta) · **implementado** (existe código que lo ejecuta) · **validado** (el código implementado corrió con evidencia real guardada, ver `specifications/validation_statuses.md`).

| # | Componente | Estado | Artefacto de referencia |
|---|---|---|---|
| 1 | Endpoint / Integration | Implementado (fuera del alcance de este repo — es el activo del cliente) | — |
| 2 | Wazuh Agent or Collector | **Con contrato** — configuración lista para desplegar, nunca ejecutada | `REGLAS_TUNEADAS/agent-conf/` |
| 3 | Wazuh Manager | **Con contrato** — ruleset custom listo para copiar, nunca desplegado en un Manager real | `REGLAS_TUNEADAS/wazuh/` |
| 4 | Wazuh Indexer | Diseñado — modelo de acceso descrito, sin Indexer configurado | `docs/architecture/INDEXER_ACCESS_MODEL.md` |
| 5 | Global Internal Ingestor | Diseñado — sin código | `docs/architecture/INDEXER_ACCESS_MODEL.md` §GlobalInternalIngestorClient |
| 6 | Event Normalization | **Con contrato** — sin extractor implementado | `specifications/normalized_event.schema.json` |
| 7 | Tenant Resolver | **Con contrato** — sin backend implementado | `specifications/tenant_resolution.schema.json`, `specifications/tenant_resolution.md` |
| 8 | Idempotent Event Store | **Con contrato** parcial (identidad del evento); sin motor de persistencia | `specifications/event_identity.schema.json` |
| 9 | Deterministic Router | **Con contrato** (policies) + script de generación, sin motor que las ejecute en tiempo real | `policies/case_types/*.yaml`, `REGLAS_TUNEADAS/routing/routing_matrix.csv` (derivado) |
| 10 | Transactional Case Engine | Diseñado (modelo de concurrencia) + **con contrato** (forma del caso); sin motor implementado | `specifications/case.schema.json`, `docs/architecture/CASE_ENGINE_CONCURRENCY.md` |
| 11 | CMDB | **Con contrato** (activo, tenant); sin base de datos real | `specifications/asset_context.schema.json`, `specifications/tenant.schema.json` |
| 12 | Enrichment Cache | **Con contrato**; sin conectores reales ni caché implementada | `specifications/enrichment_result.schema.json`, `docs/architecture/ENRICHMENT_RESILIENCE.md` |
| 13 | Deterministic Risk Engine | **Con contrato/policy**; sin motor de cálculo implementado | `policies/risk/risk_policy_v1.yaml`, `specifications/risk_result.schema.json` |
| 14 | Authorized Procedure | **Con contrato**; procedimientos existentes todos en `status: draft`, ninguno aprobado | `specifications/procedure.schema.json`, `procedures/` |
| 15 | Deterministic Template or Optional LLM | **Con contrato** (schema de notificación); sin generador implementado; sin integración de IA real | `specifications/client_notification.schema.json` |
| 16 | Validator | Diseñado — la necesidad de validar la salida (de plantilla o LLM) está descrita, sin validador implementado | `docs/architecture/ARCHITECTURE_CANONICAL.md` (este documento, ver nota abajo) |
| 17 | Human Review if Required | Diseñado — el criterio de cuándo aplica vive en cada policy (`human_review_required`), sin cola de trabajo implementada | `policies/case_types/*.yaml` |
| 18 | Communication Policy | **Con contrato**; sin motor de aplicación de quiet hours/rate limit implementado | `specifications/client_notification.schema.json` |
| 19 | Transactional Outbox | Diseñado | `docs/architecture/AUDIT_AND_OUTBOX.md` |
| 20 | Email Provider | No implementado, no contratado | — |
| 21 | Inbound Response Router | **Con contrato** parcial; sin implementación | `specifications/inbound_message.schema.json`, `docs/architecture/EMAIL_THREAD_SECURITY.md` |
| 22 | Audit | Diseñado | `docs/architecture/AUDIT_AND_OUTBOX.md` |

*(Nota: el flujo del prompt lista 20 pasos; aquí se cuentan 22 porque "Validator" y "Human Review if Required" son dos pasos distintos del mismo flujo original, ambos presentes en la lista de arriba — no se agregó ni quitó ningún componente.)*

## Principios que ningún componente puede violar

Estos 5 principios (ya presentes en la arquitectura de negocio, ver `DOCUMENTOS/01_ARQUITECTURA_Y_DISENO.docx` y `DOCUMENTOS/03_FLUJOS_OPERATIVOS.docx`) se elevan aquí a regla de arquitectura canónica, vinculante para cualquier implementación futura:

1. **Wazuh detecta. La capa Kriptome administra casos y decisiones de negocio.** Ninguna regla de Wazuh decide prioridad de negocio, redacta comunicación, ni cierra un caso — eso vive en la capa Kriptome (componentes 9-22).
2. **Una alerta no equivale a un caso.** El paso 10 (Transactional Case Engine) es el único que abre/actualiza casos; los pasos 1-9 solo producen y normalizan eventos.
3. **Una repetición no equivale a otra llamada de IA.** Ver `ai_input_hash` en `specifications/case.schema.json` — el mismo contexto material no debe volver a pagar una llamada al paso 15.
4. **Una llamada de IA no equivale automáticamente a un correo.** El paso 16 (Validator) y el paso 17 (Human Review if Required) están *entre* la generación de texto y el envío — ninguna salida de IA llega al Transactional Outbox sin pasar por ambos cuando corresponda.
5. **Ningún dato de un tenant puede mezclarse con otro.** Aplica a los pasos 4-5 (aislamiento de ingesta, ver `docs/architecture/INDEXER_ACCESS_MODEL.md`), al paso 10 (un caso pertenece a un solo `tenant_id`), y a cualquier correlación de campaña (`specifications/campaign_correlation.schema.json`, regla `never_correlates_across: tenant_id`).

## La IA nunca es fuente de verdad de

- `tenant_id` (lo resuelve el paso 7, Tenant Resolver, nunca la IA).
- Severidad/prioridad (la calcula el paso 13, Risk Engine, de forma determinística).
- Qué procedimiento aplica (lo determina el paso 9/routing + el `case_type`, no la IA).
- Estado del caso (lo determina `policies/case_state_machine.yaml`, ejecutado por el motor de casos).
- Qué acción se ejecuta (proviene de un `Procedure` con `status: approved`, la IA solo redacta texto dentro de esos límites — ver Fase 20 de la corrección de consistencia, `docs/architecture/AI_SCOPE.md` si se crea aparte, o la nota en `specifications/procedure.schema.json`).
