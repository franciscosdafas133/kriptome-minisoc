# Resolución de tenant (multi-tenant, seguridad)

Contrato de cómo se resuelve `tenant_id` a partir de un evento crudo de Wazuh, y las reglas de seguridad que ningún componente debe romper. Basado en `DOCUMENTOS/01_ARQUITECTURA_Y_DISENO.docx` (arquitectura #6) y en la nota "AISLAMIENTO MULTI-TENANT EN CORRELACIONES" de `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml` (estado: PENDIENTE). No implica un backend implementado — es el contrato que ese backend debe cumplir cuando se construya.

## 1. Cadena de resolución: `agent_id → tenant_id → asset_id`

```
evento crudo de Wazuh
  -> agent.id            (siempre presente, lo pone Wazuh; VALIDADO-XML)
  -> agent.labels.client_id    (label del grupo Wazuh del cliente, ver
                                REGLAS_TUNEADAS/agent-conf/CLI-001_agent.conf.example)
  -> tenant_id = client_id     (resuelto en BACKEND, nunca en el evento crudo directamente)
  -> agent.labels.asset_id     (label por-agente, ver kriptome-baseline_agent.conf)
  -> asset_id
```

**Regla de seguridad #1: `tenant_id` se resuelve SIEMPRE del lado del backend a partir de los labels del agente que originó el evento — nunca se acepta un `tenant_id` que venga ya puesto en el payload de un frontend, una API pública, o un campo editable por el cliente.** Esto es consistente con doc 01 §5: "ninguna consulta al Indexer corre sin client_id... el client_id se resuelve en backend; el label es la fuente de ese client_id."

## 2. Estado de verificación de `agent.labels.client_id` en tiempo de regla

**PENDIENTE** (no `VALIDADO-XML`). El propio `kriptome_local_rules.xml` documenta esto como riesgo conocido sin resolver: las correlaciones nativas y custom que usan `same_source_ip` / `same_field` acumulan por valor de IP a nivel de TODO el Manager, sin segmentar por `agent.labels.client_id`, porque no está confirmado con `wazuh-logtest` que ese campo sea accesible en tiempo de evaluación de regla en la versión desplegada. Mientras esto sea `PENDIENTE`:

- El **conteo** de una correlación (p. ej. "8 fallos en 120s") puede mezclar eventos de dos tenants distintos si comparten la misma IP atacante dentro de la ventana.
- La **atribución del caso** (a qué cliente pertenece) nunca se mezcla, porque eso se re-resuelve en el backend/App por `client_id` real al construir el caso — el riesgo es solo en el contador de la correlación de Wazuh, no en el caso final.

## 3. Comparación con labels (verificación de consistencia)

Antes de aceptar un evento como válido para abrir/actualizar un caso, el backend debe comparar:

1. `agent.labels.client_id` (el tenant declarado por el agente) contra el registro de qué grupo Wazuh pertenece ese `agent.id` en el Manager (fuente de verdad operativa, no el label auto-reportado únicamente).
2. `agent.labels.asset_id` presente y no vacío.

Si ambos coinciden y están presentes: el evento sigue el flujo normal.

## 4. Cuarentena por inconsistencia

Si la comparación del §3 falla — el agente no tiene labels, el `client_id` del label no corresponde al grupo Wazuh real, o el evento llega sin `agent.id` reconocible — el evento **NO se descarta silenciosamente ni se asigna a un tenant por defecto**. Va a una cola de cuarentena equivalente al `dead_letter` descrito en `DOCUMENTOS/03_FLUJOS_OPERATIVOS.docx` §1 (flujo end-to-end: `client_id inválido -> Dead letter + alerta interna`), con las mismas reglas:

- Se registra el evento completo para investigación manual.
- Se genera una alerta interna al operador (no al cliente).
- Existe un umbral de atención: más de N eventos en cuarentena en 15 minutos dispara revisión inmediata (doc 03 §8, "dead_letter tiene además alerta automática por umbral").

**Regla de seguridad #2: ningún agente productivo puede quedar en el grupo `default` de Wazuh** (doc 03 §5.2: "ningún agente productivo queda en grupo 'default'; toda alerta debe traer client_id + asset_id"). Un agente en `default` es, por definición, un caso de cuarentena.

## 5. Prohibición explícita: `tenant_id` del frontend nunca es autoridad

Ningún componente (Kriptome App, API futura, dashboard de operador) puede:

- Aceptar un `tenant_id` enviado por un cliente HTTP como valor de verdad para filtrar datos.
- Usar un `tenant_id` de sesión de usuario como sustituto de la resolución `agent_id -> labels -> tenant_id` para consultas al Indexer.

El `tenant_id` de sesión (con qué cliente está autenticado un operador o un usuario) solo se usa para **autorización** (qué tenant puede ver ese usuario), nunca para **resolución** (a qué tenant pertenece un evento). Son dos preguntas distintas y no deben compartir el mismo campo de confianza.

## 6. Filtros obligatorios por tenant

Toda consulta al Indexer, sin excepción, debe llevar un filtro por `tenant_id` resuelto según §1-§3. Esto incluye:

- Consultas de la Kriptome App para construir casos.
- Consultas del operador humano (nunca debe poder ver datos de un tenant fuera del que se le asignó).
- Cualquier endpoint de reporting/dashboard futuro.

**No existe un modo "todos los tenants" fuera de tareas de mantenimiento explícitas del Manager (backups, salud del Indexer), que no exponen datos de eventos por cliente.**

## 7. Estado de este documento

`policy_validation_status: DISEÑADO`. Es un contrato de arquitectura extraído de decisiones ya tomadas en `DOCUMENTOS/01` y `03`, más el riesgo conocido de `kriptome_local_rules.xml`. No hay backend implementado que lo cumpla todavía — ver `README.md` §9 sobre alcance.
