# Resolución de tenant (multi-tenant, seguridad)

Contrato de cómo se resuelve `tenant_id` a partir de un evento crudo de Wazuh, y las reglas de seguridad que ningún componente debe romper. Basado en `DOCUMENTOS/01_ARQUITECTURA_Y_DISENO.docx` (arquitectura #6) y en la nota "AISLAMIENTO MULTI-TENANT EN CORRELACIONES" de `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml` (estado: PENDIENTE). No implica un backend implementado — es el contrato que ese backend debe cumplir cuando se construya. Ver `implementation/multi_tenant_two_tenant_plan.md` para el plan de aplicación concreta con dos tenants piloto, `specifications/tenant_resolution.schema.json` para el contrato de datos formal del resultado de esta resolución, y `specifications/tenant_identifier_migration.md` para la separación `tenant_id`/`client_code` aplicada en v1.3.1.

## 1. Cadena de resolución y autoridad de cada fuente

```
evento crudo de Wazuh
  -> agent.id                    (identificador TÉCNICO del agente)
  -> manager_group                (asignación OPERATIVA en el Manager)
  -> agent.labels.client_code     (código legible que DEBE coincidir con manager_group)
  -> tenant registry              (fuente de verdad de NEGOCIO -- specifications/tenant.schema.json)
  -> tenant_id                    (resuelto en BACKEND, nunca aceptado directo del evento/frontend)
  -> asset registry               (fuente de verdad del ACTIVO -- specifications/tenant_asset_assignment.schema.json)
  -> asset_id
```

Cada eslabón tiene una autoridad distinta — la resolución **no debe confiar únicamente en una etiqueta enviada por el agente**:

| Eslabón | Qué es | Autoridad |
|---|---|---|
| `agent.id` | Identificador técnico del agente, siempre presente y puesto por Wazuh (ver `specifications/wazuh_alert_field_paths.md`). | VALIDADO-XML (Wazuh lo garantiza). No es autoridad de negocio por sí solo -- solo identifica el agente. |
| `manager_group` | Asignación operativa del agente a un grupo en el Manager (ver `docs/architecture/WAZUH_GROUP_PRECEDENCE.md` y `REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example`). | Autoridad OPERATIVA -- refleja a qué grupo se asignó el agente en el Manager, gestionado por quien administra Wazuh. Más confiable que el label auto-reportado, porque cambiar el grupo de un agente requiere acceso al Manager, no solo editar el propio agente. |
| `agent.labels.client_code` | Código legible que el agente reporta en sus eventos (ver `specifications/tenant_identifier_migration.md` -- ya NO se llama `client_id`). | Autoridad DECLARATIVA, no de verdad -- debe **coincidir** con `manager_group` (ver §3). Si no coincide, es una inconsistencia que dispara cuarentena, no un desempate a favor del label. |
| `tenant registry` (`specifications/tenant.schema.json`) | Registro de negocio de quién es cada tenant, su estado comercial y su plan. Clave primaria `tenant_id`; `client_code` es un campo del mismo registro, no la clave. | Fuente de verdad de NEGOCIO. Un `client_code` que no tiene un `tenant` correspondiente en estado `active` no debe generar notificaciones reales. |
| `asset registry` (`specifications/tenant_asset_assignment.schema.json`) | Registro de qué `asset_id` pertenece a qué `tenant_id`, vinculado a un `agent_id`/`manager_group` concretos. | Fuente de verdad del ACTIVO. Un `asset_id` sin asignación `verified` en este registro no debe procesarse como perteneciente a ningún tenant. |

**Regla de seguridad #1: `tenant_id` se resuelve SIEMPRE del lado del backend consultando el tenant registry y el asset registry — nunca se acepta un `tenant_id` que venga ya puesto en el payload de un frontend, una API pública, un campo editable por el cliente, o incluso el label `agent.labels.client_code` sin verificar contra `manager_group`.** Esto es consistente con doc 01 §5: "ninguna consulta al Indexer corre sin tenant... el tenant se resuelve en backend; el label es la fuente de esa evidencia" -- y se refina en v1.3.1: el label es un DATO DE ENTRADA a verificar, no la autoridad final.

**Regla de seguridad #1-bis (v1.3.1): nunca usar `assert` como control de esta resolución.** Un `assert` (o equivalente) puede desactivarse por configuración del intérprete/entorno (p. ej. Python con `-O`), silenciando el control de seguridad sin que se note en producción. El patrón correcto es una excepción explícita que el código de negocio siempre evalúa:

```python
if not tenant_id:
    raise TenantRequiredError("tenant_id is required")
```

nunca:

```python
assert tenant_id  # INCORRECTO: puede desactivarse en producción
```

## 2. Estado de verificación de `agent.labels.client_code` en tiempo de regla

**PENDIENTE** (no `VALIDADO-XML`). El propio `kriptome_local_rules.xml` documenta esto como riesgo conocido sin resolver: las correlaciones nativas y custom que usan `same_source_ip` / `same_field` acumulan por valor de IP a nivel de TODO el Manager, sin segmentar por `agent.labels.client_code`, porque no está confirmado con `wazuh-logtest` que ese campo sea accesible en tiempo de evaluación de regla en la versión desplegada. Mientras esto sea `PENDIENTE`:

- El **conteo** de una correlación (p. ej. "8 fallos en 120s") puede mezclar eventos de dos tenants distintos si comparten la misma IP atacante dentro de la ventana.
- La **atribución del caso** (a qué cliente pertenece) nunca se mezcla, porque eso se re-resuelve en el backend/App por `tenant_id` real al construir el caso — el riesgo es solo en el contador de la correlación de Wazuh, no en el caso final.

## 3. Comparación con labels (verificación de consistencia)

Antes de aceptar un evento como válido para abrir/actualizar un caso, el backend debe comprobar, en orden, los 6 checks siguientes, produciendo un `TenantResolutionResult` (`specifications/tenant_resolution.schema.json`):

1. **`agent.id` registrado** — el agente que originó el evento existe en el registro de agentes del Manager (no es un `agent.id` desconocido o falsificado). Si falla: `resolution_status=missing_agent`.
2. **`manager_group` válido** — el agente pertenece a un grupo Wazuh reconocido (no está en `default`, ver Regla de seguridad #2 en §4 más abajo). Si falla: `resolution_status=group_mismatch`.
3. **`agent.labels.client_code` coincide con `manager_group`** — el código legible que el agente reporta en sus eventos corresponde al grupo Wazuh real al que fue asignado en el Manager. Si falla: `resolution_status=label_mismatch`.
4. **`asset_id` registrado** — existe un registro válido en el asset registry (`specifications/tenant_asset_assignment.schema.json`) para el `asset_code` observado, no solo "presente y no vacío" como campo de texto. Si falla: `resolution_status=missing_assignment` o `missing_label`.
5. **El asset pertenece al tenant** — la asignación en `tenant_asset_assignment` para ese `asset_id` tiene `tenant_id` igual al resuelto en el paso 3, y `assignment_status='verified'` (ver regla de integridad de unicidad en ese schema: un `asset_id` no puede estar `verified` para dos tenants a la vez). Si falla: `resolution_status=ambiguous_assignment`.
6. **Tenant y asset activos** — el `tenant_id` resuelto corresponde a un registro en el tenant registry (`specifications/tenant.schema.json`) con `status='active'`, y el activo no está `decommissioned`. Un tenant en `draft`, `suspended`, `offboarding` o `closed` no debe generar notificaciones reales al cliente (aunque sí puede seguir indexando eventos para trazabilidad, según la política operativa que se defina). Si falla: `resolution_status=inactive_tenant` o `inactive_asset`.

Si los 6 checks pasan: `resolution_status=resolved` y el evento sigue el flujo normal.

## 4. Cuarentena por inconsistencia

Si **cualquiera** de los 6 checks del §3 falla, el evento **NO se descarta silenciosamente ni se asigna a un tenant por defecto**. El resultado (`resolution_status != resolved`, con `mismatches` poblado) dispara:

```
→ quarantine/dead-letter
→ audit
→ no case
→ no IA
→ no communication
```

Equivalente al `dead_letter` descrito en `DOCUMENTOS/03_FLUJOS_OPERATIVOS.docx` §1 (flujo end-to-end: `tenant inválido -> Dead letter + alerta interna`), con las mismas reglas:

- Se registra el evento completo para investigación manual.
- Se genera una alerta interna al operador (no al cliente).
- Existe un umbral de atención: más de N eventos en cuarentena en 15 minutos dispara revisión inmediata (doc 03 §8, "dead_letter tiene además alerta automática por umbral").

**Regla de seguridad #2: ningún agente productivo puede quedar en el grupo `default` de Wazuh** (doc 03 §5.2, actualizado: "ningún agente productivo queda en grupo 'default'; toda alerta debe traer client_code + asset_code, resueltos a tenant_id + asset_id reales"). Un agente en `default` es, por definición, un caso de `resolution_status=group_mismatch` → cuarentena.

## 5. Prohibición explícita: `tenant_id` del frontend nunca es autoridad

Ningún componente (Kriptome App, API futura, dashboard de operador) puede:

- Aceptar un `tenant_id` enviado por un cliente HTTP como valor de verdad para filtrar datos.
- Usar un `tenant_id` de sesión de usuario como sustituto de la resolución `agent_id -> labels -> tenant_id` para consultas al Indexer.

El `tenant_id` de sesión (con qué cliente está autenticado un operador o un usuario) solo se usa para **autorización** (qué tenant puede ver ese usuario), nunca para **resolución** (a qué tenant pertenece un evento). Son dos preguntas distintas y no deben compartir el mismo campo de confianza.

## 6. Filtros por tenant en consultas — matizado en v1.3.1

**Corrección respecto a versiones previas de este documento:** la afirmación "toda consulta al Indexer lleva tenant, sin excepción" era una simplificación que entraba en contradicción con la necesidad de que *algo* lea eventos sin tenant resuelto todavía para poder clasificarlos. La versión correcta, ver `docs/architecture/INDEXER_ACCESS_MODEL.md` para el detalle completo:

- El **Global Internal Ingestor** (servicio interno, sin endpoint público) SÍ puede leer eventos sin `tenant_id` resuelto — precisamente porque su función es detectarlos y clasificarlos (ejecutar la cadena de resolución de este documento). No es una excepción a la regla de aislamiento; es el componente que la hace cumplir.
- **Todas las demás consultas** (construcción de casos, consultas del operador, cualquier endpoint de reporting/dashboard) son estrictamente `tenant_id`-scoped, sin excepción, y ese filtro lo construye el backend — nunca lo elige el frontend ni un DSL libre.

**No existe un modo "todos los tenants" para consultas funcionales**, fuera del Global Internal Ingestor (que no expone datos de eventos por cliente hacia afuera, solo los clasifica) y de tareas de mantenimiento explícitas del Manager (backups, salud del Indexer).

## 7. Estado de este documento

`policy_validation_status: DISEÑADO`. Es un contrato de arquitectura extraído de decisiones ya tomadas en `DOCUMENTOS/01` y `03`, más el riesgo conocido de `kriptome_local_rules.xml`. No hay backend implementado que lo cumpla todavía — ver `README.md` §"Qué NO está implementado".
