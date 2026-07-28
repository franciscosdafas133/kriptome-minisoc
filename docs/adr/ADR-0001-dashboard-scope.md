# ADR-0001 — Alcance del Wazuh Dashboard

- **Estado**: Aceptado
- **Fecha**: 2026-07-26
- **Versión de arquitectura**: v1.3.1

## Contexto

Wazuh incluye un Dashboard web (basado en OpenSearch Dashboards) con visualizaciones, alertas y capacidad de exploración de eventos. Existe el riesgo de que, por estar ya disponible "gratis" con el propio Wazuh, se termine tratando implícitamente como la interfaz que ve el cliente final de Kriptome MiniSOC — sin que nadie haya tomado esa decisión explícitamente. Eso entraría en conflicto directo con el modelo de negocio ya definido (`docs/architecture/ARCHITECTURE_CANONICAL.md`, `specifications/client_notification.schema.json`): el cliente de Kriptome no opera un SIEM, recibe casos gestionados y comunicación por correo — "Wazuh detecta, Kriptome administra casos y decisiones de negocio".

Además, el Dashboard, tal como lo expone Wazuh de fábrica, no tiene aislamiento multi-tenant nativo compatible con el modelo de Kriptome (`docs/architecture/POSTGRES_TENANT_ISOLATION.md`, `docs/architecture/INDEXER_ACCESS_MODEL.md`): dar acceso directo a un cliente sin una capa de filtrado por tenant propia sería un riesgo de fuga de datos entre tenants.

## Decisión

**El Wazuh Dashboard es una herramienta INTERNA del SOC de Kriptome, nunca la interfaz MVP orientada al cliente.**

1. El Dashboard se usa exclusivamente por operadores/analistas de Kriptome, autenticados con sus propias credenciales internas, para investigación y triage — nunca se expone una URL o credencial del Dashboard directamente a un cliente final.
2. La interfaz del cliente (cuando exista) es la comunicación por correo (`specifications/client_notification.schema.json`) y, en el futuro, cualquier portal propio de Kriptome construido específicamente con aislamiento multi-tenant desde el diseño — nunca una reexposición del Dashboard de Wazuh.
3. Cualquier usuario de demostración, laboratorio o prueba de concepto creado en el Dashboard debe marcarse explícitamente `DEMO / VALIDATION ONLY` (en el nombre de usuario, en un registro de usuarios activos, o ambos) para que nunca se confunda con una cuenta operativa real ni se use accidentalmente contra datos de un tenant real.
4. El acceso de operadores internos al Dashboard sigue siendo, aun así, sujeto a las mismas reglas de resolución/aislamiento de tenant que cualquier otra consulta (`specifications/tenant_resolution.md` §5: el `tenant_id` de sesión de un operador es para *autorización*, no *resolución* — un operador solo debería poder explorar datos de los tenants para los que está autorizado, aunque el mecanismo técnico exacto para restringir esto dentro del propio Dashboard de Wazuh queda como trabajo de implementación no resuelto por este ADR).

## Consecuencias

**Positivas:**
- Evita que una decisión de conveniencia técnica ("ya está ahí, démosle acceso al cliente") erosione silenciosamente el modelo de negocio de casos gestionados.
- Deja claro, para cualquier futura discusión de producto, que un portal cliente-facing es un desarrollo propio pendiente, no una reutilización del Dashboard de Wazuh.
- Evita el riesgo de fuga cross-tenant que implicaría exponer el Dashboard sin una capa de aislamiento propia.

**Negativas / trade-offs aceptados:**
- No hay hoy una interfaz visual self-service para que el cliente explore su propio historial de casos — la única interacción es por correo, hasta que se decida construir (y presupuestar) un portal propio.
- El acceso de operadores al Dashboard requiere disciplina operativa (marcar cuentas demo, restringir accesos) mientras no exista un control técnico automático de aislamiento por tenant dentro del propio Dashboard.

## Alternativas consideradas

- **Exponer el Dashboard directamente al cliente con un usuario de solo lectura filtrado por índice/tenant**: descartada para el MVP — requeriría replicar buena parte del aislamiento de `docs/architecture/INDEXER_ACCESS_MODEL.md` dentro de una herramienta de terceros no diseñada para multi-tenancy estricto, y seguiría exponiendo terminología/estructura de Wazuh (rule_id, decoders) a un cliente no técnico, contradiciendo el lenguaje simple ya exigido en `specifications/client_notification.schema.json`.
- **No usar el Dashboard en absoluto, ni siquiera internamente**: descartada — el Dashboard sigue siendo la herramienta de investigación más eficiente disponible para los operadores de Kriptome sobre datos ya indexados; el problema no es la herramienta, es a quién se le da acceso.

## Referencias

- `docs/architecture/ARCHITECTURE_CANONICAL.md`
- `docs/architecture/INDEXER_ACCESS_MODEL.md`
- `docs/architecture/POSTGRES_TENANT_ISOLATION.md`
- `specifications/client_notification.schema.json`
- `specifications/tenant_resolution.md` §5
