# Kriptome MiniSOC

Repositorio técnico de Kriptome MiniSOC: reglas Wazuh, contratos de datos, políticas de casos y documentación funcional del proyecto. Este README explica **qué existe hoy en el repositorio y en qué estado**, para que nadie asuma capacidades que no están construidas.

## Qué existe

```
DOCUMENTOS/              8 documentos de negocio (00-07) + 2 índices — fuente funcional del proyecto
REGLAS_TUNEADAS/         Ruleset Wazuh custom v4.14.6 + documentación de despliegue
  wazuh/                 Reglas/decoders/config que se copian al Manager
  agent-conf/            Configuración de agentes
  lists/                 Listas CDB (una activa, una fixture)
  test_data/              Fixtures de entrada para wazuh-logtest
  expected_results/       Resultados esperados, estructurados
  experimental/            Reglas con decisión de arquitectura resuelta en su contra (no activas)
specifications/          Contratos de datos (JSON Schema + Markdown): eventos, casos, riesgo,
                          enriquecimiento, notificaciones, resolución de tenant
policies/case_types/     Políticas de negocio por tipo de caso (YAML)
examples/                Ejemplos de entrada/salida que cumplen los schemas de specifications/
REPO_ALIGNMENT_REPORT.md  Historial de auditoría técnica de este repositorio
```

## Qué está diseñado

Toda la lógica de negocio del proyecto: cómo un evento de Wazuh se convierte en un caso, cómo se calcula prioridad, cómo se comunica al cliente, cómo se resuelve el multi-tenant, y las políticas de 5 tipos de caso (`AUTH_BRUTEFORCE_SUCCESS`, `MALWARE_CONFIRMED`, `FIM_CRITICAL_PATH`, `AGENT_HEALTH`, `VULNERABILITY_KEV`). Ver `specifications/` y `policies/case_types/`.

## Qué está configurado

El paquete `REGLAS_TUNEADAS/wazuh/` está completo y listo para copiarse a un Manager Wazuh v4.14.6 (ver `REGLAS_TUNEADAS/GUIA_DE_DESPLIEGUE.docx`). Los schemas de `specifications/` son JSON Schema válidos y las políticas de `policies/case_types/` son YAML válido.

## Qué está validado — y a qué nivel

Este repositorio usa un vocabulario cerrado de estados (`specifications/validation_statuses.md`): `DISEÑADO`, `CONFIGURADO`, `VALIDADO-DOCUMENTALMENTE`, `VALIDADO-XML`, `VALIDADO-LOGTEST`, `VALIDADO-SHADOW`, `VALIDADO-PILOTO`, `PENDIENTE`, `EXPERIMENTAL`, `PEND-INTEGRACION`. Regla estricta: **ningún elemento se marca `VALIDADO-LOGTEST`, `VALIDADO-SHADOW` o `VALIDADO-PILOTO` sin evidencia real guardada en el repo** — y hoy no existe esa evidencia para ninguna regla, porque el ruleset nunca se ha ejecutado en un Manager real.

Lo que SÍ está `VALIDADO-XML` (comprobado línea por línea contra el código fuente oficial de Wazuh v4.14.6, no inferido): las reglas custom activas (100010-100013, 100030), la equivalencia `same_source_ip`/`same_srcip` (son aliases, ver `src/analysisd/rules.c`), los campos del diccionario de enriquecimiento, y el formato del feed CISA KEV usado en `specifications/enrichment_result.schema.json` (verificado contra el feed público real).

## Qué está pendiente

- Ejecutar el ruleset contra un Manager Wazuh real con `wazuh-logtest` (`PENDIENTE` en todas las reglas de correlación).
- Verificar `matching_user_verified` para casos originados por la regla 100013 (correlaciona por IP, no por cuenta — ver `specifications/auth_evidence.schema.json`).
- Aislamiento multi-tenant a nivel de conteo en correlaciones de Wazuh (ver `specifications/tenant_resolution.md` §2).
- Integración M365/Office 365 (`PEND-INTEGRACION`, requiere credenciales de tenant real).
- Automatizar el feed real de CISA KEV (hoy la lista `REGLAS_TUNEADAS/lists/kriptome-cisa-kev` es un fixture de 3 CVEs fijos).
- Decisión del usuario sobre el tratamiento de 7 documentos `.docx` adicionales encontrados en la raíz del repo, que citan este mismo repositorio como fuente (ver `REPO_ALIGNMENT_REPORT.md`, actualización de la tercera pasada) — no fusionados ni tratados como reemplazo de `DOCUMENTOS/00-07` todavía.
- Desalineación conocida entre `specifications/client_notification.schema.json` (mensaje único, sin A/B/C) y `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` (aún especifica A/B/C) — documentada explícitamente en el propio schema, no resuelta.

## Qué NO está implementado

- Backend o motor de casos funcionando.
- API productiva.
- Base de datos productiva.
- Envío real de correos (las plantillas y schemas son contratos de texto/datos, no un sistema de envío).
- Integración real con un proveedor de IA.
- Consultas reales a CISA KEV, VirusTotal o AbuseIPDB (los `examples/` usan datos ilustrativos con formato verificado contra los feeds públicos reales, no llamadas en vivo).
- Remediación automática (bloqueo, aislamiento de equipos, etc.).

Los JSON Schema de `specifications/` y las políticas de `policies/case_types/` son **contratos para cuando esos componentes se construyan**, no una implementación parcial de ellos.

## Por dónde empezar

- Para entender el negocio: `DOCUMENTOS/_LEEME_PRIMERO.docx`.
- Para desplegar el ruleset: `REGLAS_TUNEADAS/README.md` y `REGLAS_TUNEADAS/GUIA_DE_DESPLIEGUE.docx`.
- Para entender los contratos de datos: `specifications/normalized_event.schema.json` → `specifications/case.schema.json` → `specifications/client_notification.schema.json`, en ese orden (el flujo de un evento a una notificación).
- Para ver ejemplos completos de entrada/salida: `examples/client_notifications/`.
- Para el historial completo de decisiones técnicas: `REPO_ALIGNMENT_REPORT.md` y `REGLAS_TUNEADAS/CHANGELOG.md`.
