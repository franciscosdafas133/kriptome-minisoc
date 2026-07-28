# Modelo de grupos Wazuh y precedencia de configuración (v1.3.1)

`policy_validation_status: DISEÑADO`. Contrato de arquitectura, NO implica que estos grupos existan hoy en un Manager real. Documenta cómo DEBEN nombrarse y ordenarse los grupos Wazuh para que la configuración de un Manager compartido (multi-tenant) sea predecible y auditable, y para que `docs/architecture/ARCHITECTURE_CANONICAL.md` / `specifications/tenant_resolution.md` puedan referenciar `manager_group` sin ambigüedad.

Ver también: `specifications/tenant_resolution.md` §1 (`manager_group` como autoridad operativa), `REGLAS_TUNEADAS/agent-conf/kriptome-baseline_agent.conf`, `REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example`, `REGLAS_TUNEADAS/wazuh/config/ossec.conf.ruleset.snippet.xml` (Fase 14: por qué `rule_exclude` no sirve para personalización por tenant).

## 1. Por qué hace falta este documento

Wazuh resuelve la configuración efectiva de un agente combinando **todos** los grupos a los que pertenece, aplicados en el orden en que están asignados (`agent_groups`), donde el **último grupo gana** en caso de que dos grupos definan la MISMA opción/clave. Si Kriptome no fija una convención de nombres y un orden obligatorio, dos operadores pueden asignar los grupos en orden distinto para dos agentes del mismo tenant y terminar con comportamiento distinto sin que nadie lo note — esto ya causó el error real corregido en Fase 14 (`rule_exclude` tratado como si fuera "por tenant" cuando en realidad es global al Manager).

## 2. Taxonomía de grupos (obligatoria)

| Prefijo/nombre | Alcance | Contenido permitido | Ejemplo |
|---|---|---|---|
| `kriptome-baseline` | TODOS los agentes del Manager, sin excepción | Ruido universal (ignore de heartbeat, extensiones temporales), FIM/Sysmon base, opciones que deben ser iguales para cualquier tenant | `REGLAS_TUNEADAS/agent-conf/kriptome-baseline_agent.conf` |
| `TENANT-<client_code>` | Todos los agentes de UN tenant | `label client_code`, overrides de FIM/logs específicos del parque de ESE cliente (rutas de una app de negocio suya) | `TENANT-CLI-001` (ver `CLI-001_agent.conf.example`) |
| `ROLE-<asset_role_code>` | Agentes que cumplen un rol técnico concreto, sin importar el tenant | Directorios/monitoreo específicos de ese rol (p. ej. rutas de logs de un motor de base de datos) | `ROLE-DB`, `ROLE-WEB` |

`asset_role_code` usa el mismo vocabulario que la label `agent.labels.asset_role_code` (ver `specifications/wazuh_alert_field_paths.md`) — no son dos taxonomías distintas, el grupo `ROLE-<x>` y la label `asset_role_code=<x>` deben coincidir para el mismo agente (una discrepancia es señal de configuración desalineada, aunque hoy no hay un chequeo automático de esto — ver §5, pendiente).

**Grupo `default`**: nunca debe tener agentes productivos asignados (regla de seguridad #2 de `specifications/tenant_resolution.md` §4) — un agente en `default` es por definición `resolution_status=group_mismatch`.

## 3. Orden de asignación obligatorio (precedencia)

Un agente productivo debe estar asignado, en este orden exacto:

```
1. kriptome-baseline
2. ROLE-<asset_role_code>      (0 o 1 — un agente tiene un único rol primario)
3. TENANT-<client_code>        (siempre el ÚLTIMO)
```

Ejemplo real (agente de base de datos del cliente CLI-001):

```
agent_groups: kriptome-baseline,ROLE-DB,TENANT-CLI-001
```

**Regla de precedencia**: `TENANT-<client_code>` va SIEMPRE último porque, si dos grupos definen la misma clave (p. ej. un `<ignore>` de FIM), la configuración del TENANT debe poder sobrescribir tanto el baseline como el rol técnico — el cliente puede tener una excepción legítima de negocio que ni el baseline ni el rol genérico conocen. Invertir este orden (tenant antes que rol) haría que un override de rol pisara silenciosamente una excepción de negocio del tenant, o viceversa, dependiendo de qué operador asignó los grupos primero — el mismo tipo de inconsistencia no determinista que Fase 14 corrigió para `rule_exclude`.

## 4. Qué NUNCA va en cada nivel (relación con Fase 14)

- **`kriptome-baseline`**: nunca una decisión que solo aplique a un tenant o rol específico. Nunca PII (nombres de cliente, alias de negocio — ver `specifications/wazuh_alert_field_paths.md`).
- **`ROLE-<x>`**: nunca un `client_code` o cualquier dato de identidad de tenant — un rol es transversal a tenants por diseño.
- **`TENANT-<client_code>`**: nunca una exclusión que dependa de la ausencia de una tecnología en TODO el parque del Manager (eso es `rule_exclude` en `ossec.conf`, que es global al Manager, no al grupo — ver `REGLAS_TUNEADAS/wazuh/config/ossec.conf.ruleset.snippet.xml`, comentario "CORRECCION v1.3.1 Fase 14"). Los grupos Wazuh controlan qué se **recolecta** por agente; no controlan qué **reglas/decoders** carga el Manager — eso es `ossec.conf`, un único archivo compartido por todos los tenants del Manager.

## 5. Validación de claves duplicadas entre grupos — estado

`policy_validation_status: PENDIENTE (no implementado)`. Hoy no existe una herramienta que, dado el conjunto de archivos `agent-conf/*.conf`, detecte automáticamente:

- Dos grupos que definan la misma clave de configuración con valores distintos sin que el orden de precedencia (§3) esté documentado explícitamente para ese agente.
- Un grupo `TENANT-<x>` que declare una label `asset_role_code` o cualquier dato que debería vivir en `ROLE-<x>` (mezcla de responsabilidades entre niveles).
- Un `ROLE-<x>` que declare `client_code` (mezcla inversa).

Esto queda como requisito de diseño para una futura extensión de `scripts/validate_repository.py` (ver Fase 27) — no se inventa una herramienta que no existe; se documenta el hueco.

## 6. Relación con `manager_group` en `TenantResolutionResult`

`specifications/tenant_resolution.schema.json` usa el campo `manager_group` como "el `wazuh_group` real del agente en el Manager". Con la taxonomía de este documento, `manager_group` en la práctica es la **lista completa** de grupos asignados (no un único valor), pero para efectos de la resolución de tenant el campo relevante es específicamente el grupo `TENANT-<client_code>` presente en esa lista — es el que debe coincidir con `agent.labels.client_code` (check 3 de `tenant_resolution.md` §3). Si un agente no tiene ningún grupo `TENANT-*` asignado, o tiene más de uno, el resultado es `resolution_status=group_mismatch` (ambigüedad de tenant, nunca se asume el primero o el último de la lista).

## 7. Estado de este documento

`policy_validation_status: DISEÑADO`. No implica grupos reales creados en un Manager, ni una herramienta de validación de duplicados funcionando (ver §5). Es el contrato que cualquier despliegue real de Kriptome MiniSOC debe seguir para mantener la separación baseline/rol/tenant descrita en `docs/architecture/ARCHITECTURE_CANONICAL.md`.
