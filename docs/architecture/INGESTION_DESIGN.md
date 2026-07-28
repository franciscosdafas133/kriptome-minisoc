# Diseño de ingesta (polling del Indexer por el Global Internal Ingestor)

`policy_validation_status: DISEÑADO`. Contrato de diseño para el mecanismo por el cual el `GlobalInternalIngestorClient` (`docs/architecture/INDEXER_ACCESS_MODEL.md`) descubre eventos nuevos en el Wazuh Indexer. NO implica un servicio de ingesta implementado ni probado — es el diseño que ese servicio debe seguir cuando se construya (fuera de alcance de este repo, ver `README.md`).

## 1. Por qué polling (no push)

El Indexer (OpenSearch) no empuja eventos activamente a consumidores externos. El Global Internal Ingestor debe consultar (`_search`) periódicamente el índice de alertas nuevas. Esto introduce los problemas clásicos de todo consumidor por polling contra un almacén append-only: cómo saber qué ya se leyó, cómo no perder eventos entre lecturas, y cómo no reprocesar de más.

## 2. Estrategia de paginación: `search_after` + `@timestamp` + `_id`

- Ordenar siempre por `(@timestamp, _id)` ascendente — nunca por `_id` solo (no es correlativo en el tiempo) ni por `@timestamp` solo (no es único; dos documentos pueden compartir el mismo milisegundo, ver `specifications/event_identity.schema.json` sobre por qué timestamp no es identidad).
- Usar `search_after` (no `from`/`size` con offset creciente): `from`/`size` se degrada en costo con índices grandes y es inestable si llegan documentos nuevos entre páginas; `search_after` es estable frente a inserciones concurrentes porque avanza por el valor del último documento leído, no por posición.
- El cursor persistido (`checkpoint`, ver §4) es el par `(last_timestamp, last_id)` de la última página confirmada como procesada.

## 3. Ventana de solape (overlap window)

Ningún reloj de origen es perfectamente monotónico ni la indexación es instantánea: un documento con `@timestamp = T` puede aparecer indexado varios segundos después de otro con `@timestamp = T + 5s` (indexación asíncrona, múltiples agentes, colas intermedias). Consultar estrictamente `@timestamp > last_timestamp` puede saltarse documentos que llegan tarde con un timestamp "antiguo".

- Cada ciclo de polling re-consulta desde `last_timestamp - overlap_window` (no desde `last_timestamp` exacto).
- `overlap_window` por defecto: `PT30S` (ajustable por volumen/latencia observada de indexación).
- Los documentos ya vistos dentro de esa ventana se descartan por `event_hash` ya conocido (idempotencia, ver §6), no por timestamp — el overlap existe para no perder eventos, la deduplicación existe para no procesarlos dos veces.

## 4. Checkpoint (persistencia del cursor)

- El checkpoint (`last_timestamp`, `last_id`, `resolver_version`) se persiste de forma transaccional junto con el resultado del lote procesado (no antes de procesar, no de forma separada sin garantía) — un checkpoint avanzado sin que el lote se haya escrito completo produciría pérdida silenciosa de eventos tras un reinicio.
- Un checkpoint corrupto o ausente (primer arranque, o recuperación tras incidente) hace que el ingestor re-consulte desde una ventana de seguridad configurada (p. ej. últimas 24h) en vez de fallar o asumir "desde ahora" — asumir "desde ahora" perdería silenciosamente cualquier evento pendiente.

## 5. Tamaño de lote, timeout y reintentos

| Parámetro | Valor por defecto | Nota |
|---|---|---|
| `batch_size` | 500 documentos | Ajustable según tamaño medio de documento y latencia de red al Indexer. |
| `query_timeout` | `PT10S` | Timeout de la consulta `_search` individual. |
| `max_retries` | 5 | Con backoff exponencial (ver abajo), no reintento inmediato en bucle. |
| `backoff_base` | `PT2S`, factor 2, tope `PT60S` | `2s, 4s, 8s, 16s, 32s, 60s, 60s...` — evita machacar un Indexer ya degradado. |

Un lote que falla tras agotar `max_retries` **no** descarta los eventos: se marca el ciclo como fallido, el checkpoint NO avanza, y se genera una alerta interna de operación (distinta de una alerta de cliente) — el siguiente ciclo reintenta desde el mismo checkpoint.

## 6. Replay e idempotencia

- Reprocesar un lote ya visto (tras un reinicio sin checkpoint actualizado, o dentro del overlap window) es seguro porque la deduplicación ocurre por `event_hash` (`specifications/event_identity.schema.json`), con `UNIQUE(event_hash)` en el almacén de eventos (`docs/architecture/CASE_ENGINE_CONCURRENCY.md`) — un replay produce un insert que falla por conflicto de unicidad y se descarta sin efectos secundarios (no vuelve a disparar el router ni el motor de casos).
- El diseño depende de que el cálculo de `event_hash` sea determinístico para el mismo documento de origen (estrategia principal: `source_cluster_id + source_index + source_document_id`, ver ese schema) — replays no producen hashes distintos para el mismo documento.

## 7. Eventos tardíos (late events) y clock skew

- Un evento cuyo `@timestamp` de origen es anterior al checkpoint actual pero que recién se indexa (agente con reloj desfasado, o cola de envío retrasada) se acepta igual siempre que entre dentro de `overlap_window`, y se procesa normalmente (no se descarta por "es viejo").
- Si el desfase excede `overlap_window` (evento "demasiado tarde"), se registra igualmente para trazabilidad, pero **no** reabre casos ya cerrados fuera de su ventana de reapertura ni recalcula fingerprints de casos históricos — sigue el flujo normal como un evento nuevo con su propio timestamp.
- El clock skew de agentes individuales (reloj del endpoint mal configurado) es un problema de higiene operativa del cliente, no del ingestor — el ingestor no intenta "corregir" timestamps de origen, solo tolera el desfase vía `overlap_window`.

## 8. Backpressure

- Si el motor de casos (consumidor aguas abajo) no puede absorber el ritmo de eventos normalizados (cola de escritura llena, base de datos saturada), el ingestor debe **reducir su cadencia de polling**, no acumular lotes en memoria sin límite ni descartar eventos para "ponerse al día".
- Señal de backpressure: profundidad de cola de escritura pendiente por encima de un umbral configurado → el ingestor introduce un retraso creciente entre ciclos de polling (mismo mecanismo de backoff exponencial de §5, aplicado aquí a la cadencia, no a reintentos de error).
- El checkpoint sigue avanzando normalmente durante backpressure (los eventos sí se leyeron y encolaron) — backpressure ralentiza la tasa de lectura, no crea un estado de error.

## 9. Dead-letter

- Un evento que pasa la lectura pero falla de forma no transitoria en una etapa posterior (normalización imposible, resolución de tenant fallida de forma permanente, esquema irreconocible) va a una cola dead-letter — nunca se descarta en silencio ni bloquea el avance del checkpoint general.
- Corresponde al mismo mecanismo de cuarentena ya descrito en `specifications/tenant_resolution.md` §4 para fallos de resolución de tenant; este documento generaliza esa cola a cualquier fallo no transitorio de la etapa de ingesta/normalización, no solo los de tenant.
- Umbral de atención: más de N eventos en dead-letter en una ventana de 15 minutos dispara revisión inmediata del operador (mismo umbral ya definido en `specifications/tenant_resolution.md` §4 para el caso específico de tenant).

## 10. Métricas mínimas requeridas

- `ingestion_lag_seconds`: diferencia entre `now()` y el `@timestamp` del último documento procesado — mide qué tan "al día" está el ingestor.
- `events_read_total`, `events_deduplicated_total`, `events_dead_lettered_total`, `events_quarantined_total` (tenant).
- `checkpoint_age_seconds`: tiempo desde el último avance de checkpoint — un valor creciente sin backpressure activa indica que el ingestor está detenido silenciosamente.
- `retry_count_total`, `backoff_current_seconds`.

## 11. Recuperación tras reinicio

1. Cargar el último checkpoint persistido.
2. Si no existe (primer arranque) o está corrupto: usar la ventana de seguridad configurada (§4) y registrar el evento de arranque en frío en auditoría.
3. Reanudar el polling desde `last_timestamp - overlap_window` (mismo mecanismo que un ciclo normal, no un camino especial) — un reinicio no es un caso distinto de un ciclo con overlap, es el mismo mecanismo aplicado tras una interrupción.
4. No se asume que el estado del motor de casos aguas abajo está sincronizado con el checkpoint del ingestor — la idempotencia de §6 es la que garantiza que un reprocesamiento post-reinicio no duplica efectos, no una coordinación explícita entre ambos componentes.

## 12. Qué NO resuelve este documento

- No define el mecanismo de transporte entre el Global Internal Ingestor y el motor de casos (cola de mensajes, HTTP interno, etc.) — eso es un detalle de implementación fuera de alcance de este contrato.
- No define límites de coste/tamaño de la infraestructura del Indexer — ver `docs/architecture/CAPACITY_AND_CONTINUITY.md` para dimensionamiento.

## 13. Estado de este documento

`policy_validation_status: DISEÑADO`. No hay servicio de ingesta implementado; no hay métricas reales recolectadas; los valores por defecto (`overlap_window`, `batch_size`, backoff) son puntos de partida razonables para el diseño, no resultados de una prueba de carga real.
