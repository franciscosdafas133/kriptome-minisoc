# Kriptome MiniSOC

Repositorio técnico de Kriptome MiniSOC: reglas Wazuh, contratos de datos, políticas de casos y documentación funcional del proyecto. Este README explica **qué existe hoy en el repositorio y en qué estado**, para que nadie asuma capacidades que no están construidas.

> **Todos los ejemplos de este repositorio (`examples/`) son ilustrativos y no representan eventos reales.** Fueron diseñados a mano para validar los schemas de `specifications/`; no fueron generados por un backend, no provienen de un Manager Wazuh real, y ningún dato de enriquecimiento (GeoIP, reputación, CISA KEV) proviene de una consulta en vivo. Ver `examples/client_notifications/README.md` para el detalle.

## Fuente de verdad documental

Cuando dos documentos del repositorio parezcan contradecirse, **`DOCUMENTATION_SOURCE_OF_TRUTH.md` decide cuál es vigente** — no asumas por antigüedad ni por ubicación. En particular: `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` está marcado **HISTÓRICO / SUPERADO EN EL FLUJO A/B/C / NO UTILIZAR PARA IMPLEMENTAR RESPUESTAS** — el diseño vigente de comunicación (mensaje único, respuesta libre) es `specifications/client_notification.schema.json` + `07_Outputs_y_Entregables_Detallado_v3.docx`.

## Qué existe

```
DOCUMENTATION_SOURCE_OF_TRUTH.md  Tabla de fuentes de verdad vigentes vs. históricas
DOCUMENTOS/              8 documentos de negocio (00-07) + 2 índices — ver estado real en
                          DOCUMENTATION_SOURCE_OF_TRUTH.md (07 es HISTÓRICO para comunicación)
REGLAS_TUNEADAS/         Ruleset Wazuh custom v4.14.6 + documentación de despliegue
  wazuh/                 Reglas/decoders/config que se copian al Manager
  agent-conf/            Configuración de agentes
  lists/                 Listas CDB (una activa, una fixture)
  test_data/              Fixtures de entrada para wazuh-logtest
  expected_results/       Resultados esperados, estructurados
  experimental/            Reglas con decisión de arquitectura resuelta en su contra (no activas)
specifications/          Contratos de datos (JSON Schema + Markdown): eventos, casos, riesgo,
                          enriquecimiento, notificaciones, tenant, resolución de tenant,
                          mensajería entrante (inbound_message)
policies/case_types/     Políticas de negocio por tipo de caso (YAML)
policies/risk/           Política determinística de riesgo (risk_policy_v1.yaml)
procedures/              Catálogo de procedimientos autorizados (todos en estado draft)
docs/architecture/       Documentos de arquitectura DISEÑADO: grupos Wazuh, ingesta, alcance
                          de IA, seguridad de email, aislamiento Postgres, audit/outbox,
                          resiliencia de enriquecimiento, capacidad y continuidad
docs/adr/                Architecture Decision Records (ADR-0001: alcance del Dashboard)
examples/                Ejemplos ILUSTRATIVOS de entrada/salida (ver advertencia arriba)
implementation/          Plan de implementación multi-tenant (diseño, no ejecutado)
scripts/validate_repository.py   Validación local de contratos
.github/workflows/       Validación automática en CI
REPO_ALIGNMENT_REPORT.md  Historial de auditoría técnica de este repositorio
```

## v1.3.1 — Architectural Consistency (2026-07-26)

Segunda pasada v1.3.1 del mismo ciclo, esta vez de alcance arquitectónico (28 fases, ver `REGLAS_TUNEADAS/CHANGELOG.md` para el detalle completo). Añade 8 documentos nuevos en `docs/architecture/`, el primer ADR (`docs/adr/ADR-0001-dashboard-scope.md`), `policies/risk/risk_policy_v1.yaml`, `specifications/inbound_message.schema.json`, un sexto procedimiento (`PROC-VULN-KEV-MC-001`), y 9 checks nuevos en `scripts/validate_repository.py` — incluyendo la corrección de 2 bugs reales encontrados en el propio tooling de validación (comparación de fin de línea en `generate_routing_matrix.py --check`, y un `TypeError` en el nuevo check de máquina de estados única). Corrige además un hallazgo P0 sobre `rule_exclude` mal aplicado como si fuera personalización por tenant en un Manager compartido. Mismo alcance limitado que toda pasada anterior: ningún componente nuevo tiene implementación real, ningún gate de continuidad está cumplido, sin acciones Git ejecutadas por el asistente.

## Qué está diseñado

Toda la lógica de negocio del proyecto: cómo un evento de Wazuh se convierte en un caso, cómo se calcula prioridad, cómo se comunica al cliente, cómo se resuelve el multi-tenant, y las políticas de tipos de caso (`AUTH_BRUTEFORCE_SUCCESS`, `MALWARE_CONFIRMED`, `FIM_CRITICAL_PATH`, `AGENT_HEALTH`, `VULNERABILITY`). Ver `specifications/` y `policies/case_types/`.

**Nota v1.3.1**: el caso de vulnerabilidad usa un `case_type` único y estable, `VULNERABILITY` (antes `VULNERABILITY_KEV`) — un CVE genérico y su eventual escalamiento a KEV son el MISMO caso con el mismo fingerprint, nunca dos casos distintos. `policies/case_types/VULNERABILITY_KEV.yaml` queda como archivo deprecado, ver ese archivo para el puntero.

## Qué está configurado

El paquete `REGLAS_TUNEADAS/wazuh/` está completo y listo para copiarse a un Manager Wazuh v4.14.6 (ver `REGLAS_TUNEADAS/GUIA_DE_DESPLIEGUE.docx`). Los schemas de `specifications/` son JSON Schema Draft 2020-12 válidos, las políticas de `policies/case_types/` y los procedimientos de `procedures/` son YAML válido — verificable localmente con `python scripts/validate_repository.py` y automáticamente en cada push/PR (`.github/workflows/validate-contracts.yml`).

## Qué está validado — y a qué nivel

Este repositorio usa un vocabulario cerrado de estados (`specifications/validation_statuses.md`): `DISEÑADO`, `CONFIGURADO`, `VALIDADO-DOCUMENTALMENTE`, `VALIDADO-XML`, `VALIDADO-LOGTEST`, `VALIDADO-SHADOW`, `VALIDADO-PILOTO`, `PENDIENTE`, `EXPERIMENTAL`, `PEND-INTEGRACION`. Regla estricta: **ningún elemento se marca `VALIDADO-LOGTEST`, `VALIDADO-SHADOW`, `VALIDADO-PILOTO` u `OPERATIVO` sin evidencia real guardada en el repo** — y hoy no existe esa evidencia para ninguna regla, porque el ruleset nunca se ha ejecutado en un Manager real ni existe un piloto activo.

Lo que SÍ está `VALIDADO-XML` (comprobado línea por línea contra el código fuente oficial de Wazuh v4.14.6, no inferido): las reglas custom activas (100010-100013, 100030), la equivalencia `same_source_ip`/`same_srcip` (son aliases, ver `src/analysisd/rules.c`), los campos del diccionario de enriquecimiento, y el formato del feed CISA KEV usado en `specifications/enrichment_result.schema.json` (verificado contra el feed público real).

## Qué está pendiente

- Ejecutar el ruleset contra un Manager Wazuh real con `wazuh-logtest` (`PENDIENTE` en todas las reglas de correlación).
- Verificar `matching_user_verified` para casos originados por la regla 100013 (correlaciona por IP, no por cuenta — ver `specifications/auth_evidence.schema.json`).
- Aislamiento multi-tenant a nivel de conteo en correlaciones de Wazuh (ver `specifications/tenant_resolution.md`).
- Integración M365/Office 365 (`PEND-INTEGRACION`, requiere credenciales de tenant real).
- Automatizar el feed real de CISA KEV (hoy la lista `REGLAS_TUNEADAS/lists/kriptome-cisa-kev` es un fixture de 3 CVEs fijos).
- Aprobación humana real de los procedimientos de `procedures/` (todos en `status: draft` — ninguno puede usarse para comunicar al cliente hasta ser aprobado, ver `procedures/README.md`).
- Ejecutar el plan de `implementation/multi_tenant_two_tenant_plan.md` (estado `DISEÑADO`, no ejecutado).
- Decisión del usuario sobre el tratamiento de los 6 documentos `.docx` de análisis (`01_Propuesta...` a `06_Seguridad...`) que no fueron declarados fuente de verdad de ninguna área (ver `DOCUMENTATION_SOURCE_OF_TRUTH.md`).
- Los 4 gates de continuidad (`BACKUP_CONFIGURED`/`RESTORE_TESTED`/`RPO_APPROVED`/`RTO_APPROVED`, ver `docs/architecture/CAPACITY_AND_CONTINUITY.md`) — ninguno cumplido hoy.
- Row-Level Security real en Postgres (`docs/architecture/POSTGRES_TENANT_ISOLATION.md`) — diseñado, sin base de datos desplegada ni pruebas negativas ejecutadas.
- Registro formal de contactos autorizados por tenant (`docs/architecture/EMAIL_THREAD_SECURITY.md` §3) — sin schema propio todavía.

## Qué NO está implementado

- Backend o motor de casos funcionando.
- API productiva.
- Base de datos productiva.
- Envío real de correos (las plantillas y schemas son contratos de texto/datos, no un sistema de envío).
- Integración real con un proveedor de IA.
- Consultas reales a CISA KEV, VirusTotal o AbuseIPDB (los `examples/` usan datos ilustrativos con formato verificado contra los feeds públicos reales, no llamadas en vivo).
- Remediación automática (bloqueo, aislamiento de equipos, etc.) — cualquier acción de este tipo en los ejemplos requiere `human_review_required: true` y `out_of_band_confirmation_required: true`, nunca se ejecuta sola.
- Despliegue de Wazuh en un Manager real (el paquete está listo, pero no se ha ejecutado).

Los JSON Schema de `specifications/`, las políticas de `policies/case_types/` y los procedimientos de `procedures/` son **contratos para cuando esos componentes se construyan**, no una implementación parcial de ellos.

## Por dónde empezar

- Para saber qué documento es vigente ante una contradicción: `DOCUMENTATION_SOURCE_OF_TRUTH.md`.
- Para entender el negocio: `DOCUMENTOS/_LEEME_PRIMERO.docx`.
- Para desplegar el ruleset: `REGLAS_TUNEADAS/README.md` y `REGLAS_TUNEADAS/GUIA_DE_DESPLIEGUE.docx`.
- Para entender los contratos de datos: `specifications/normalized_event.schema.json` → `specifications/case.schema.json` → `specifications/client_notification.schema.json`, en ese orden (el flujo de un evento a una notificación).
- Para el modelo de tenants: `specifications/tenant.schema.json`, `specifications/tenant_asset_assignment.schema.json`, `specifications/tenant_resolution.md`.
- Para ver ejemplos ilustrativos de entrada/salida: `examples/client_notifications/` (leer su README primero).
- Para validar el repositorio localmente: `python scripts/validate_repository.py`.
- Para el historial completo de decisiones técnicas: `REPO_ALIGNMENT_REPORT.md` y `REGLAS_TUNEADAS/CHANGELOG.md`.
