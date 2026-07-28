# CHANGELOG — REGLAS_TUNEADAS/

## v1.3.1 — Architectural Consistency (2026-07-26)

Quinta pasada, ejecutada como auditoría integral de arquitectura sobre el estado dejado por la pasada `v1.3.1 — Consistencia de contratos, tenants y validación automática` (2026-07-22, ver sección siguiente). Cierra inconsistencias arquitectónicas P0/P1/P2 detectadas y añade 12 documentos de arquitectura nuevos, 1 schema nuevo, 1 procedimiento nuevo, y extiende 2 scripts de validación. Mismo alcance y mismas limitaciones que la pasada anterior: sin backend, sin despliegue real, sin resultados de `wazuh-logtest`/shadow/piloto inventados, sin acciones Git ejecutadas por el asistente (commits/push quedaron para revisión humana).

### P0 — `rule_exclude` mal aplicado en Manager compartido
- `REGLAS_TUNEADAS/wazuh/config/ossec.conf.ruleset.snippet.xml`: el comentario sugería decisiones de exclusión "por cliente" en un archivo (`ossec.conf`) que es GLOBAL a todo el Manager en la arquitectura multi-tenant. Corregido con explicación completa de por qué `rule_exclude` solo es válido cuando NINGÚN tenant del Manager usa la tecnología, y las 4 alternativas correctas para personalización por tenant (grupo Wazuh, routing en la capa Kriptome, integración por agente, policy tenant-specific futura).
- Mismo principio aplicado a la whitelist FIM (regla `100030`, `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml`): documentado que la lista CDB `kriptome-fim-whitelist` es GLOBAL y solo admite ruido universal; excepciones tenant-specific van en `agent.conf` del grupo o en la futura false-positive policy de la Kriptome App, nunca en la lista global.

### Nuevos documentos de arquitectura (`docs/architecture/`)
- `WAZUH_GROUP_PRECEDENCE.md`: taxonomía de grupos Wazuh (`kriptome-baseline`/`ROLE-<x>`/`TENANT-<client_code>`), orden de precedencia obligatorio, y qué nunca va en cada nivel.
- `INGESTION_DESIGN.md`: diseño de polling del Global Internal Ingestor (`search_after`+overlap window+checkpoint+backpressure+dead-letter+recuperación tras reinicio).
- `AI_SCOPE_AND_GUARDRAILS.md`: catálogo cerrado de 5 intents permitidos para la IA, 8 prohibiciones explícitas, composición formal de `ai_input_hash` (7 componentes), controles de prompt injection.
- `EMAIL_THREAD_SECURITY.md`: verificación de hilo (provider_thread_id+in_reply_to+references), verificación de remitente autorizado, cuarentena de adjuntos, correo reenviado, buzón comprometido.
- `POSTGRES_TENANT_ISOLATION.md`: diseño de Row-Level Security (RLS) con `FORCE ROW LEVEL SECURITY`, `SET LOCAL` por transacción, roles separados, pruebas negativas obligatorias.
- `AUDIT_AND_OUTBOX.md`: audit log append-only con eventos compensatorios, y patrón transactional outbox completo (esquema, estados, idempotencia).
- `ENRICHMENT_RESILIENCE.md`: timeout/retry/backoff/circuit breaker/rate limit/caché positiva-negativa/stale fallback/exclusión de IPs privadas.
- `CAPACITY_AND_CONTINUITY.md`: variables de dimensionamiento y los 4 gates de continuidad (`BACKUP_CONFIGURED`/`RESTORE_TESTED`/`RPO_APPROVED`/`RTO_APPROVED`), ninguno cumplido hoy.
- `docs/adr/ADR-0001-dashboard-scope.md`: primer ADR del repositorio -- el Wazuh Dashboard es herramienta interna del SOC, nunca la interfaz cliente-facing; usuarios demo marcados `DEMO / VALIDATION ONLY`.

### Reconciliación de nomenclatura (`specifications/normalized_event.schema.json`, `specifications/procedure.schema.json`)
- `NormalizedEvent` ampliado con `agent_id`, `client_code`, `asset_code`, `decoder`, `source_port`, `destination_port`, `normalization_version` -- campos genuinamente faltantes frente al vocabulario de arquitectura más reciente. `event_hash`/`event_hash_version` NO se duplican (viven en `event_identity.schema.json`); `rule_id`/`rule_level`/`rule_groups` se mantienen separados en vez de un objeto `rule` único (Wazuh los expone como campos planos, verificado contra el XML real).
- `Procedure` ampliado con `title`, `owner`, `applicable_conditions` (nuevos genuinos) y equivalencias documentadas para `approval_status`/`forbidden_actions`/`required_evidence`/`client_actions`/`kriptome_actions`/`version` (mismos campos que `status`/`do_not_do`/`evidence_to_preserve`/`customer_actions`/`internal_actions`/`procedure_version`, sin duplicar). Los 5 procedures existentes actualizados con `title`/`owner`.
- Nuevo `procedures/PROC-VULN-KEV-MC-001.yaml`: sexto procedimiento, específico para el `material_change` "escalada a KEV de un caso ya notificado" -- distinto de `PROC-VULN-001` (procedimiento general de primera notificación).

### Política de riesgo determinística (nuevo)
- `policies/risk/risk_policy_v1.yaml`: 9 factores (incluye `technical_severity`, `evidence_strength`, `successful_access`, `scope`, `historical_context`, `business_impact` -- nuevos frente a los 4 ya existentes), regla de combinación por máximo (no promedio), overrides de escalada forzada (`known_exploitation=listed` y `successful_access=true` fuerzan mínimo `urgente`).
- `specifications/risk_result.schema.json`: enum de `risk_factors[].factor` ampliado de 9 a 15 valores, documentando la equivalencia con los factores ya existentes.

### Nuevo contrato de mensajería entrante
- `specifications/inbound_message.schema.json`: contrato formal de una respuesta de correo del cliente, con `thread_verification_status`/`sender_verification_status`/`compromised_mailbox_suspected`/`forwarded_indicator` y la regla de que solo se enruta a `case_engine` cuando las 4 condiciones de seguridad se cumplen simultáneamente.

### Validación automática extendida
- `scripts/validate_repository.py`: 9 secciones nuevas -- CSV drift (routing matrix), enlaces internos Markdown, prohibición `data.labels.*`, prohibición de PII en labels de agente, prohibición de `100040` como producción, prohibición de `assert` como control de seguridad, single state machine (`case.schema.json` vs `case_state_machine.yaml`), case_types duplicados, referencias a schemas inexistentes.
- **2 bugs reales encontrados y corregidos durante esta pasada** (no solo features nuevas): (1) `scripts/generate_routing_matrix.py --check` fallaba SIEMPRE por una comparación de fin de línea `\r\n` vs `\n` entre el archivo leído en modo texto universal y el contenido generado por `csv.writer` -- corregido leyendo con `newline=""`; (2) el nuevo check `single_state_machine` fallaba con `TypeError: unhashable type: 'dict'` porque `policies/case_state_machine.yaml` declara `states` como lista de objetos `{name, description}`, no de strings -- corregido.
- `.github/workflows/validate-contracts.yml`: paso renombrado para reflejar el alcance ampliado del validador.

### XML: recordatorio del patrón de error `--` en comentarios
- Durante la edición de `kriptome_local_rules.xml` y `ossec.conf.ruleset.snippet.xml` en esta misma pasada se reintrodujo accidentalmente `--` como puntuación dentro de comentarios XML (inválido por especificación) -- detectado y corregido de inmediato mediante re-validación de buena formación tras cada edición. Mismo patrón de error ya documentado en pasadas anteriores; ambos archivos quedan verificados como bien formados al cierre de esta pasada.

### Limitaciones pendientes (sin resolver, por diseño de esta pasada)
- Ningún componente nuevo de esta pasada tiene implementación real -- todos los documentos de `docs/architecture/` y `docs/adr/` son contratos `DISEÑADO`, no servicios funcionando.
- Los 4 gates de continuidad (`docs/architecture/CAPACITY_AND_CONTINUITY.md`) siguen sin cumplirse: no hay backups configurados, no hay restauración probada, no hay RPO/RTO acordados.
- El registro formal de "contactos autorizados por tenant" que sustenta `sender_verification_status` (`docs/architecture/EMAIL_THREAD_SECURITY.md`) no tiene un schema propio todavía -- documentado como hueco explícito.
- `docs/architecture/WAZUH_GROUP_PRECEDENCE.md` §5 (validación automática de claves duplicadas entre grupos) no está implementado.

## v1.3.1 — Consistencia de contratos, tenants y validación automática (2026-07-22)

Cuarta pasada el mismo día, corrigiendo contradicciones internas dejadas por v1.3.0 e introduciendo el modelo de tenant y la validación automática. Alcance explícitamente limitado a schemas, políticas, contratos de datos, ejemplos estructurados y documentación técnica Markdown — sin backend, API, base de datos, envío de correo, integración real de IA, conectores reales de enriquecimiento, remediación automática, despliegue de Wazuh, ni resultados de `wazuh-logtest`/shadow/piloto inventados. Ningún elemento se marcó `VALIDADO-LOGTEST`, `VALIDADO-SHADOW`, `VALIDADO-PILOTO` ni `OPERATIVO` sin evidencia real.

### Fuente de verdad documental
- Nuevo `DOCUMENTATION_SOURCE_OF_TRUTH.md`: tabla que resuelve explícitamente la contradicción entre `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (A/B/C) y `specifications/client_notification.schema.json` (mensaje único). Decisión vigente: mensaje único + respuesta libre, con `07_Outputs_y_Entregables_Detallado_v3.docx` y el schema como fuentes vigentes de comunicación. `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` queda marcado `HISTÓRICO / SUPERADO EN EL FLUJO A/B/C / NO UTILIZAR PARA IMPLEMENTAR RESPUESTAS` -- no se editó el binario (sin herramienta de edición segura validada en este repo), la advertencia vive en Markdown. `README.md` y `REPO_ALIGNMENT_REPORT.md` actualizados para reflejar este estado.

### Corrección del required de notificaciones (`specifications/client_notification.schema.json`)
- `body_sections.required` ahora incluye exactamente los 9 campos pedidos: `nivel_de_atencion, que_paso, por_que_importa, datos_principales, que_debe_hacer_usted, que_no_debe_hacer, que_esta_haciendo_kriptome, instrucciones_de_respuesta, detalle_soporte_tecnico` -- coincide con el changelog (antes había desalineación entre lo documentado y el `required` real del schema).
- Nuevas reglas `allOf`/`if`/`then` por `message_type`: `alerta_inicial`, `actualizacion` y `cierre` exigen `incident_facts`+`risk_explanation`+`action_plan`+`technical_appendix`; `recordatorio` exige solo `action_plan`; `digest_semanal`/`informe_mensual` quedan explícitamente exceptuados de `incident_facts` (mensajes agregados, no de un caso puntual) -- ya no es solo una diferencia descrita en texto.
- `subject`, `language`, `delivery_status`, `out_of_band_confirmation_required` pasan a ser obligatorios a nivel raíz. `message_key` se conserva como clave de idempotencia.
- Sin ninguna referencia operativa a A/B/C en el schema (solo la nota de desalineación histórica en la descripción).

### Separación de capas (`specifications/normalized_event.schema.json`)
- Se retiraron los campos que duplicaban capas posteriores: `asset_alias`, `environment`, `criticality`, `business_service`, `first_seen_at`, `last_seen_at`, `failed_attempt_count`, `successful_login_count`, `risk_score`, `risk_factors`. Cada uno tiene ahora una única fuente de verdad: `asset_context` (contexto del activo), `case_summary` (agregados del caso), `auth_evidence` (evidencia de autenticación), `risk_result` (riesgo calculado). `NormalizedEvent` vuelve a representar únicamente el evento puntual que Wazuh entrega.
- `specifications/client_notification.schema.json` se ajustó en paralelo: `incident_facts` ya no duplica `asset_alias`/`criticality`/`business_service`/etc. -- referencia `asset_id` y consulta `asset_context` por separado.

### Identidad estable del caso de vulnerabilidad
- **Problema corregido**: `case_type=VULNERABILITY_KEV` cambiaba de identidad cuando un CVE genérico escalaba a KEV, y el fingerprint incluye `case_type` -- eso generaba un caso nuevo en vez de enriquecer el existente, contradiciendo la propia regla de "no crear un segundo caso".
- Nuevo `policies/case_types/VULNERABILITY.yaml`: `case_type` único y estable `VULNERABILITY`. La información de KEV vive en dos campos que enriquecen el caso sin cambiar su identidad: `vulnerability_classification` (`generic`/`kev`/`ransomware_related`/`unsupported_product`) y `kev_status`. Fingerprint (`tenant_id+asset_id+case_type+cve`) nunca cambia.
- `policies/case_types/VULNERABILITY_KEV.yaml` reemplazado por un archivo pequeño de deprecación (`status: DEPRECATED`, `replaced_by: VULNERABILITY.yaml`), conservado por trazabilidad histórica.
- `REGLAS_TUNEADAS/routing/routing_matrix.csv`: fila de la regla 100040 corregida -- el fingerprint `VULN_KEV+cve` (distinto de `VULN+cve` de las demás filas Vuln) era la inconsistencia real detectada; ahora es el mismo fingerprint que 23504-23506.

### Procedimientos sin aprobación ficticia
- **Problema corregido**: los ejemplos anteriores usaban `approved_by: "EJEMPLO-NO-REAL"` con `status: "approved"`, simulando una aprobación humana que nunca ocurrió.
- Nuevo directorio `procedures/` con 5 procedimientos (`PROC-AUTH-001`, `PROC-MALWARE-001`, `PROC-FIM-001`, `PROC-AGENT-001`, `PROC-VULN-001`), todos con `status: draft`, `approved_by: null`, `approved_at: null`. `procedures/README.md` documenta quién debe aprobarlos, qué evidencia requiere la aprobación, versionado, retiro, y la regla dura de que un procedimiento `draft` no puede ser fuente de una notificación real.
- `specifications/procedure.schema.json` ampliado con `decision_points`: acciones condicionales (p. ej. `active_session_detected: true/false`) en vez de reglas universales sin contexto.

### Acciones operativamente riesgosas corregidas
- Se retiraron afirmaciones de capacidad inexistente en los ejemplos ("estamos revisando qué hizo la cuenta", "podemos bloquear la dirección de origen") -- reemplazadas por lenguaje honesto sobre el estado actual del repositorio (el caso queda "registrado y escalado para revisión humana").
- Se retiró la prohibición universal "no cerrar la sesión activa hasta revisarla" (podía permitir que una sesión hostil continuara) -- reemplazada por el `decision_point` condicional `active_session_detected` en `PROC-AUTH-001.yaml`.

### Modelo de activo hogar/empresa (`specifications/asset_context.schema.json`)
- Campo `environment` (prod/staging/dev) reemplazado por dos campos independientes: `environment_type` (`production/staging/development/testing/lab/personal/unknown`) y `site_type` (`home/office/branch/datacenter/cloud/hybrid/unknown`). Ejemplo "Casa del CEO": `{environment_type: 'personal', site_type: 'home'}`. `notification_field_mapping.md` actualizado.

### Contratos de tenant (nuevos)
- `specifications/tenant.schema.json`: registro de negocio del tenant (`tenant_type` incluye `home` para tenants residenciales, `status`, `onboarding_status` con 8 estados, contactos, `allowed_asset_count`, `timezone`, etc.).
- `specifications/tenant_asset_assignment.schema.json`: vínculo `agent_id`/`wazuh_group`/`asset_id`/`tenant_id` con `assignment_status` (`pending_verification/verified/inconsistent/quarantined/retired`) y la regla de integridad "un `asset_id` pertenece a un solo tenant activo" documentada como regla de colección (no expresable en JSON Schema puro).
- `specifications/tenant_resolution.md` ampliado: cadena completa `agent.id -> wazuh_group -> agent.labels.client_id -> tenant registry -> tenant_id -> asset registry -> asset_id` con la autoridad de cada eslabón explicitada; §3 pasa de 2 a 6 checks de consistencia obligatorios antes de aceptar un evento.

### Plan de implementación multi-tenant (nuevo)
- `implementation/multi_tenant_two_tenant_plan.md`: plan (`DISEÑADO`, no ejecutado) para dos tenants piloto -- Casa del CEO (`tenant_type=home`) y una empresa piloto por identificar -- cubriendo capa de negocio, capa Wazuh, capa Indexer, capa Dashboard y capa de validación (ingesta, atribución, procesamiento, generación de alertas, visualización, acceso cruzado, correlación cruzada).

### Validación automática (nuevo)
- `.github/workflows/validate-contracts.yml`: corre en `push`/`pull_request` -- sintaxis JSON, validez de JSON Schema Draft 2020-12, ejemplos contra schemas, sintaxis YAML, buena formación XML (estructura, no funcionamiento real en Wazuh), archivos obligatorios presentes, y búsqueda de referencias activas prohibidas (`Bloque A/B/C`, `como_responder`, `EJEMPLO-NO-REAL`) excluyendo archivos históricos/de deprecación explícitos.
- `scripts/validate_repository.py`: mismas comprobaciones ejecutables localmente, con salida `[PASS]`/`[FAIL]` por sección y código de salida distinto de cero si algo falla. Incluye una sección adicional `v1.3.1 consistency` que verifica específicamente que `NormalizedEvent` no duplique campos de capas posteriores, que `enrichment_result` tenga la regla condicional de `cisa_kev`, que `VULNERABILITY.yaml` exista y `VULNERABILITY_KEV.yaml` esté deprecado, y que `asset_context` use `environment_type`/`site_type`.
- Nuevo `examples/client_notifications/example_input_bundle.schema.json`: schema explícito para el envelope compuesto de los `*.input.json` -- deja constancia de que ese envelope NO es un objeto real de ningún componente, y valida cada clave interna contra su propio schema (vía `$ref`), sin fingir que el bundle completo cumple `client_notification.schema.json`.

### Ejemplos actualizados
- `_comment`/`_comment_*` eliminados de todos los `*.input.json`/`*.output.json` (rompían `additionalProperties: false`). La documentación se movió a `examples/client_notifications/README.md`, que explica: que son ilustrativos, que no fueron generados por un backend real, por qué `matching_user_verified=false` en el ejemplo de fuerza bruta, qué campos son simulados, y qué capacidades no existen todavía.
- `VULNERABILITY_KEV.{input,output}.json`/`.email.md` renombrados a `VULNERABILITY.*` (mismo `case_type` estable que la política).
- Ambos ejemplos usan ahora `environment_type`/`site_type`, procedimientos con `status: draft`/`approved_by: null`, y lenguaje honesto sobre capacidades.

### Limitaciones pendientes (sin resolver, por diseño de esta pasada)
- Ningún backend, API, base de datos, envío de correo, integración de IA, conector de enriquecimiento real o remediación automática implementados.
- Ningún procedimiento de `procedures/` está aprobado -- todos en `draft`.
- El plan de `implementation/multi_tenant_two_tenant_plan.md` es un diseño, no un piloto ejecutado.
- El riesgo de conteo cross-tenant en correlaciones nativas de Wazuh (`tenant_resolution.md`) sigue `PENDIENTE`, heredado sin resolver en el plan de dos tenants.
- La desalineación de comunicación con `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` está resuelta a nivel de fuente de verdad, pero el documento `.docx` en sí no fue editado (solo marcado histórico en Markdown).

## v1.3.0 — Alineación de outputs, KEV y políticas de casos (2026-07-22)

Tercera pasada el mismo día, centrada exclusivamente en schemas, políticas, contratos de datos, ejemplos estructurados y documentación técnica Markdown. Sin backend, sin API, sin base de datos, sin envío de correo, sin integración real con IA, sin consultas reales a CISA/VirusTotal/AbuseIPDB, sin remediación automática, sin pruebas inventadas. Ningún elemento se marcó `VALIDADO-LOGTEST`, `VALIDADO-SHADOW` ni `VALIDADO-PILOTO` sin evidencia real guardada.

### Eliminado
- Eliminado completamente el campo `como_responder` y toda referencia al "Bloque A/B/C" en `specifications/client_notification.schema.json`. La comunicación ahora es un solo mensaje: el cliente responde al mismo correo indicando si reconoce la actividad, quién la realizó, por qué motivo, qué acciones ejecutó y si encontró cambios extraños — sin menú de letras. La desalineación con `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (que aún especifica A/B/C, documento no editado) sigue documentada explícitamente en la descripción del schema.

### Cambiado — `specifications/client_notification.schema.json`
- `body_sections` ahora requiere: `nivel_de_atencion`, `que_paso`, `por_que_importa`, `datos_principales`, `que_debe_hacer_usted`, `que_no_debe_hacer`, `que_esta_haciendo_kriptome`, `instrucciones_de_respuesta`, `detalle_soporte_tecnico`.
- Nuevos objetos estructurados: `incident_facts` (asset_alias, hostname, environment, business_service, criticality, target_user, source_ip, access_type, workstation_name, first_seen_at, last_seen_at, successful_login_at, failed_attempt_count, successful_login_count, geo_country, geo_city, isp_or_asn, reputation_verdict, source_seen_before, authorized_source_match), `risk_explanation` (risk_score, priority_level, risk_factors, risk_policy_version, calculated_at), `action_plan` (procedure_id, procedure_version, customer_actions, do_not_do, evidence_to_preserve, recommended_deadline, escalation_contact), `technical_appendix` (rule_ids, event_ids, raw_event_references, mitre_ids, source_ip, target_user, logon_type, workstation_name, provider_references — nada de esto aparece en el cuerpo principal dirigido al cliente).

### Añadido — nuevos contratos de datos en `specifications/`
- `case_summary.schema.json`: resumen agregado de un caso. Regla explícita: `event_count` NO es sinónimo de `failed_attempt_count` — un caso puede mezclar eventos de distintos tipos.
- `asset_context.schema.json`: contexto de negocio del activo; `asset_alias` (p. ej. "Servidor de facturación") es el único identificador que ve el cliente, nunca `asset_id` crudo.
- `auth_evidence.schema.json`: formaliza `matching_user_verified` — resuelve la limitación real de 100013 (correlaciona por IP vía 60204, no por cuenta). Regla crítica de comunicación incluida como `$comment`: no se puede afirmar "N intentos contra la cuenta X" salvo que `matching_user_verified=true`; si es `false`, la redacción correcta separa "intentos desde la misma IP" de "acceso exitoso con la cuenta X".
- `risk_result.schema.json`: `priority_level` NO se copia directamente de `rule_level` — se deriva de `risk_factors` (catálogo cerrado: successful_login_after_failures, privileged_account, asset_criticality, asset_exposure, source_reputation, source_not_authorized, source_not_seen_before, attempt_count, known_exploitation), cada uno con factor/value/weight/explanation.
- `procedure.schema.json`: catálogo autorizado de acciones. `action_plan.customer_actions` de una notificación debe ser subconjunto de `procedure.customer_actions` — la IA mejora la redacción, nunca inventa acciones.

### Cambiado — `specifications/enrichment_result.schema.json` (CISA KEV)
- Añadidos `is_known_exploited` (derivado explícito de `kev_status`), `catalog_version`, `catalog_fetched_at`.
- Nuevo valor de estado `kev_status='stale_catalog'`: cuando la copia local del catálogo está desactualizada, NO se puede afirmar `not_listed` con confianza — se trata como dato incompleto, no como ausencia confirmada.
- Documentado explícitamente: la ausencia en KEV (`not_listed`) nunca significa que la vulnerabilidad sea segura, solo que CISA no la tiene listada como explotada activamente a la fecha de consulta.
- Campos verificados contra el feed real de CISA (`https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`, consultado 2026-07-22, 1651 entradas).

### Cambiado — `policies/case_types/VULNERABILITY_KEV.yaml`
- Declaración formal explícita: `source_detection: wazuh_vulnerability_detector` (23501/23504/23505/23506) + `kev_enrichment: kriptome_app`. La regla `100040` permanece `EXPERIMENTAL`/no productiva/no cargada y NO figura como fuente productiva principal.
- Nuevas limitaciones documentadas: manejo de `stale_catalog`, advertencia explícita sobre no tratar `not_listed` como "seguro".

### Cambiado — `policies/case_types/AUTH_BRUTEFORCE_SUCCESS.yaml` (corrección de inconsistencia)
- **Problema corregido**: el fingerprint (`tenant_id+asset_id+case_type+source_ip`) contradecía sus propios `material_changes`, que listaban "nuevo source_ip" y "otro asset" como cambios materiales del MISMO caso — imposible, porque ambos son campos del fingerprint: si cambian, se genera un caso nuevo por definición.
- Fingerprint corregido: se agrega `target_user`. `material_changes` reescrito para incluir únicamente cambios compatibles con un fingerprint fijo; se documenta explícitamente en `removed_as_material_change` qué se retiró y por qué.
- Nueva sección `auth_evidence_requirements`: exige verificar `matching_user_verified` antes de redactar cualquier notificación originada por la regla 100013.
- Nuevo bloque `campaign_correlation` (mismo archivo): relaciona casos con fingerprints DISTINTOS (misma IP contra varios assets/cuentas, o varias IPs contra la misma cuenta) sin fusionar los casos técnicos entre sí. Regla dura: `never_correlates_across: tenant_id`.

### Añadido — `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml`
- Nota técnica en la regla `100013`: documenta que la correlación nativa 60204 agrupa por IP, no por cuenta, y que la verificación de coincidencia de cuenta (`matching_user_verified`) se realiza en la futura Kriptome App consultando los eventos fallidos relacionados — no se creó una regla XML nueva sin probarla primero en un Manager real (fuera de alcance de esta pasada).

### Añadido — `examples/client_notifications/`
- `AUTH_BRUTEFORCE_SUCCESS.{input,output}.json` + `.email.md`: ejemplo con `matching_user_verified=false` (el caso más común, vía 100013), demostrando la redacción correcta que separa el conteo de intentos (por IP) del acceso exitoso (por cuenta).
- `VULNERABILITY_KEV.{input,output}.json` + `.email.md`: ejemplo con `kev_status='listed'`, usando un CVE y campos con formato verificado contra el feed real de CISA.

### Añadido — `specifications/notification_field_mapping.md`
- Tabla completa: texto visible → campo → objeto de origen → fuente original → obligatorio/opcional → fallback → si puede mostrarse al cliente → sensibilidad. Regla general: ningún campo se rellena con un valor inventado cuando falta el dato real — se omite la frase correspondiente.

### Pendiente (documentado, no resuelto por diseño de esta pasada)
- Ningún backend, API, base de datos, envío de correo, integración de IA o remediación automática implementados — los schemas y ejemplos son contratos, no código funcionando.
- `matching_user_verified` sigue siendo un campo de contrato: no existe hoy el código que compare `targetUserName` evento por evento.
- El motor de riesgo (`risk_result`) es un contrato de datos; no existe un clasificador real.
- La consulta real a CISA KEV, VirusTotal o AbuseIPDB no está implementada — los ejemplos usan datos ilustrativos con formato verificado contra el feed público real.

## v1.2.1 — Decisión D-KEV resuelta + revisión de schemas (2026-07-22)

Segunda pasada el mismo día, a partir de una revisión externa del contenido subido en v1.2.0. Confirmado con el usuario: no reemplaza los documentos 00–07 (siguen siendo la fuente funcional, no editados); una afirmación de "decisión final de mensaje único sin A/B/C" no tenía respaldo en ningún documento del repo en el momento de esta pasada — se aplicó de todos modos por instrucción explícita del usuario, dejando la desalineación documentada.

### Cambiado
- **Decisión D-KEV RESUELTA**: la fuente de verdad para CISA KEV es el enriquecimiento en la Kriptome App sobre las reglas nativas del Vulnerability Detector (23501/23504/23505/23506), consultando el feed CISA KEV únicamente cuando Wazuh ya entregó un `vulnerability.cve` válido — nunca de forma especulativa. El resultado enriquece el mismo caso y recalcula prioridad; no abre un segundo caso. Ver `policies/case_types/VULNERABILITY_KEV.yaml` (reescrito) y `specifications/enrichment_result.schema.json` (`$defs.kev_result`, campos verificados contra el feed real de CISA consultado el 2026-07-22: `cveID`, `vendorProject`, `product`, `vulnerabilityName`, `dateAdded`, `dueDate`, `requiredAction`, `knownRansomwareCampaignUse`, `cwes`, `notes`).
- Regla `100040` pasa de `EXPERIMENTAL` (decisión pendiente) a `DESCARTADA-PARA-PRODUCCION` (decisión tomada en su contra) — se conserva el archivo en `experimental/100040_cisa_kev.xml` solo como referencia histórica de la corrección XML aplicada en v1.0.0, no como pieza pendiente de activar.
- `specifications/client_notification.schema.json` reescrito: se retira el bloque `como_responder` (A/B/C) y se reemplaza por `customer_actions` (acción recomendada única + qué no hacer + evidencia a preservar + plazo recomendado). **Desalineación documentada explícitamente en el schema**: `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (verificado línea por línea en esta misma pasada) todavía especifica A/B/C en sus 15 plantillas — ese documento NO fue editado (fuera de alcance) y sigue siendo la fuente funcional vigente hasta que se reciban e integren documentos de reemplazo. Se añaden también `asset_context` (asset_alias, hostname, environment, criticality, business_service), `event_timing` (first_seen_at, last_seen_at, failed_attempt_count, successful_login_count), `auth_context` (logon_type, workstation_name) y `risk_assessment` (risk_score, risk_factors) como bloques nuevos.
- `specifications/normalized_event.schema.json` ampliado con los mismos campos de contexto/tiempo/autenticación/riesgo que `client_notification.schema.json`, más `cisa_kev` en el enum de `enrichment_pending` (solo aplicable cuando `cve` no es null).
- `specifications/validation_statuses.md`: añadida nota (regla de uso #5) aclarando que `DESCARTADA-PARA-PRODUCCION` es una anotación de texto libre (`policy_scope_status`), no un 11º estado del vocabulario cerrado de 10 estados definido en la v1.2.0.

## v1.2.0 — Alineación técnica (2026-07-22)

Trabajo de alineación estructural sobre el paquete técnico, sin tocar los documentos funcionales de negocio (`../DOCUMENTOS/`). Ver `../REPO_ALIGNMENT_REPORT.md` para el detalle completo de hallazgos y decisiones.

### Cambiado
- Reestructuración de carpetas: `rules/`, `decoders/`, `config/` (raíz de `REGLAS_TUNEADAS/`) se movieron a `wazuh/rules/`, `wazuh/decoders/`, `wazuh/config/` (historial de git preservado vía `git mv`).
- Vocabulario de estados de validación normalizado en todo el paquete técnico (`DISEÑADO`, `CONFIGURADO`, `VALIDADO-DOCUMENTALMENTE`, `VALIDADO-XML`, `VALIDADO-LOGTEST`, `VALIDADO-SHADOW`, `VALIDADO-PILOTO`, `PENDIENTE`, `EXPERIMENTAL`, `PEND-INTEGRACION`). Reemplaza el vocabulario libre anterior (`PEND-LOGTEST`, `PEND-SHADOW`, `NO VERIFICADO`, `OPCIONAL` usado como estado). Definiciones completas en `../specifications/validation_statuses.md`.
- `test_data/*.log` y `.json` permanecen como fixtures de entrada; los resultados esperados (antes solo narrativos dentro de `RESULTADOS_ESPERADOS.docx`) ahora también existen estructurados en `expected_results/*.expected.yaml`, sin contradecir ni reemplazar el `.docx`.

### Movido
- Regla `100040` (CISA KEV) movida de `rules/kriptome_local_rules.xml` a `experimental/100040_cisa_kev.xml`, deshabilitada (fuera del `<rule_dir>` cargado en producción). Motivo: decisión de arquitectura sin resolver (fuente de verdad KEV: regla de Wazuh vs. enriquecimiento en la Kriptome App — D-KEV, nunca decidida) y la lista `kriptome-cisa-kev` es un fixture de 3 CVEs fijos, no el feed real. La regla en sí sigue siendo `VALIDADO-XML` (su sintaxis es correcta) — se movió por una razón de producto, no por un bug.
- Snippet `wazuh/config/ossec.conf.ruleset.snippet.xml` actualizado: ya no declara `<list>etc/lists/kriptome-cisa-kev</list>` porque el set activo no la usa (ver nota v1.2.0 dentro del propio archivo).

### Añadido
- `README.md`, este `CHANGELOG.md`.
- `archive/pre-v1.2.0-paths/README.md` — mapeo de rutas viejas → nuevas, para que `GUIA_DE_DESPLIEGUE.docx` y `EXPLICACION_DEL_TUNING.docx` (no editados) sigan siendo utilizables.
- `lists/kriptome-cisa-kev.FIXTURE.md` — documenta explícitamente que la lista es un fixture de prueba, no el feed real (el formato CDB no admite comentarios inline sin corromper la compilación, ver nota técnica en ese archivo).
- `expected_results/*.expected.yaml` (3 archivos) + `expected_results/_cobertura.md` (matriz honesta de qué regla custom tiene fixture/expected result y por qué las que no lo tienen no lo tienen).
- `../specifications/` (raíz del repo): `normalized_event.schema.json`, `case.schema.json`, `enrichment_result.schema.json`, `client_notification.schema.json`, `case_type_policy.example.yaml`, `validation_statuses.md`, `tenant_resolution.md`.
- `../policies/case_types/` (raíz del repo): `AUTH_BRUTEFORCE_SUCCESS.yaml`, `MALWARE_CONFIRMED.yaml`, `FIM_CRITICAL_PATH.yaml`, `AGENT_HEALTH.yaml`, `VULNERABILITY_KEV.yaml`.
- `../REPO_ALIGNMENT_REPORT.md` (raíz del repo): inventario completo, hallazgos, y justificación de cada decisión tomada en esta versión.

### Verificado (sin cambio de comportamiento)
- `<same_source_ip/>` vs `<same_srcip/>`: verificado contra `src/analysisd/rules.c` del tag oficial `v4.14.6` (líneas 169-170, 1019-1020) — ambos son aliases reconocidos por el parser de Wazuh, funcionalmente idénticos. Se documentó la equivalencia en `wazuh/rules/kriptome_local_rules.xml`; **no se reemplazó el tag** porque `<same_source_ip/>` es el que usa el ruleset oficial de Wazuh (0 apariciones de `<same_srcip/>` en el ruleset oficial), y cambiarlo no habría corregido nada, solo desviado el estilo del proyecto respecto a la fuente que audita (`PROCEDENCIA_WAZUH.docx`).
- IDs de Active Directory para grupos sensibles (4728/4732/4756) confirmados existentes en `ruleset/rules/0580-win-security_rules.xml` del tag `v4.14.6`. Se mantienen en estado `PENDIENTE` (no se promueven a `VALIDADO-XML`) porque el campo de nombre de grupo depende de la política de auditoría de Windows del cliente, no verificable sin un entorno real.
- Correo M365 (familia 15) confirmado sin cambios: se mantiene `PEND-INTEGRACION` en `routing/routing_matrix.csv` y `routing/diccionario_campos_enriquecimiento.csv`.

## v1.1.0 (previo)

Revisión de despliegue: snippet `ossec.conf` con paridad al default de v4.14.6, listas CDB en formato estricto, `test_data/` con margen de frecuencia, runbook completo. Ver historial de `wazuh/rules/kriptome_local_rules.xml` para el detalle.

## v1.0.0 (previo)

Tuning inicial: auditoría del set de reglas propuesto contra el XML real de Wazuh v4.14.6, corrección de reglas rotas (100010–100013, 100030, 100040).
