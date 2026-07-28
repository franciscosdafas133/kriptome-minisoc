# Paths reales de campos en una alerta Wazuh

**Estado: VALIDADO-XML** (verificado contra el código fuente de Wazuh v4.14.6, no inferido). Existe porque el repositorio necesitaba una referencia única y verificada de dónde vive cada campo dentro del JSON de una alerta — para evitar que contratos, ejemplos, consultas o dashboards asuman un path incorrecto.

## Advertencia principal

> **Las labels de Wazuh viven bajo `agent.labels.*`, no bajo `data.labels.*`.**

Verificado en el código fuente real: `src/analysisd/format/json_extended.c` línea 702 (tag `v4.14.6`):

```c
cJSON_AddItemToObject(agent, "labels", labels);
```

Las labels se agregan explícitamente al objeto `agent` del JSON de salida, nunca al objeto `data`. `data.*` está reservado para los campos que produce el **decoder** específico de cada fuente (SSH, Windows eventchannel, FIM, etc. — ver `REGLAS_TUNEADAS/GUIA_CAMPOS_ENRIQUECIMIENTO.docx`), no para metadatos del agente.

## Estructura de una alerta (paths verificados)

```
{
  "agent": {
    "id": "...",              -- identificador técnico del agente
    "name": "...",             -- nombre del host que reporta
    "ip": "...",               -- IP del agente
    "labels": {                -- ver src/analysisd/format/json_extended.c:702
      "client_code": "...",
      "asset_code": "...",
      "criticality_code": "...",
      "environment_code": "...",
      "site_code": "...",
      "asset_role_code": "..."
    }
  },
  "rule": {
    "id": "...",
    "level": ...,
    "description": "...",
    "groups": [...],
    "mitre": { "id": [...] }
  },
  "decoder": {
    "name": "..."
  },
  "data": {
    "srcip": "...",
    "dstuser": "...",
    "win": { "eventdata": {...}, "system": {...} },
    "syscheck": {...},
    "vulnerability": {...}
    // campos específicos del decoder -- ver diccionario_campos_enriquecimiento.csv
  },
  "full_log": "...",           -- el log crudo completo, sin parsear
  "timestamp": "...",          -- o "@timestamp" según la versión del Indexer
  "location": "..."
}
```

## Tabla de referencia rápida

| Path | Qué contiene | Ejemplos en este repo |
|---|---|---|
| `agent.id` | Identificador técnico del agente, siempre presente, lo pone Wazuh. | `specifications/tenant_asset_assignment.schema.json` (campo `agent_id`) |
| `agent.name` | Nombre de host reportado por el agente (dato técnico, nunca el nombre de negocio del activo). | Va a `technical_appendix`, nunca al cuerpo del correo (`specifications/client_notification.schema.json`) |
| `agent.ip` | IP del agente (no confundir con `data.srcip`, que es la IP del origen del evento detectado). | — |
| `agent.labels.*` | Labels configuradas por Kriptome vía `agent.conf` — SOLO códigos operativos (`client_code`, `asset_code`, `criticality_code`, `environment_code`, `site_code`, `asset_role_code`). **Nunca PII ni datos de negocio mutables** (ver §Prohibición de PII más abajo). | `REGLAS_TUNEADAS/agent-conf/*.conf*` |
| `rule.*` | Metadatos de la regla que disparó (id, level, description, groups, mitre). | `specifications/normalized_event.schema.json` (`rule_id`, `rule_level`, `rule_groups`, `mitre_ids`) |
| `decoder.*` | Qué decoder de Wazuh procesó el log. | — |
| `data.*` | Campos específicos extraídos por el decoder (varían por familia: SSH da `data.srcip`/`data.dstuser`; Windows da `data.win.eventdata.*`; FIM da `data.syscheck.*`; vulnerabilidades dan `data.vulnerability.*`). | `REGLAS_TUNEADAS/GUIA_CAMPOS_ENRIQUECIMIENTO.docx`, `REGLAS_TUNEADAS/routing/diccionario_campos_enriquecimiento.csv` |
| `full_log` | El log crudo sin parsear. Nunca se envía completo a un LLM ni al cliente (ver `docs/architecture/ARCHITECTURE_CANONICAL.md` principio "la IA nunca es fuente de verdad", y la limitación de sudo/PAM documentada en `GUIA_CAMPOS_ENRIQUECIMIENTO.docx` que requiere leerlo para el comando ejecutado). | — |
| `timestamp` / `@timestamp` | Momento del evento. El nombre exacto del campo depende de la versión/configuración del Indexer (`@timestamp` es la convención de OpenSearch/Elasticsearch cuando el documento se indexa con ese mapeo). | `specifications/normalized_event.schema.json` (campo `timestamp`) |

## Prohibición de PII en `agent.labels.*`

Las labels quedan **indexadas en el Indexer** junto con cada alerta — son difíciles de corregir o purgar retroactivamente si cambian (p. ej. una razón social se actualiza, un contacto deja la empresa). Por eso:

**Prohibido en `agent.labels.*`:**
- `client_contact_email`, `contact_email`, `owner_email`, `support_email` (cualquier variante de correo de contacto)
- `client_name`, `business_name` (nombre comercial — dato mutable de negocio)
- `contact_name`, `owner_area`, `business_function` (cualquier dato de negocio mutable o potencialmente identificable)

**Permitido en `agent.labels.*` — solo códigos operativos estables:**
- `client_code`, `asset_code`, `site_code`, `criticality_code`, `environment_code`, `asset_role_code`

Los datos completos (contactos, nombre comercial, SLA, reglas de comunicación, función de negocio) se resuelven **siempre** desde la CMDB (`specifications/tenant.schema.json`, `specifications/asset_context.schema.json`) usando el código operativo como clave de búsqueda — nunca se leen directamente de una alerta de Wazuh. Ver `REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example` y `REGLAS_TUNEADAS/agent-conf/kriptome-baseline_agent.conf` para la aplicación concreta de esta regla (v1.3.1: se retiraron `client_name` y `asset_alias` de las labels de ejemplo).

## Prueba de que este documento se respeta (ver CI)

`.github/workflows/validate-contracts.yml` y `scripts/validate_repository.py` deben fallar si encuentran:
- `data.labels.client_id` o `data.labels.*` en cualquier contrato/ejemplo/consulta vigente (patrón prohibido).
- Cualquiera de los términos de PII de la lista de arriba dentro de `agent.labels` en un archivo vigente (no histórico).

Ver Fase 27 de la corrección de consistencia v1.3.1 para el detalle de esas dos verificaciones automatizadas.
