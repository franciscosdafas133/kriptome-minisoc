# Resiliencia de enriquecimiento externo

`policy_validation_status: DISEÑADO`. Contrato de cómo debe comportarse cualquier conector de enriquecimiento externo (GeoIP, reputación de IP/hash/dominio, CISA KEV — ver `specifications/enrichment_result.schema.json`) frente a fallas, límites de tasa y datos no disponibles. NO implica conectores reales implementados ni credenciales de proveedor — ver `README.md` §"Qué NO está implementado". Ya referenciado desde `enrichment_result.schema.json` (campo `kev_result.kev_status=source_error`) y `policies/risk/risk_policy_v1.yaml` (factor `known_exploitation`).

## 1. Principio: el enriquecimiento nunca bloquea el flujo del caso

`enrichment_result.schema.json` ya lo establece para `query_failed`: "el evento debe seguir su flujo SIN el enriquecimiento en vez de bloquearse... el enriquecimiento no es bloqueante para abrir un caso CRITICAL". Este documento detalla el mecanismo completo detrás de esa afirmación — no solo qué pasa cuando la consulta falla, sino cómo se evita llegar a fallar innecesariamente y cómo se comunica la incertidumbre resultante.

## 2. Timeout, retry, backoff

| Parámetro | Valor por defecto | Nota |
|---|---|---|
| `query_timeout` | `PT5S` | Timeout por intento individual — más corto que el de ingesta (`docs/architecture/INGESTION_DESIGN.md` usa `PT10S`) porque el enriquecimiento es un paso opcional en la ruta crítica de apertura de un caso, no debe demorar esa ruta más de lo estrictamente necesario. |
| `max_retries` | 2 (3 intentos totales) | Menos reintentos que la ingesta (`docs/architecture/INGESTION_DESIGN.md` usa 5) — un enriquecimiento que sigue fallando debe degradarse a `query_failed`/`source_error` rápido, no bloquear la apertura del caso mientras reintenta. |
| `backoff_base` | `PT1S`, factor 2, tope `PT8S` | `1s, 2s, 4s` — ventana corta, consistente con que el caso no debe esperar minutos por un enriquecimiento opcional. |

Un timeout o error transitorio (5xx, error de red) agota los reintentos y produce `query_failed=true` (o, específicamente para CISA KEV, `kev_status=source_error` — ver `enrichment_result.schema.json` `$defs.kev_result`) — nunca bloquea la escritura del `NormalizedEvent`/`case` ni retrasa `human_review_required=true` cuando corresponde por otros factores.

## 3. Circuit breaker

Cuando un proveedor específico acumula una tasa de fallos por encima de un umbral (p. ej. más del 50% de las últimas 20 consultas fallidas) dentro de una ventana corta, el circuito se abre: nuevas consultas a ESE proveedor se marcan `query_failed`/`source_error` inmediatamente, sin intentar la llamada de red, durante un período de enfriamiento (`open_duration`, p. ej. `PT2M`) — evita que un proveedor caído multiplique la latencia agregada del sistema con timeouts repetidos de cada evento que necesita ese enriquecimiento. Tras el enfriamiento, el circuito pasa a semi-abierto (permite una consulta de prueba); si tiene éxito, se cierra; si falla, reinicia el enfriamiento.

Este mecanismo es por proveedor (`source_provider`), no global — un circuito abierto para el proveedor de reputación de IP no afecta las consultas al feed CISA KEV, que es un proveedor distinto.

## 4. Rate limiting

- Cada conector respeta el límite de tasa documentado por su proveedor (p. ej. N consultas/minuto). El límite se aplica del lado de Kriptome de forma proactiva (no se espera a recibir un 429 para frenar), usando la caché (§5) para minimizar consultas repetidas del mismo IOC.
- Al alcanzar el límite, las consultas adicionales dentro de la ventana se encolan (si el caso puede esperar razonablemente) o se marcan `query_failed` con causa `rate_limited` (si el caso no puede esperar, p. ej. ruta `CRITICAL`) — nunca se descarta el evento completo por no poder enriquecerlo.

## 5. Caché por IOC — positiva y negativa

Ya establecido en `enrichment_result.schema.json` (`cache_ttl_seconds`, ligado a doc 03 nivel de control 6: "87 alertas del mismo IOC → 1 consulta API"). Este documento añade la distinción entre caché positiva y negativa:

- **Caché positiva**: el resultado de una consulta exitosa se reutiliza durante `cache_ttl_seconds`, evitando pagar/consultar de nuevo el mismo IOC repetidamente en una ventana corta (el mismo `source_ip` disparando múltiples eventos, el mismo `cve` repetido en varios activos).
- **Caché negativa**: un resultado `query_failed`/`source_error` TAMBIÉN se cachea, pero con un TTL mucho más corto que el positivo (p. ej. `PT60S` frente a horas/días de una caché positiva) — evita que una ráfaga de eventos durante una caída breve del proveedor multiplique intentos de red inútiles, sin arriesgar quedarse con un `source_error` cacheado por horas cuando el proveedor ya se recuperó.
- La caché negativa nunca se promueve silenciosamente a un resultado positivo por su ausencia — un IOC sin entrada de caché (ni positiva ni negativa vigente) siempre dispara una consulta nueva, nunca se asume "no encontrado" por defecto.

## 6. Stale fallback

Cuando una consulta falla pero existe un resultado positivo previo ya vencido (`cache_ttl_seconds` superado) para el mismo IOC, el sistema puede usar ese dato como *stale fallback* únicamente si se marca explícitamente como tal (campo de proveniencia, ver §7) — nunca se presenta un dato vencido como si fuera fresco. Esto aplica especialmente a CISA KEV: un `catalog_fetched_at` antiguo combinado con una consulta fallida nueva corresponde a `kev_status=stale_catalog` (dato incompleto conocido) en vez de `source_error` (sin dato alguno) — la distinción ya existe en el schema; este documento aclara que `stale_catalog` es precisamente el caso de "uso un stale fallback, y lo digo explícitamente", no un resultado fresco reetiquetado.

## 7. Proveniencia (provenance) obligatoria

Todo `EnrichmentResult` debe permitir reconstruir, para auditoría, de dónde vino el dato: `source_provider` (ya existe en el schema), y a nivel de implementación (no todos estos campos están en el schema de datos porque son metadatos de operación, no de negocio, pero deben quedar en el log/auditoría del conector): versión del conector/librería usada, código de error específico del proveedor cuando la consulta falla, latencia de la consulta, y si el resultado servido fue fresco o *stale fallback* (§6). Ver `docs/architecture/AUDIT_AND_OUTBOX.md` para dónde queda registrado esto.

## 8. Métricas mínimas

`enrichment_query_total` (por proveedor, por resultado: success/failed/rate_limited/circuit_open), `enrichment_latency_seconds`, `enrichment_cache_hit_ratio` (positiva vs negativa), `enrichment_cost_estimate` (cuando el proveedor cobra por consulta — permite detectar un aumento anómalo de gasto por una caché mal configurada o un ataque que genera IOCs únicos deliberadamente para agotar cuota).

## 9. Exclusión de IPs privadas/reservadas

Ninguna IP privada (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`) ni reservada (`0.0.0.0/8`, `100.64.0.0/10` CGNAT, `224.0.0.0/4` multicast, etc.) se envía a un proveedor externo de reputación de IP o GeoIP — no tiene sentido geolocalizar o consultar reputación de una IP interna, y hacerlo desperdicia cuota de consulta sin ningún valor de detección. Estas IPs producen directamente `enrichment_pending` resuelto como "no aplica" (no se agrega a la cola de enriquecimiento pendiente en `normalized_event.schema.json`), no un `query_failed`.

## 10. Estado de este documento

`policy_validation_status: DISEÑADO`. No hay conectores reales implementados, ni circuit breaker, ni métricas recolectadas — es el contrato para cuando se construyan los conectores de enriquecimiento.
