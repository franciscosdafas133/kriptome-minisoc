# Modelo de acceso al Indexer

**Estado: DISEÑADO.** Resuelve una contradicción latente en versiones previas de la documentación: "toda consulta al Indexer lleva tenant" no puede ser literalmente cierto, porque *algo* tiene que leer los eventos recién llegados para poder resolverles un tenant en primer lugar. Este documento separa dos clientes lógicos con permisos y propósitos distintos.

## El problema

Un evento de Wazuh recién indexado no trae un `tenant_id` de confianza hasta que pasa por el Tenant Resolver (`specifications/tenant_resolution.schema.json`). Si la regla fuera "ninguna consulta sin tenant", no habría manera de que el sistema encontrara esos eventos nuevos para empezar a clasificarlos. La solución no es debilitar la regla de aislamiento — es reconocer que hay dos tipos de cliente con responsabilidades distintas.

## A. `GlobalInternalIngestorClient`

**Propósito:** leer eventos nuevos del Indexer para clasificarlos, nunca para servirlos a un usuario o a un reporte.

Características:
- Es un **servicio interno**, sin endpoint público expuesto.
- Lee **todos** los eventos nuevos, sin filtro de tenant (porque su trabajo es precisamente descubrir a qué tenant pertenecen).
- Ejecuta la cadena de resolución de `specifications/tenant_resolution.md` sobre cada evento leído.
- Cuando la resolución falla (`resolution_status != resolved`), envía el evento a cuarentena — nunca lo descarta en silencio ni lo asigna a un tenant por defecto.
- Solo tiene los **permisos mínimos de lectura** necesarios sobre el índice de eventos crudos — no tiene permisos de escritura sobre datos de casos, ni acceso a otros índices (contactos, procedimientos, etc.).
- No decide prioridad, no abre casos, no genera comunicación — solo produce `NormalizedEvent` + `TenantResolutionResult` como salida hacia el siguiente componente (`Deterministic Router`, ver `docs/architecture/ARCHITECTURE_CANONICAL.md`).

## B. `TenantScopedIndexerClient`

**Propósito:** todas las consultas funcionales posteriores a la resolución de tenant.

Características:
- Exige `tenant_id` como parámetro obligatorio de construcción/uso — no existe una forma de instanciar este cliente sin un tenant.
- Los filtros de consulta los construye el **backend**, nunca se aceptan como DSL libre desde un frontend o una API pública.
- No permite "elegir tenant" desde el frontend: el `tenant_id` usado en cada consulta proviene de la sesión autorizada del operador (para *autorización*, no *resolución* — ver distinción en `tenant_resolution.md` §5) o del caso/evento ya resuelto que se está procesando.
- Cualquier código que necesite leer casos, activos, notificaciones o auditoría usa este cliente, nunca el `GlobalInternalIngestorClient`.

### Ejemplo de guardia obligatoria (no usar `assert`)

```python
class TenantScopedIndexerClient:
    def __init__(self, tenant_id: str):
        if not tenant_id:
            raise TenantRequiredError("tenant_id is required")
        self.tenant_id = tenant_id

    def query(self, query_body: dict):
        # el filtro de tenant se inyecta aquí, SIEMPRE, sin que el
        # llamador pueda anularlo pasando su propio filtro de tenant
        scoped_query = self._apply_tenant_filter(query_body, self.tenant_id)
        return self._execute(scoped_query)
```

`assert tenant_id` está prohibido como control de seguridad en este punto (ver `specifications/tenant_resolution.md` §1, Regla de seguridad #1-bis): en Python, `assert` se elimina completamente si el intérprete corre con `-O` (optimizaciones activadas), lo que desactivaría el control sin ningún error visible. Una excepción explícita (`raise TenantRequiredError(...)`) siempre se ejecuta.

## Resumen de la regla

> El ingestor global puede leer eventos sin tenant porque su función es clasificarlos.
> Las consultas funcionales posteriores siempre son tenant-scoped.

## Qué NO cambia

- El principio "ningún dato de un tenant puede mezclarse con otro" (`docs/architecture/ARCHITECTURE_CANONICAL.md`) sigue vigente sin excepción para **cualquier dato ya clasificado**. La única ventana donde un evento existe "sin tenant confirmado" es entre su llegada al Indexer y el momento en que el `GlobalInternalIngestorClient` completa su resolución — y en esa ventana, el evento no es visible para ningún operador, caso, o comunicación; solo para el propio proceso de clasificación.
- Los 6 checks de `specifications/tenant_resolution.md` §3 siguen siendo obligatorios antes de que un evento pase de "leído por el ingestor global" a "parte de un caso tenant-scoped".

## Relación con otros documentos

- `specifications/tenant_resolution.md` — la cadena de resolución que ejecuta el `GlobalInternalIngestorClient`.
- `docs/architecture/INGESTION_DESIGN.md` — el diseño de polling/checkpoint que usa el ingestor global para saber qué es "nuevo".
- `docs/architecture/POSTGRES_TENANT_ISOLATION.md` — el equivalente de este modelo de acceso, pero para la base de datos relacional del motor de casos (RLS), no para el Indexer.
