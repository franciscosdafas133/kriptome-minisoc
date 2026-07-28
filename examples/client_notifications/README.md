# examples/client_notifications/ — ejemplos ilustrativos

**Todos los archivos de esta carpeta son ilustrativos y no representan eventos reales.** Se diseñaron a mano para validar los schemas de `specifications/`, no para documentar un incidente que haya ocurrido.

## Qué contiene cada trío

Por cada `case_type` de ejemplo (`AUTH_BRUTEFORCE_SUCCESS`, `VULNERABILITY`) hay 3 archivos:

- `*.input.json` — los objetos de entrada (`normalized_event`, `auth_evidence` o `enrichment_result`, `asset_context`, `risk_result`, `procedure`) que alimentarían la generación de una notificación, si existiera el código que hace esa generación.
- `*.output.json` — una instancia que cumple `specifications/client_notification.schema.json`, mostrando cómo se vería el resultado.
- `*.email.md` — el mismo contenido, renderizado como un correo legible.

## Por qué no fueron generados por un backend real

**No existe un backend implementado en este repositorio** (ver `README.md` raíz, sección "Qué NO está implementado"). Ningún archivo aquí pasó por un motor de casos, un clasificador de riesgo o un sistema de envío de correo real. Se escribieron directamente respetando los schemas, para servir de referencia de cómo debería verse el resultado final el día que ese código exista.

## Por qué `matching_user_verified=false` en el ejemplo de AUTH_BRUTEFORCE_SUCCESS

El ejemplo usa deliberadamente el caso **más común y menos ideal**: la regla `100013` (login Windows exitoso tras fuerza bruta) se apoya en la correlación nativa `60204`, que agrupa por dirección IP, no por cuenta de usuario (ver `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml`, nota técnica en esa regla). Por eso `auth_evidence.matching_user_verified=false`: los 10 intentos fallidos contados se correlacionaron por IP, no se verificó evento-por-evento que todos fueran contra la cuenta `administrador`.

Esto se refleja en el texto del correo (`datos_principales` y `body_sections`): en vez de afirmar *"detectamos 10 intentos contra la cuenta administrador"* (que sería una afirmación no verificada), el texto dice *"detectamos 10 intentos... y luego un acceso exitoso... usando la cuenta administrador"* — separando el conteo (por IP) del acceso (por cuenta). Ver la regla completa en `specifications/auth_evidence.schema.json` (`$comment`).

## Qué campos son simulados

- **Todos los identificadores** (`case_id`, `event_id`, `tenant_id`, `asset_id`) son ficticios.
- **Los datos de enriquecimiento externo** (`geo_country`, `geo_city`, `isp_or_asn`, `reputation_verdict`) aparecen como `null` en los ejemplos de fuerza bruta porque no hay una consulta real de GeoIP/reputación — ver `enrichment_pending` en el `normalized_event` de entrada.
- **El contenido del ejemplo de `VULNERABILITY`** usa un CVE y campos con el **formato real** verificado contra el feed público de CISA KEV (`https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`, consultado 2026-07-22) — el formato de los campos es real, pero el escenario (activo, tenant, fechas de detección) es ficticio.
- **El `procedure` de entrada de ambos ejemplos tiene `status: "draft"` y `approved_by: null`** — a propósito. Ningún procedimiento de `procedures/` ha sido aprobado por una persona real todavía (ver `procedures/README.md`). Los ejemplos de `action_plan` en los `.output.json` usan ese procedimiento en borrador únicamente para ilustrar la estructura del contrato — en una implementación real, un caso sin procedimiento **aprobado** debe ir a cola humana, no comunicarse con acciones improvisadas.

## Qué capacidades no existen todavía (lenguaje honesto)

Versiones anteriores de estos ejemplos afirmaban capacidades inexistentes en el texto del correo, como *"estamos revisando qué hizo esa cuenta"* o *"podemos bloquear la dirección de origen"*. Se corrigieron (v1.3.1) a lenguaje que describe únicamente lo que el estado actual del repositorio puede sostener: que el caso quedó **registrado y escalado para revisión humana**, no que un sistema automático ya está actuando. Ninguna acción de bloqueo, aislamiento o remediación se presenta como ya disponible — ver `README.md` raíz, sección "Qué NO está implementado".

## Cómo validar estos ejemplos

```bash
python scripts/validate_repository.py
```

o manualmente:

```python
import json, jsonschema
schema = json.load(open("specifications/client_notification.schema.json"))
instance = json.load(open("examples/client_notifications/AUTH_BRUTEFORCE_SUCCESS.output.json"))
jsonschema.validate(instance=instance, schema=schema)
```

Los objetos compuestos de los `*.input.json` (que agrupan varios objetos bajo una sola clave por conveniencia de lectura) no cumplen ningún schema individual como un todo — cada clave interna (`normalized_event`, `auth_evidence`, `asset_context`, `risk_result`, `procedure`, `enrichment_result`) se valida por separado contra su propio schema. Ver `scripts/validate_repository.py` para cómo se hace esa validación sección por sección.
