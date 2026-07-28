# Plan de implementación multi-tenant — dos tenants piloto

**Estado: `DISEÑADO`.** Este documento describe cómo se implementaría el aislamiento multi-tenant para dos tenants concretos, usando los contratos ya definidos en `specifications/`. **No se ha ejecutado nada de lo aquí descrito** — no hay Manager Wazuh desplegado, no hay Indexer configurado, no hay Dashboard con usuarios reales. Es un plan, no un reporte de trabajo hecho.

## Los dos tenants

| # | Tenant | `tenant_type` | `environment_type` / `site_type` típico |
|---|---|---|---|
| 1 | Casa del CEO | `home` | `personal` / `home` |
| 2 | Empresa piloto (por identificar) | `small_business` o `medium_business` (a confirmar según el tamaño real) | `production` / `office` |

Estos dos tenants son deliberadamente distintos en perfil de riesgo y en expectativas de servicio — sirven para probar que el modelo de `specifications/tenant.schema.json` y `specifications/asset_context.schema.json` (con `environment_type`/`site_type` separados en v1.3.1) efectivamente distingue entre ambos casos sin forzar el modelo residencial dentro del molde empresarial.

---

## Capa de negocio

Qué se registra antes de tocar Wazuh:

- **Tenant**: alta en el registro de tenants (`specifications/tenant.schema.json`) con `status: draft` → `onboarding` una vez iniciado el proceso técnico.
- **Contactos**: `primary_contact` obligatorio para ambos tenants. `secondary_contact` fuertemente recomendado (necesario para el canal alterno de correo comprometido, ver `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` §B.10) — para "Casa del CEO" el contacto secundario podría ser un familiar o asistente con acceso a otro medio de contacto.
- **Activos**: inventario inicial en `specifications/asset_context.schema.json` — para Casa del CEO, probablemente 1-3 activos (laptop personal, router doméstico si se monitorea, quizás un NAS); para la empresa piloto, el inventario real de equipos a definir en el onboarding.
- **Servicio**: `service_plan` y `allowed_asset_count` a definir comercialmente (fuera del alcance técnico de este repo).
- **Responsables**: `owner_name`/`owner_contact` por activo (ver `asset_context.schema.json`).
- **Alcance**: qué familias de detección aplican a cada tenant — un tenant `home` probablemente no necesita FIM en rutas de servidor ni SCA de hardening empresarial; la matriz de routing (`REGLAS_TUNEADAS/routing/routing_matrix.csv`) se filtra por relevancia, no se aplica ciegamente igual a los dos tenants.

**Estado de esta capa: `DISEÑADO`.** No existe hoy un registro de tenants funcionando — los schemas son el contrato para cuando exista.

---

## Capa Wazuh

- **Grupos**: un grupo Wazuh por tenant (p. ej. `HOME-CEO` y `CLI-PILOTO-001`), siguiendo el patrón ya usado en `REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example`.
- **Agentes**: instalación del agente Wazuh en cada activo. Para Casa del CEO, esto puede significar un agente en un solo equipo personal — el mismo mecanismo técnico, un perfil de uso distinto.
- **Labels**: `client_id` (= `tenant_id`), `asset_id`, `criticality`, `environment_type`, `site_type` en el `agent.conf` de cada grupo/agente (ver `REGLAS_TUNEADAS/agent-conf/kriptome-baseline_agent.conf` para la separación entre labels de grupo y labels por-agente).
- **Configuraciones**: `agent.conf` por grupo. Para Casa del CEO, probablemente una configuración FIM más ligera (menos rutas críticas que monitorear que en un servidor empresarial).
- **Reglas**: el mismo `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml` para ambos tenants (las reglas custom no son por-tenant, operan sobre cualquier evento con los labels correctos).
- **Correlaciones**: aquí vive el riesgo ya documentado en `specifications/tenant_resolution.md` — las correlaciones nativas de Wazuh (`same_source_ip`, etc.) cuentan a nivel de todo el Manager, sin segmentar por tenant. Con solo 2 tenants el riesgo de colisión de conteo es bajo pero no nulo (si la misma IP atacante golpea a ambos en la misma ventana). Este plan NO resuelve ese riesgo — lo hereda como `PENDIENTE`.

**Estado de esta capa: `DISEÑADO`.** El paquete de reglas está `CONFIGURADO` (listo para copiar a un Manager), pero no hay Manager real desplegado con estos dos grupos.

---

## Capa Indexer

- **Documentos**: cada evento indexado debe llevar `tenant_id` resuelto (no aceptado del evento crudo, ver `tenant_resolution.md` §5) como campo filtrable.
- **Filtros**: toda consulta al Indexer para construir casos o servir al Dashboard debe llevar filtro obligatorio por `tenant_id` (ver `tenant_resolution.md` §6).
- **DLS (Document-Level Security)**: si el Indexer usado lo soporta (p. ej. OpenSearch/Elasticsearch con seguridad activada), configurar DLS por rol para que un usuario/rol asociado a un tenant solo pueda leer documentos de ese `tenant_id`, como defensa en profundidad además del filtro a nivel de aplicación.
- **Retención**: política de retención (ver `DOCUMENTOS/07_COMUNICACION_CON_EL_CLIENTE.docx` §B.7, "120 días: 30 en acceso inmediato + 90 en archivo") aplicada igual para ambos tenants, salvo que el contrato de alguno especifique algo distinto.

**Estado de esta capa: `DISEÑADO`.** No hay Indexer configurado en este repositorio.

---

## Capa Dashboard

- **Usuarios**: un usuario operador de Kriptome (no del cliente — recordar que el cliente no usa Dashboard, opera por correo, ver `DOCUMENTOS/01_ARQUITECTURA_Y_DISENO.docx`).
- **Roles**: rol de operador con acceso de solo lectura a los tenants que se le asignen (para el piloto, probablemente ambos).
- **Espacios**: si el Dashboard soporta "spaces"/tenants lógicos, uno por cada tenant, para que las búsquedas por defecto no crucen tenants por accidente.
- **Dashboards**: paneles operativos (casos abiertos, SLA, salud de agentes) parametrizados por tenant, no un panel global mezclado.
- **Consultas cruzadas**: **prohibidas** salvo tareas de mantenimiento del Manager que no exponen datos de eventos por cliente (ver `tenant_resolution.md` §6). El piloto de 2 tenants es precisamente donde este límite se prueba primero: si el operador puede, sin querer, ver datos de "Casa del CEO" al consultar la empresa piloto (o viceversa), el diseño de aislamiento falló.

**Estado de esta capa: `DISEÑADO`.** No hay Dashboard configurado en este repositorio.

---

## Capa de validación

Antes de considerar el piloto listo para operar con datos reales, se debe validar explícitamente (no asumir):

| Validación | Qué se prueba |
|---|---|
| Ingesta | Los eventos de ambos tenants llegan al Indexer con `tenant_id` correctamente resuelto (no null, no cruzado). |
| Atribución | Un evento del agente de Casa del CEO nunca se atribuye al `tenant_id` de la empresa piloto, y viceversa — incluso si por error de configuración ambos agentes comparten alguna IP de red (p. ej. detrás del mismo NAT si el CEO trabaja remoto desde la oficina). |
| Procesamiento | Las correlaciones de Wazuh (ver riesgo de conteo cross-tenant arriba) se observan en la práctica: ¿hay evidencia real de mezcla de conteo entre los dos tenants durante el piloto? |
| Generación de alertas | Cada caso generado para un tenant usa solo evidencia de ese tenant (nunca mezclada). |
| Visualización | El Dashboard, si se usa en el piloto, respeta el aislamiento por rol/espacio. |
| Acceso cruzado | Ningún operador con acceso a un solo tenant puede consultar el otro por error de UI o de API. |
| Correlación cruzada | Ninguna funcionalidad de "campaña" (ver `policies/case_types/AUTH_BRUTEFORCE_SUCCESS.yaml` → `campaign_correlation`) mezcla datos de ambos tenants — regla dura `never_correlates_across: tenant_id` ya declarada en esa política, a probarse aquí con datos reales de 2 tenants distintos.

**Ninguna de estas validaciones tiene evidencia registrada hoy.** Cuando se ejecuten, sus resultados deben documentarse con fecha, entorno y datos observados — no se promueve ningún elemento a `VALIDADO-SHADOW` o `VALIDADO-PILOTO` sin ese registro (ver `specifications/validation_statuses.md`).

---

## Qué NO afirma este documento

- Que el piloto ya está en marcha.
- Que existe un Manager, Indexer o Dashboard configurado para estos tenants.
- Que la empresa piloto ya fue identificada y contratada (el título del plan dice explícitamente "por identificar").
- Que el riesgo de correlación cross-tenant en Wazuh (`tenant_resolution.md`) esté resuelto — se hereda como pendiente conocido, no se resuelve aquí.

Este documento es el mapa de qué hacer, en qué orden y con qué criterio de éxito — no el registro de que ya se hizo.
