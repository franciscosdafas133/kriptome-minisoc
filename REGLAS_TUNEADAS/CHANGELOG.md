# CHANGELOG — REGLAS_TUNEADAS/

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
