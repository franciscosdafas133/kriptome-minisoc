# Fuente de verdad documental — Kriptome MiniSOC

Este archivo resuelve las contradicciones entre documentos que coexisten en el repositorio, declarando cuál es vigente para cada área. Se creó porque `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (flujo A/B/C) y `specifications/client_notification.schema.json` (mensaje único, respuesta libre) especificaban diseños contradictorios sin que ningún documento anterior lo resolviera formalmente. Ampliado en v1.3.1 (Architectural Consistency) con el orden de precedencia formal entre TODAS las categorías de documento del repositorio, no solo el caso de comunicación.

## Orden de precedencia (v1.3.1)

Cuando dos artefactos de categorías distintas se contradigan, gana el de número más bajo. Dentro de la misma categoría, gana el más reciente por fecha de aprobación/commit.

| # | Categoría | Ejemplos en este repo | Por qué manda |
|---|---|---|---|
| 1 | **ADR aprobados** | `docs/adr/*.md` | Decisión de arquitectura explícita, con contexto y consecuencias registradas; la más deliberada de todas. |
| 2 | **Arquitectura canónica** | `docs/architecture/ARCHITECTURE_CANONICAL.md` | El flujo end-to-end de referencia; todo lo demás debe ser consistente con él. |
| 3 | **Contratos de datos** | `specifications/*.schema.json`, `specifications/*.md` | Máquina-verificables (JSON Schema); definen la forma exacta de los datos que cualquier implementación debe producir/consumir. |
| 4 | **Policies máquina-legibles** | `policies/case_types/*.yaml`, `policies/case_state_machine.yaml`, `policies/risk/*.yaml` | Comportamiento de negocio parametrizado, pensado para ser leído por código (o generarlo), no solo por humanos. |
| 5 | **Reglas Wazuh y configuración técnica** | `REGLAS_TUNEADAS/wazuh/`, `REGLAS_TUNEADAS/agent-conf/`, `REGLAS_TUNEADAS/routing/` | Verificado línea por línea contra el ruleset oficial de Wazuh v4.14.6; autoridad técnica de detección. |
| 6 | **Manuales operativos** | `DOCUMENTOS/03_FLUJOS_OPERATIVOS.docx`, `DOCUMENTOS/04_MANUAL_DE_USUARIO.docx`, `REGLAS_TUNEADAS/GUIA_*.docx` | Cómo se opera el día a día; debe reflejar 1-5, no inventar comportamiento nuevo. |
| 7 | **Documentos gerenciales** | `DOCUMENTOS/00_INFORME_FINAL.docx`, `DOCUMENTOS/05_COSTOS_Y_VIABILIDAD.docx`, `DOCUMENTOS/06_PLAN_IMPLEMENTACION_NUBE.docx` | Comunican la decisión hacia arriba/afuera; no son la fuente de implementación. |
| 8 | **Documentos históricos y de investigación** | `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (marcado HISTORICAL), los 6 `.docx` de análisis externo (`01_Propuesta...` a `06_Seguridad...`), `REGLAS_TUNEADAS/archive/` | Contexto y trazabilidad de cómo se llegó al diseño actual; **nunca implementable directamente**. |

**Regla explícita: un documento histórico no puede utilizarse como especificación implementable.** Si algo solo está descrito en un documento de categoría 6-8, no existe como contrato hasta que se formalice en 1-5.

### Convención de cabecera para documentos sustituidos

Todo documento que quede reemplazado por uno vigente debe declarar, tan cerca de su inicio como el formato del archivo lo permita (front-matter YAML en Markdown; primera sección en `.docx` si es editable; este mismo archivo como puente si no lo es):

```yaml
status: HISTORICAL
superseded_by: <ruta del documento vigente>
```

Ningún documento histórico se elimina — queda marcado como tal y se conserva para trazabilidad (ver regla de lectura abajo).

## Regla de lectura

Cuando dos documentos entren en conflicto sobre un área, **este archivo decide cuál es vigente**, aplicando el orden de precedencia de arriba. Ningún documento histórico se elimina — queda marcado como tal y se conserva para trazabilidad.

## Tabla de fuentes de verdad

| Área | Documento vigente | Documento histórico o reemplazado | Decisión | Fecha | Estado |
|---|---|---|---|---|---|
| Comunicación con el cliente (formato de respuesta) | `specifications/client_notification.schema.json` + `07_Outputs_y_Entregables_Detallado_v3.docx` | `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` | Mensaje único, sin opciones A/B/C. El cliente responde libremente al mismo correo indicando: si reconoce la actividad, quién la realizó, por qué motivo, qué acciones ejecutó, y si observó algo adicional. | 2026-07-22 | VIGENTE |
| Estructura del cuerpo del correo (secciones, tono, nivel de atención) | `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (parcialmente) + `specifications/client_notification.schema.json` (estructura formal) | — | El *tono* y el *lenguaje simple para MYPE peruana* del doc 07 siguen siendo la referencia de estilo; la *estructura de datos y el mecanismo de respuesta* los define el schema. Son complementarios en esto, no contradictorios. | 2026-07-22 | VIGENTE (parcial) |
| Reglas Wazuh, routing, familias de detección | `REGLAS_TUNEADAS/` (ruleset + `routing/routing_matrix.csv` + `routing/diccionario_campos_enriquecimiento.csv`) | — | Sin conflicto detectado con `DOCUMENTOS/02_DETECCION_Y_REGLAS.docx`; ambos describen el mismo ruleset auditado. | 2026-07-22 | VIGENTE |
| Arquitectura general, multi-tenant, seguridad | `DOCUMENTOS/01_ARQUITECTURA_Y_DISENO.docx` + `specifications/tenant_resolution.md` | — | Sin conflicto; `tenant_resolution.md` es una formalización técnica del mismo diseño de arquitectura. | 2026-07-22 | VIGENTE |
| Identidad y fingerprint del caso de vulnerabilidad KEV | `policies/case_types/VULNERABILITY.yaml` | `policies/case_types/VULNERABILITY_KEV.yaml` | `case_type` único y estable `VULNERABILITY` en vez de `VULNERABILITY_KEV`, para que el fingerprint (que incluye `case_type`) no cambie cuando un CVE genérico escala a KEV. Ver `vulnerability_classification`/`kev_status` como campos que enriquecen el mismo caso. | 2026-07-22 | VIGENTE (v1.3.1) |
| Análisis de negocio/producto (7 documentos v2.0) | Ninguno declarado vigente todavía | — | `07_Outputs_y_Entregables_Detallado_v3.docx` se declara vigente ÚNICAMENTE para el área de comunicación (fila 1 de esta tabla). Los otros 6 documentos (`01_Propuesta...` a `06_Seguridad...`) NO se declaran fuente de verdad de ninguna otra área en esta pasada — quedan pendientes de una decisión explícita del usuario sobre su alcance (ver `REPO_ALIGNMENT_REPORT.md`). | 2026-07-22 | PENDIENTE DE DECISIÓN |
| Flujo end-to-end de la plataforma (arquitectura de referencia) | `docs/architecture/ARCHITECTURE_CANONICAL.md` | `DOCUMENTOS/01_ARQUITECTURA_Y_DISENO.docx` (sigue vigente para el contexto de negocio y multi-tenant de alto nivel, no para el detalle de componentes técnicos) | Nuevo documento (v1.3.1) que enumera los 20 componentes del flujo canónico (Endpoint → ... → Audit) y su estado real (diseñado/con contrato/implementado/validado) por separado, para que ningún documento gerencial o histórico dé la impresión de que un componente ya está construido cuando solo está diseñado. | 2026-07-22 | VIGENTE (v1.3.1) |
| Identificadores de tenant y cliente | `specifications/tenant_identifier_migration.md` + `specifications/tenant.schema.json` (`tenant_id`) + `specifications/tenant_asset_assignment.schema.json` (`client_code`) | Menciones sueltas de `client_id` en `agent-conf/`, `kriptome_local_rules.xml` y versiones previas de `tenant.schema.json` | `tenant_id` = identificador técnico interno estable; `client_code` = código legible operativo (p. ej. `CLI-001`). No son sinónimos. Ver migración completa en el documento de la izquierda. | 2026-07-22 | VIGENTE (v1.3.1) |
| Máquina de estados del caso | `policies/case_state_machine.yaml` | El enum previo de `case.schema.json` (`open/pending_human_review/pending_client_response/closed_resolved/closed_false_positive/closed_auto`) | Estados unificados (`new/triaging/observing/pending_human/ready_to_communicate/waiting_client/monitoring/resolved/closed`), motivo de cierre como atributo separado (`resolution_type`), reapertura como transición `closed → triaging` (no un estado permanente `reopened`). | 2026-07-22 | VIGENTE (v1.3.1) |
| Origen de `routing_matrix.csv` | `policies/case_types/*.yaml` (fuente) → `scripts/generate_routing_matrix.py` (genera el CSV) | `REGLAS_TUNEADAS/routing/routing_matrix.csv` editado a mano | El CSV pasa a ser un artefacto **derivado**, regenerado desde las policies — no se edita directamente. Ver cabecera del propio CSV. | 2026-07-22 | VIGENTE (v1.3.1) |
| Exclusión de tecnologías (`rule_exclude`) en un Manager compartido | `docs/architecture/WAZUH_GROUP_PRECEDENCE.md` | Comentarios previos en `REGLAS_TUNEADAS/wazuh/config/ossec.conf.ruleset.snippet.xml` que sugerían excluir por cliente individual | `rule_exclude` es una decisión a nivel de Manager (tecnología ausente en TODO el parque atendido), no una personalización por tenant — la personalización por tenant se hace en policies de Kriptome y en la configuración de grupo/agente, nunca desactivando el ruleset entero. | 2026-07-22 | VIGENTE (v1.3.1) |
| Whitelist FIM tenant-specific vs global | Comentario ampliado de la regla `100030` en `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml` | — | La lista CDB `kriptome-fim-whitelist` es GLOBAL al Manager, solo admite ruido universal aprobado para TODOS los tenants; excepciones tenant-specific van en `agent.conf` del grupo del tenant o en la futura false-positive policy de la Kriptome App, nunca en la lista global. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency) |
| Cálculo de prioridad de negocio (`priority_level`) | `policies/risk/risk_policy_v1.yaml` | — | Política determinística (nunca IA) que combina 9 factores por regla de máximo (no promedio); `rule_level` de Wazuh es solo uno de los insumos, nunca copiado directamente. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency) |
| Alcance y límites de la IA | `docs/architecture/AI_SCOPE_AND_GUARDRAILS.md` | — | Catálogo cerrado de 5 intents permitidos, 8 prohibiciones explícitas, composición formal de `ai_input_hash`. La IA nunca decide tenant/severidad/procedimiento/estado/acción — solo redacta dentro de límites ya decididos determinísticamente. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency) |
| Verificación de respuestas de correo del cliente | `specifications/inbound_message.schema.json` + `docs/architecture/EMAIL_THREAD_SECURITY.md` | — | Un mensaje entrante solo se enruta a procesamiento automático si hilo verificado + remitente autorizado + sin sospecha de buzón comprometido + no reenviado, simultáneamente. Cualquier otra combinación va a revisión humana o cuarentena. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency) |
| Nomenclatura de campos de `Procedure` (`title`/`owner`/`approval_status`/etc.) | `specifications/procedure.schema.json` | — | `approval_status`/`forbidden_actions`/`required_evidence`/`client_actions`/`kriptome_actions`/`version` son EQUIVALENTES documentados de `status`/`do_not_do`/`evidence_to_preserve`/`customer_actions`/`internal_actions`/`procedure_version` — mismo campo, no duplicado; `title`/`owner`/`applicable_conditions` son campos nuevos genuinos. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency) |
| Continuidad operativa (backup/restore/RPO/RTO) | `docs/architecture/CAPACITY_AND_CONTINUITY.md` | — | 4 gates formales (`BACKUP_CONFIGURED`/`RESTORE_TESTED`/`RPO_APPROVED`/`RTO_APPROVED`); ninguno cumplido hoy — este documento es la referencia para trackear ese trabajo, no una certificación de que ya existe. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency), gates PENDIENTES |
| Alcance del Wazuh Dashboard | `docs/adr/ADR-0001-dashboard-scope.md` | — | El Dashboard es herramienta interna del SOC, nunca la interfaz cliente-facing; usuarios demo marcados `DEMO / VALIDATION ONLY`. | 2026-07-26 | VIGENTE (v1.3.1 — Architectural Consistency) |

## Declaración explícita sobre `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx`

```
ESTADO: HISTÓRICO
SUPERADO EN EL FLUJO A/B/C
NO UTILIZAR PARA IMPLEMENTAR RESPUESTAS
```

Este documento **no fue editado ni eliminado** (el repositorio no cuenta con una herramienta fiable para editar el binario `.docx` de forma segura sin arriesgar corromper su formato o su contenido — ver nota técnica abajo). La advertencia de reemplazo queda establecida aquí, en `README.md` y en `REPO_ALIGNMENT_REPORT.md`, como referencia obligatoria antes de usar ese documento para cualquier trabajo de implementación de respuestas del cliente.

Sigue siendo válido para: el tono, el lenguaje simple dirigido a MYPE peruana, y la lista de 15 escenarios de caso que cubre (uno por familia de detección) — esa taxonomía de escenarios no cambió, solo el mecanismo de respuesta A/B/C que quedó reemplazado.

### Nota técnica sobre no editar el binario

Los archivos `.docx` de este repositorio se generan y editan de forma fiable únicamente con la biblioteca `python-docx` u otra herramienta equivalente que preserve el paquete OOXML completo (relaciones, estilos, tabla de contenidos). No existe en este repositorio un proceso de edición de `.docx` validado como parte de esta pasada v1.3.1, y modificar el binario directamente arriesga corromper el archivo o introducir cambios no verificables. Por eso se optó por la alternativa segura: dejar la advertencia en los tres archivos Markdown (`README.md`, `REPO_ALIGNMENT_REPORT.md`, `REGLAS_TUNEADAS/CHANGELOG.md`) y en este documento, sin tocar el binario.

## Cómo se actualiza esta tabla

Cualquier corrección futura de una contradicción documental debe añadir una fila aquí (o actualizar la existente), nunca resolverse solo en un mensaje de commit o en la memoria de quien hizo el cambio.
