# Alcance y límites de la IA en Kriptome MiniSOC (v1.3.1)

`policy_validation_status: DISEÑADO`. Formaliza un principio que ya aparecía disperso en varios documentos (`docs/architecture/ARCHITECTURE_CANONICAL.md`, `specifications/procedure.schema.json`, `procedures/README.md`) en un único contrato: qué puede y qué NUNCA puede hacer la IA en este sistema, y cómo se audita cada uso.

## 1. Principio rector

> **La IA nunca es la fuente de verdad de tenant, severidad, procedimiento, estado o acción.** (`docs/architecture/ARCHITECTURE_CANONICAL.md`)

Todo lo demás en este documento es una consecuencia operativa de ese principio, no una excepción a él.

## 2. Intents permitidos (catálogo cerrado)

La IA solo puede invocarse para uno de estos propósitos explícitos. Un uso fuera de este catálogo requiere primero agregarse aquí, con su propia justificación y guardarraíles — no se invoca la IA para un propósito no listado "porque parece útil".

| `notification_intent` | Qué hace | Qué NO hace |
|---|---|---|
| `draft_initial_notification` | Redacta el borrador de la primera comunicación de un caso, a partir de `case_summary` + `procedure` YA aprobado + `risk_result` YA calculado. | No decide `priority_level`, no elige qué `procedure` aplica, no inventa acciones fuera de `customer_actions`/`internal_actions` del procedure. |
| `draft_material_change_update` | Redacta la actualización cuando un caso ya notificado tiene un `material_change` (ver `specifications/case.schema.json` `material_changes`). | No decide si algo cuenta como `material_change` — esa clasificación ya viene dada por `policies/case_types/*.yaml`. |
| `draft_closure_message` | Redacta el mensaje de cierre, a partir de `resolution_type` YA decidido (`specifications/case_state_machine.yaml`). | No decide `resolution_type`. |
| `summarize_for_operator` | Resume evidencia/contexto de un caso para lectura rápida de un operador humano (uso interno, nunca sale al cliente sin pasar por los demás intents). | No sustituye la revisión del operador; el resumen es un insumo, no una decisión. |
| `adapt_message_to_recipient` | Ajusta tono/nivel de detalle de un mensaje YA redactado y validado para un perfil de destinatario distinto (técnico vs no técnico, ver `recipient_profile_version`). | No cambia hechos, acciones, plazos ni cifras del mensaje original — solo forma, nunca contenido sustantivo. |

Cualquier salida de la IA bajo cualquier intent pasa por `Validator` + `Human Review if Required` antes de `Communication Policy` (ver el flujo canónico en `docs/architecture/ARCHITECTURE_CANONICAL.md`) — ningún intent de esta tabla se comunica directo al cliente sin ese paso.

## 3. Prohibiciones explícitas

La IA **nunca**:

1. Decide a qué `tenant_id` pertenece un evento (eso es `specifications/tenant_resolution.md`, backend puro).
2. Calcula o ajusta `priority_level` (eso es `policies/risk/risk_policy_v1.yaml`, determinístico).
3. Selecciona qué `procedure_id`/`procedure_version` aplica a un caso (eso es un match determinístico `case_type` + `priority_levels` + `applicable_conditions`, ver `specifications/procedure.schema.json`).
4. Decide el `status` o la transición de un caso (eso es `policies/case_state_machine.yaml`).
5. Inventa una `customer_action`/`internal_action` que no esté en el `Procedure` aprobado correspondiente (ver `procedures/README.md` regla dura 1).
6. Decide si algo es un `material_change` (eso ya viene resuelto por `policies/case_types/*.yaml` antes de que la IA vea el caso).
7. Envía un mensaje directamente al cliente sin pasar por el `Transactional Outbox` y sin que exista `human_review_required` resuelto (ver `docs/architecture/ARCHITECTURE_CANONICAL.md`).
8. Recibe datos de un tenant distinto al del caso que está procesando en la misma invocación (aislamiento multi-tenant también aplica al contexto que se le da a la IA, no solo a las consultas del Indexer/Postgres).

## 4. Composición de `ai_input_hash` (v1.3.1, ampliada)

`specifications/case.schema.json` define `ai_input_hash` como "hash del contexto mínimo enviado a la IA", reutilizado si no cambia (evita re-pagar la IA en repeticiones, doc 03 nivel de control 7). La versión v1.3.1 formaliza los componentes exactos que entran en ese hash, para que "no cambió" sea una afirmación verificable y no una intuición:

```
ai_input_hash = hash(
    case_material_version,       # versión del contenido sustantivo del caso (resumen/evidencia) usado como insumo
    risk_policy_version,          # policies/risk/risk_policy_v1.yaml -- si cambia la política, el hash cambia aunque el caso no
    procedure_id,
    procedure_version,            # ver specifications/procedure.schema.json
    notification_intent,          # cuál de los 5 intents del catálogo (§2) se está invocando
    recipient_profile_version,    # versión del perfil de destinatario (técnico/no técnico) usado por adapt_message_to_recipient
    prompt_version                # versión del prompt/plantilla de instrucción usado para invocar el modelo
)
```

**Por qué cada componente importa:**

- `case_material_version` + `risk_policy_version` + `procedure_id`/`procedure_version`: si cualquiera de estos cambia, el contexto sustantivo que vería la IA es distinto, aunque el `case_id` sea el mismo — reutilizar una salida vieja sería servir un mensaje basado en información obsoleta.
- `notification_intent`: dos intents distintos sobre el mismo caso no deben compartir hash ni salida cacheada (redactar un cierre no es lo mismo que redactar una actualización).
- `recipient_profile_version`: la misma decisión de contenido puede requerir dos redacciones distintas (perfil técnico vs no técnico) — no son intercambiables aunque el resto del contexto sea idéntico.
- `prompt_version`: si se ajusta la plantilla/instrucción dada al modelo (mejora de redacción, corrección de un error de tono), las salidas viejas no deben confundirse con las nuevas bajo el mismo hash — un cambio de prompt invalida la caché.

## 5. Controles de inyección de prompt (prompt injection)

`policy_validation_status: DISEÑADO`, sin herramienta implementada. Controles mínimos requeridos antes de que cualquier intent de §2 se conecte a una fuente de texto no controlada por Kriptome (p. ej. contenido de un correo entrante, un campo de texto libre de un formulario, contenido de log crudo con `full_log`):

1. **Separación estricta de instrucción y dato**: el contenido de terceros (evidencia cruda, texto de un correo entrante) se pasa siempre como dato delimitado explícitamente, nunca concatenado directamente a la instrucción del sistema.
2. **La salida de la IA nunca se interpreta como instrucción de control**: un texto generado (o citado desde una fuente externa) no puede, por su propio contenido, cambiar el `notification_intent`, el `procedure_id` aplicado, ni ningún campo de las prohibiciones de §3 — esos valores llegan siempre por el pipeline determinístico, nunca extraídos del texto libre por la propia IA.
3. **Detección de intentos de instrucción embebida**: contenido de terceros que contenga patrones típicos de instrucción a un modelo (p. ej. "ignora las instrucciones anteriores", bloques que imitan un system prompt) se marca para revisión humana, no se descarta en silencio ni se ejecuta.
4. Relación directa con `docs/architecture/EMAIL_THREAD_SECURITY.md` (Fase 21): el vector más probable de prompt injection en este sistema es contenido de correos entrantes de clientes o remitentes no verificados — ver ese documento para los controles de la capa de email específicamente.

## 6. Auditoría

Toda invocación de IA queda registrada (ver `docs/architecture/AUDIT_AND_OUTBOX.md`, Fase 23) con al menos: `case_id`, `notification_intent`, `ai_input_hash` completo (los 7 componentes de §4, no solo el hash final), `prompt_version`, resultado de `Validator`, y si requirió `Human Review`. Esto permite reconstruir, para cualquier mensaje enviado, exactamente qué contexto determinístico lo originó — la IA mejora la redacción, la auditoría demuestra que nunca decidió el contenido de negocio.

## 7. Estado de este documento

`policy_validation_status: DISEÑADO`. No existe hoy un pipeline de IA implementado que siga este contrato, ni un validador de prompt injection funcionando — es el diseño que cualquier implementación futura del bloque "Deterministic Template or Optional LLM" (`docs/architecture/ARCHITECTURE_CANONICAL.md`) debe cumplir.
