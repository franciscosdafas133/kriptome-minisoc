# Vocabulario de estados de validación

Único vocabulario permitido en todo el repositorio (reglas XML, CSVs, políticas, specs). Reemplaza el vocabulario libre anterior (`PEND-LOGTEST`, `PEND-SHADOW`, `NO VERIFICADO`, `OPCIONAL` usado como estado).

| Estado | Significado | Evidencia requerida para usarlo |
|---|---|---|
| `DISEÑADO` | Especificado en los documentos funcionales (00–07) o en una política/schema, pero sin ninguna verificación técnica todavía. | Ninguna — es el punto de partida. |
| `CONFIGURADO` | El artefacto existe y está sintácticamente completo (un archivo de configuración, una política, un schema), pero no se comprobó contra el código fuente real de Wazuh ni contra un Manager. | El archivo existe en el repo. |
| `VALIDADO-DOCUMENTALMENTE` | Se comprobó por lectura cruzada entre documentos (p. ej. el routing_matrix coincide con lo que dice doc 02), sin tocar código fuente ni un Manager. | Referencia cruzada explícita entre al menos 2 artefactos del repo. |
| `VALIDADO-XML` | Se comprobó línea por línea contra el ruleset/decoders/código fuente oficial de Wazuh (un tag específico, p. ej. v4.14.6), sin ejecutar nada. | Cita del archivo y línea del ruleset oficial verificado (ver ejemplos en `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml`). |
| `VALIDADO-LOGTEST` | Se ejecutó `wazuh-logtest` contra el fixture correspondiente en un Manager real, y la salida quedó guardada en el repo (no solo se afirma que "debería" disparar). | Archivo de salida real de `wazuh-logtest` adjunto o referenciado, con fecha y versión de Wazuh usada. |
| `VALIDADO-SHADOW` | Se observó en modo shadow (sin enviar correos) durante un periodo, con métricas de volumen/falsos positivos registradas. | Reporte de shadow mode con fechas, cliente/entorno y datos observados. |
| `VALIDADO-PILOTO` | Se operó en producción real con al menos un cliente piloto y hubo revisión humana del resultado. | Reporte de piloto con casos reales gestionados. |
| `PENDIENTE` | Se sabe qué falta validar y a qué nivel, pero no se ha hecho todavía. Es el estado por defecto para todo lo que hoy dice "requeriría X" sin que X haya ocurrido. | Ninguna — es honestidad sobre ausencia de evidencia. |
| `EXPERIMENTAL` | Existe una decisión de producto/arquitectura sin resolver que impide cargar el artefacto en producción, independientemente de si su sintaxis es correcta. | Debe citar la decisión pendiente específica (ver `REGLAS_TUNEADAS/experimental/100040_cisa_kev.xml` como ejemplo). |
| `PEND-INTEGRACION` | El artefacto depende de una integración externa no configurada todavía (credenciales de un tenant, un wodle, una API). No es que falte "probarlo" — falta que exista la conexión misma. | Debe nombrar la integración exacta que falta (p. ej. "wodle office365 con credenciales del tenant del cliente"). |

## Reglas de uso

1. **Nunca se sube un estado sin la evidencia que ese nivel exige.** Si no hay un log de `wazuh-logtest` guardado, no se puede escribir `VALIDADO-LOGTEST` aunque "debería funcionar".
2. **Un artefacto puede tener dos estados simultáneos en capas distintas** (p. ej. `VALIDADO-XML` en su sintaxis, `PENDIENTE` en su comportamiento en un Manager real) — se escriben ambos, no se colapsan en uno solo.
3. **`EXPERIMENTAL` no es sinónimo de "roto".** Puede ser una regla perfectamente válida sintácticamente (`VALIDADO-XML`) que no se activa por una decisión de negocio/arquitectura sin tomar.
4. **Este vocabulario no inventa madurez.** Su propósito es que cualquier persona que lea el repo sepa exactamente qué se comprobó y qué no, sin tener que releer el historial de conversación que lo produjo.
