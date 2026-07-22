# REGLAS_TUNEADAS/ — paquete técnico desplegable de Kriptome MiniSOC

Ruleset custom de Wazuh (v4.14.6) para Kriptome MiniSOC, más el diseño de casos, routing y comunicación al cliente que consume la Kriptome App. Este README describe la **estructura técnica del repositorio**; la fuente funcional del proyecto (qué es Kriptome, cómo opera, el modelo de negocio) vive en `../DOCUMENTOS/` y no se duplica aquí.

## Estructura

```
REGLAS_TUNEADAS/
├── README.md                      ← este archivo
├── CHANGELOG.md                   ← historial de versiones
├── wazuh/                         ← artefactos que se copian al Manager
│   ├── rules/kriptome_local_rules.xml
│   ├── decoders/kriptome_local_decoders.xml
│   └── config/ossec.conf.ruleset.snippet.xml
├── agent-conf/                    ← configs de agente (baseline + ejemplo por cliente)
├── lists/                         ← listas CDB (kriptome-fim-whitelist activa)
├── test_data/                     ← fixtures de entrada para wazuh-logtest
├── expected_results/              ← resultados esperados, estructurados (YAML)
├── experimental/                  ← reglas con decisión de arquitectura pendiente,
│                                     NO cargadas en producción
├── routing/                       ← routing_matrix.csv + diccionario de campos
├── archive/                       ← mapeos de ruta para compatibilidad con
│                                     documentación no editada
└── *.docx                         ← documentación de soporte del ruleset
                                      (GUIA_DE_DESPLIEGUE, EXPLICACION_DEL_TUNING,
                                      GUIA_LISTAS, GUIA_CAMPOS_ENRIQUECIMIENTO,
                                      PROCEDENCIA_WAZUH, RESULTADOS_ESPERADOS)
```

**Nota sobre rutas:** los `.docx` de este directorio referencian las rutas de la versión anterior (`rules/`, `decoders/`, `config/` en la raíz de `REGLAS_TUNEADAS/`, sin el prefijo `wazuh/`). No se editaron esos documentos en esta pasada (fuera de alcance). Ver `archive/pre-v1.2.0-paths/README.md` para el mapeo exacto ruta-vieja → ruta-nueva antes de seguir el runbook de `GUIA_DE_DESPLIEGUE.docx` al pie de la letra.

## Qué cambia respecto a v1.1.0

Ver `CHANGELOG.md`. En resumen: reestructuración de carpetas, normalización del vocabulario de estados de validación, y la regla `100040` (CISA KEV) se movió a `experimental/` por una decisión de arquitectura sin resolver (no por un error de sintaxis — la regla es `VALIDADO-XML`).

## Reglas activas (cargadas en el Manager)

| Regla | Case type | Estado |
|---|---|---|
| 100010 | roll-up brute force SSH | VALIDADO-XML |
| 100011 | brute force Windows por cuenta | VALIDADO-XML; requiere VALIDADO-LOGTEST (hoy PENDIENTE) |
| 100012 | login SSH OK tras brute force | VALIDADO-XML; requiere VALIDADO-LOGTEST (hoy PENDIENTE) |
| 100013 | login Windows OK tras brute force | VALIDADO-XML; requiere VALIDADO-LOGTEST (hoy PENDIENTE) |
| 100030 | whitelist FIM (opcional por cliente) | VALIDADO-XML |

## Reglas experimentales (NO cargadas)

| Regla | Motivo | Ver |
|---|---|---|
| 100040 | Decisión de arquitectura KEV pendiente + lista CDB es fixture, no feed real | `experimental/100040_cisa_kev.xml` |

Vocabulario completo de estados: `../specifications/validation_statuses.md`.

## Relación con `specifications/` y `policies/` (raíz del repo)

Este directorio contiene el **ruleset y sus artefactos de despliegue**. Los contratos de datos (schemas JSON, políticas de case_type, resolución de tenant) viven en `../specifications/` y `../policies/case_types/`, en la raíz del repositorio, porque son contratos que sirven a todo el proyecto (no solo al ruleset de Wazuh) — los consume, en el diseño, la Kriptome App.

## Alcance de este repositorio (qué NO está implementado)

Este repositorio contiene reglas, configuraciones, listas, fixtures, contratos de datos (schemas/políticas) y documentación. **No contiene:**

- Un backend o motor de casos funcionando.
- Una API productiva.
- Envío real de correos (las plantillas en `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` son texto, no un sistema de envío).
- Integración real con un proveedor de IA.
- Una base de datos productiva.
- Remediación automática (bloqueo, aislamiento de equipos, etc.).

Los `schemas` de `specifications/` y las `policies/` son **contratos para cuando esos componentes se construyan**, no una implementación parcial de ellos.
