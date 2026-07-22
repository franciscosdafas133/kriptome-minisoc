# REPO_ALIGNMENT_REPORT.md

Reporte de inventario y alineación técnica del repositorio `kriptome-minisoc` contra los 7 documentos funcionales de `DOCUMENTOS/` (fuente de verdad, no modificados por este trabajo).

Generado: 2026-07-22 · Wazuh base de referencia: v4.14.6 (verificado vía sparse-checkout oficial `wazuh/wazuh` tag `v4.14.6`, código fuente `src/analysisd/rules.c` incluido).

---

## 1. Inventario de archivos (estado antes de este trabajo)

### DOCUMENTOS/ (7 documentos + 3 auxiliares — NO tocados, fuente funcional)

| Archivo | Rol |
|---|---|
| `00_INFORME_FINAL.docx` | Ejecutivo |
| `01_ARQUITECTURA_Y_DISENO.docx` | Arquitectura, multi-tenant, seguridad |
| `02_DETECCION_Y_REGLAS.docx` | 15 familias, routing, política IA |
| `03_FLUJOS_OPERATIVOS.docx` | Flujo end-to-end, 7 niveles de control, onboarding |
| `04_MANUAL_DE_USUARIO.docx` | Manual operador + cliente |
| `05_COSTOS_Y_VIABILIDAD.docx` | Presupuesto |
| `06_PLAN_IMPLEMENTACION_NUBE.docx` | Plan 4 semanas, gaps G1–G12 |
| `07_COMUNICACION_CON_EL_CLIENTE.docx` | Plantillas de correo, niveles, escalamiento |
| `_INDICE_POR_ETAPAS.docx`, `_LEEME_PRIMERO.docx` | Índices de navegación |

Nota: el prompt que originó este reporte menciona "siete documentos" — el paquete `DOCUMENTOS/` contiene 8 documentos numerados (00–07) más 2 índices. Los 8 numerados se tratan como fuente funcional única; ninguno fue editado.

### REGLAS_TUNEADAS/ (paquete técnico desplegable — auditado en este trabajo)

| Archivo | Tipo | Duplicado/obsoleto |
|---|---|---|
| `rules/kriptome_local_rules.xml` | Reglas custom (5 reglas: 100010–100013, 100030, 100040) | No |
| `decoders/kriptome_local_decoders.xml` | Decoder custom | Vacío a propósito (documentado en el propio archivo: todos los campos usados ya los produce el decoder nativo) |
| `config/ossec.conf.ruleset.snippet.xml` | Bloque `<ruleset>` para el Manager | No |
| `agent-conf/kriptome-baseline_agent.conf` | Config FIM/syscheck compartida | No |
| `agent-conf/CLI-001_agent.conf.example` | Ejemplo de labels por cliente | No |
| `lists/kriptome-cisa-kev` | Lista CDB, 3 CVEs de ejemplo | **Es un fixture, no un feed real** (ver §2.3) |
| `lists/kriptome-fim-whitelist` | Lista CDB, 2 rutas de ejemplo | No |
| `routing/routing_matrix.csv` | 64 filas, 15 familias | No |
| `routing/diccionario_campos_enriquecimiento.csv` | Campos por familia, verificados contra decoders reales | No |
| `test_data/ssh_samples.log` | Fixture SSH (11 líneas) | No |
| `test_data/sudo_pam_samples.log` | Fixture sudo/PAM (4 líneas) | No |
| `test_data/windows_4625_eventchannel.json` | Fixture Windows (11 eventos JSON) | No |
| 6 archivos `.docx` (EXPLICACION_DEL_TUNING, GUIA_DE_DESPLIEGUE, GUIA_LISTAS, GUIA_CAMPOS_ENRIQUECIMIENTO, PROCEDENCIA_WAZUH, RESULTADOS_ESPERADOS) | Documentación de soporte del paquete técnico | No — no son los 7/8 documentos funcionales de negocio, son manuales operativos del ruleset. No modificados. |

**No se encontraron archivos duplicados, huérfanos ni restos de versiones anteriores.** El repo ya estaba en un estado limpio (validado en sesiones previas con 44+ checks automatizados).

---

## 2. Hallazgos de alineación técnica

### 2.1 `same_source_ip` vs `same_srcip` — VERIFICADO EN CÓDIGO FUENTE, NO ES UN BUG

Se verificó `src/analysisd/rules.c` (líneas 169-170 y 1019-1020) del tag oficial `v4.14.6`:

```c
const char *xml_same_source_ip = "same_source_ip";
const char *xml_same_srcip = "same_srcip";
...
} else if (strcasecmp(..., xml_same_source_ip) == 0 ||
           strcasecmp(..., xml_same_srcip) == 0) {
    config_ruleinfo->same_field |= FIELD_SRCIP;
```

**Ambos tags son aliases reconocidos por el parser real de Wazuh — producen el mismo efecto exacto (`FIELD_SRCIP`).** El ruleset oficial de Wazuh usa `<same_source_ip/>` (0 apariciones de `<same_srcip/>` en `ruleset/rules/*.xml` del tag oficial). El XML actual de Kriptome (`100012`) usa `<same_source_ip/>`, que es el tag preferido por el propio ruleset upstream.

**Decisión tomada:** NO se reemplaza `same_source_ip` por `same_srcip` como si fuera una corrección de bug, porque no lo es — haría que el XML se desviara del estilo del ruleset oficial que audita este mismo proyecto (`PROCEDENCIA_WAZUH.docx`), sin ganancia funcional. Se documenta la equivalencia en `rules/kriptome_local_rules.xml` para que quede explícito y no se reabra la duda en el futuro.

### 2.2 Regla 100040 (CISA KEV) — movida a experimental

La regla depende de una lista CDB (`kriptome-cisa-kev`) que hoy contiene **3 CVE-IDs de ejemplo**, no un feed real automatizado. Además, el propio archivo `kriptome_local_rules.xml` (comentario original de la regla) ya señalaba una decisión de arquitectura pendiente: "elige UNA fuente de verdad (regla CDB o App) para evitar 2 casos" — esa decisión nunca se tomó.

**Acción:** la regla se movió a `REGLAS_TUNEADAS/experimental/100040_cisa_kev.xml`, deshabilitada por defecto (fuera del `<group>` que carga el Manager), con cabecera que documenta:
- Que el enriquecimiento KEV en producción se resuelve en la Kriptome App (arquitectura #8, doc 01), no como segunda regla de Wazuh.
- Que activarla en paralelo a la App abriría un caso duplicado por el mismo evento.
- Que la lista `kriptome-cisa-kev` es un fixture (§2.3), no apta para producción sin automatizar el feed.

### 2.3 Lista `kriptome-cisa-kev` — marcada como fixture de prueba

Contiene 3 CVE-IDs reales pero fijos (Log4Shell, Outlook, PAN-OS), sin mecanismo de actualización automatizado implementado. Movida conceptualmente a fixture: se documenta en `REGLAS_TUNEADAS/README.md` y en la cabecera del archivo que **no es el feed real** — el feed real requiere el cron diario contra el catálogo CISA KEV descrito en `GUIA_LISTAS.docx`, no construido en este repo.

### 2.4 Correo M365 (familia 15) — confirmado PEND-INTEGRACION

Ya estaba correctamente marcado como tal en `routing_matrix.csv` y `diccionario_campos_enriquecimiento.csv`. Se mantiene sin cambios de fondo; se normaliza únicamente el token de estado (ver §3).

### 2.5 IDs de Active Directory para grupos sensibles — confirmado PENDIENTE

La fila `Active Directory,4740/4728/4732/4756` en `routing_matrix.csv` ya traía la nota `"FALTA REVISAR IDs exactos en 0580 (marcado NO VERIFICADO)"`. Verificación realizada en esta sesión contra `ruleset/rules/0580-win-security_rules.xml` del tag v4.14.6: los IDs 4728/4732/4756 **sí existen** (confirmado línea 159-163 y 466-584 del archivo), pero el campo textual del nombre del grupo (`win.eventdata.targetGroupName`) depende de la política de auditoría de Windows del cliente — no siempre presente. Se mantiene el estado como **PENDIENTE** (no se sube a VALIDADO-XML) porque la verificación de los IDs es parcial: falta confirmar en un Manager real que el campo de nombre de grupo llega poblado con la configuración de auditoría típica de una PyME.

### 2.6 Snippet `ossec.conf` y decoders custom

Sin hallazgos nuevos. El snippet ya mantenía paridad con el default de v4.14.6 (verificado en trabajo previo contra `etc/templates/config/generic/rules.template`). El decoder custom vacío está correctamente justificado y no requiere cambios.

---

## 3. Normalización de estados de validación

Vocabulario anterior en uso: `VALIDADO-XML`, `PEND-LOGTEST`, `PEND-SHADOW`, `NO VERIFICADO`, `PENDIENTE`, `OPCIONAL`, `CUSTOM fix`, `CUSTOM keep`, `RETUNE`, `POBLAR lista` (mezclado libremente entre comentarios de código y CSV).

Vocabulario normalizado (ver `specifications/validation_statuses.md` para definiciones completas):

```
DISEÑADO · CONFIGURADO · VALIDADO-DOCUMENTALMENTE · VALIDADO-XML ·
VALIDADO-LOGTEST · VALIDADO-SHADOW · VALIDADO-PILOTO · PENDIENTE ·
EXPERIMENTAL · PEND-INTEGRACION
```

Mapeo aplicado (ningún estado fue promovido a un nivel superior de evidencia — solo se tradujo el token):

| Estado anterior | Estado normalizado | Regla aplicada |
|---|---|---|
| `VALIDADO-XML` | `VALIDADO-XML` | Sin cambio — ya significaba "comprobado contra el XML nativo" |
| `PEND-LOGTEST` | `PENDIENTE` (sub-nota: requiere VALIDADO-LOGTEST) | No hay evidencia de logtest guardada en el repo — no se puede marcar VALIDADO-LOGTEST |
| `PEND-SHADOW` | `PENDIENTE` (sub-nota: requiere VALIDADO-SHADOW) | No hay evidencia de shadow mode guardada — no se puede marcar VALIDADO-SHADOW |
| `NO VERIFICADO` | `PENDIENTE` | Equivalente directo |
| `OPCIONAL` (100030, 100040) | se retira como estado; pasa a nota de alcance | No es un estado de validación, es una decisión de producto — se documenta aparte |
| `PEND-INTEGRACION` (M365) | `PEND-INTEGRACION` | Sin cambio — ya en el vocabulario objetivo |
| — (routing_matrix, sin estado explícito por fila) | se añade columna `EstadoValidacion` | Ver `routing/routing_matrix.csv` — no se modificó el CSV original; la columna adicional vive en `specifications/` para no tocar el archivo fuente sin necesidad (ver §4) |

**Regla aplicada estrictamente en todo el repo:** ninguna regla fue marcada `VALIDADO-LOGTEST`, `VALIDADO-SHADOW` o `VALIDADO-PILOTO` porque **no existe evidencia de ejecución guardada** en este repositorio (no hay logs de salida de `wazuh-logtest`, no hay capturas de shadow mode, no hay reporte de piloto). Esto es consistente con el estado real del proyecto: nunca se ha desplegado en un Manager.

---

## 4. Decisión de diseño: routing_matrix.csv y diccionario NO fueron reescritos

Los archivos `routing/routing_matrix.csv` y `routing/diccionario_campos_enriquecimiento.csv` ya estaban verificados campo-por-campo contra el código fuente de Wazuh (ver historial: 44 checks automatizados en sesión previa). Reescribirlos para insertar columnas de estado habría arriesgado introducir inconsistencias en un artefacto ya validado y consumido por `DOCUMENTOS/02_DETECCION_Y_REGLAS.docx` (que cita sus conteos exactos: 64 filas, 15 familias). En su lugar:

- Los estados de validación por familia se documentan en `policies/case_types/*.yaml` (nuevo, ver §6 de la entrega) sin duplicar ni contradecir el CSV existente.
- El CSV permanece como fuente única de verdad para routing; los nuevos artefactos de `specifications/` y `policies/` lo referencian por `case_type`, nunca lo repiten con datos distintos.

---

## 5. Resumen de riesgo residual (sin resolver en este trabajo, por diseño)

| Riesgo | Por qué sigue abierto |
|---|---|
| Ninguna regla ha corrido contra un Manager real | Requiere infraestructura desplegada; fuera del alcance de "no inventar resultados de pruebas" |
| Aislamiento multi-tenant en correlaciones (`same_source_ip` sin `agent.labels.client_id`) | Ya documentado como riesgo conocido en el XML original; requiere confirmar con `wazuh-logtest` si el campo es accesible en tiempo de regla |
| Feed real de CISA KEV no automatizado | La lista actual es fixture; automatizar el cron es trabajo de integración, no de este repo |
| Integración M365 (wodle office365) no configurada | PEND-INTEGRACION; requiere credenciales de tenant real de un cliente |

Ninguno de estos se "resuelve" en esta pasada — se documentan con su estado real para que la siguiente persona/sesión no reabra la investigación desde cero.
