# procedures/ — Catálogo de procedimientos autorizados

Contratos de datos que cumplen `specifications/procedure.schema.json`. Cada uno define las acciones que se pueden comunicar al cliente para un `case_type`, incluyendo qué hacer, qué no hacer y — cuando la acción correcta depende de una circunstancia real del incidente — reglas condicionales (`decision_points`) en vez de reglas universales sin contexto.

## Estado actual: todos en `draft`

Los 6 procedimientos de este directorio (`PROC-AUTH-001`, `PROC-MALWARE-001`, `PROC-FIM-001`, `PROC-AGENT-001`, `PROC-VULN-001`, `PROC-VULN-KEV-MC-001`) tienen:

```yaml
status: draft
approved_by: null
approved_at: null
```

**Esto es intencional y obligatorio.** Ningún procedimiento de este repositorio ha sido revisado ni aprobado por una persona real. Marcarlos como `approved` sin que eso haya ocurrido sería simular una garantía de calidad que no existe — el mismo error que se corrigió en v1.3.1, donde ejemplos anteriores usaban `approved_by: "EJEMPLO-NO-REAL"` con `status: "approved"`.

## Quién debe aprobarlos

Un procedimiento pasa de `draft` a `approved` cuando una persona con responsabilidad operativa sobre el servicio (el Lead SOC o el responsable técnico del proyecto, según se defina en el modelo operativo de `DOCUMENTOS/03_FLUJOS_OPERATIVOS.docx`) lo revisa línea por línea y confirma que:

- Las `customer_actions` son seguras y realizables por un cliente sin conocimiento técnico (o con el apoyo de su proveedor de TI).
- Los `decision_points` cubren las circunstancias reales que pueden presentarse, sin dejar vacíos que fuercen una decisión improvisada.
- Ninguna acción afirma una capacidad que Kriptome no tiene hoy (ver `examples/client_notifications/README.md` sobre lenguaje honesto).
- `human_review_required` y `out_of_band_confirmation_required` están correctamente marcados para las acciones sensibles.

## Qué evidencia requiere la aprobación

No un simple "se ve bien". La aprobación debe registrar:

- Quién revisó (`approved_by`, un nombre o identificador real, nunca un placeholder).
- Cuándo (`approved_at`, fecha real de la revisión).
- Idealmente, referencia a la conversación/documento donde se discutió el procedimiento (fuera del alcance de este schema hoy, pero recomendado como práctica).

## Cómo se versionan

Cada archivo tiene `procedure_version` (string). Un cambio de contenido en las acciones, `decision_points` o `do_not_do` de un procedimiento **ya aprobado** debe incrementar `procedure_version` y volver a pasar por aprobación — no se edita un procedimiento aprobado in situ sin nueva revisión.

## Cómo se retiran

Un procedimiento que ya no debe usarse pasa a `status: deprecated` (no se elimina el archivo, por trazabilidad de qué procedimiento se usó en casos históricos). Ver el patrón aplicado a `policies/case_types/VULNERABILITY_KEV.yaml` como ejemplo de deprecación con puntero al reemplazo.

## `PROC-VULN-001` vs `PROC-VULN-KEV-MC-001`

Ambos comparten `case_type: VULNERABILITY` (fingerprint estable, ver `policies/case_types/VULNERABILITY.yaml`) pero cubren momentos distintos del ciclo de vida del mismo caso:

- **`PROC-VULN-001`**: procedimiento general, cubre la primera notificación en cualquiera de las clasificaciones (`generic`/`kev`/`ransomware_related`/`unsupported_product`) vía `decision_points.vulnerability_classification`.
- **`PROC-VULN-KEV-MC-001`**: procedimiento específico para el `material_change` "un caso ya notificado como `generic` escala a `kev`" (ver `policies/case_types/VULNERABILITY.yaml` `material_changes`) — regula específicamente la **comunicación de actualización** de un caso existente, no una primera notificación. `applicable_conditions` deja explícito que solo aplica si el caso ya fue notificado antes como genérico.

## Reglas duras

1. **Un procedimiento en `status: draft` NO puede ser la fuente de `action_plan` en una notificación real al cliente.** `specifications/client_notification.schema.json` documenta esta regla explícitamente en `action_plan.description`.
2. **Antes del piloto con los dos tenants** (ver `implementation/multi_tenant_two_tenant_plan.md`), debe existir aprobación humana real de al menos los procedimientos de los `case_type` que se esperan activar en el piloto. Sin esa aprobación, cualquier caso de esos tipos debe ir a cola humana con acciones decididas caso por caso, no comunicarse con un procedimiento no aprobado.
3. **Ninguna acción condicional se colapsa a una regla universal.** Si una acción depende de una circunstancia observable (¿hay una sesión activa?, ¿el cliente puede aislar el equipo?), va en `decision_points`, nunca en `do_not_do` como una prohibición sin contexto.
