# CHANGELOG — REGLAS_TUNEADAS/

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
