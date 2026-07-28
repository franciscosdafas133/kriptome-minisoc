# Dimensionamiento y continuidad

`policy_validation_status: DISEÑADO`. Contrato de qué variables determinan el dimensionamiento de un despliegue de Kriptome MiniSOC, y de los "gates" (compuertas de aprobación) que deben cumplirse antes de poder afirmar que existe continuidad operativa real. NO implica infraestructura dimensionada ni backups configurados hoy — ver `README.md` §"Qué NO está implementado".

## 1. Por qué no hay un número fijo de "EPS soportados" en este repo

No se publica una cifra única de capacidad porque el requerimiento real depende de una combinación de variables específicas de cada despliegue, no de una tabla genérica. Publicar un número sin contexto (p. ej. "soporta 1000 EPS") sería una afirmación no verificable — el mismo tipo de inflación de estado que el resto de este repositorio evita explícitamente (`VALIDADO-*` sin evidencia, `approved` sin aprobación real).

## 2. Variables que determinan el dimensionamiento

| Variable | Por qué importa |
|---|---|
| EPS (eventos por segundo) | Determina throughput de ingesta (Manager) e indexación (Indexer). |
| Proporción archives vs alerts | Wazuh puede indexar todos los eventos (`archives`) o solo los que disparan una regla (`alerts`) — `archives` multiplica el volumen de almacenamiento e indexación varias veces frente a solo `alerts`. |
| Retención (días) | Volumen de almacenamiento total = EPS promedio × tamaño medio de evento × días de retención — variable directamente proporcional al costo de almacenamiento. |
| Cantidad de agentes | Afecta carga de conexión/keepalive en el Manager, independiente del volumen de eventos que cada agente genere. |
| Uso de FIM (File Integrity Monitoring) | Puede generar picos de EPS significativos durante escaneos programados (`scan_time`/`scan_day`) o cambios masivos (una actualización de software que toca miles de archivos monitoreados). |
| Uso de Sysmon (Windows) | Sysmon con configuración amplia (todos los Event IDs) genera EPS por endpoint sustancialmente mayor que auditoría nativa de Windows sola. |
| Vulnerability Detector | Corre en ciclos periódicos (no en tiempo real), pero el ciclo de escaneo completo de todo el parque genera un pico de EPS concentrado en una ventana, no un promedio constante. |
| Integraciones externas (M365, AWS, GCP, Azure, etc.) | Cada integración activa añade su propio volumen de eventos, independiente del EPS de los endpoints — ver `REGLAS_TUNEADAS/wazuh/config/ossec.conf.ruleset.snippet.xml` sobre por qué estas integraciones son decisiones de parque completo del Manager, no solo de un tenant. |
| Overhead del Indexer (OpenSearch) | Índices, replicas, shards, y el propio overhead de indexación (no solo el volumen de datos crudo) — un Indexer subdimensionado en shards/heap se degrada bajo carga aunque el volumen de datos "quepa" en disco. |

El dimensionamiento real de un despliegue concreto es la salida de aplicar estas variables a las características del cliente/tenant en cuestión — no un valor genérico aplicable a cualquier despliegue.

## 3. Continuidad — qué queda explícitamente pendiente

Los siguientes puntos son requisitos de continuidad operativa que **no están resueltos** en este repositorio y no deben inflarse como si lo estuvieran:

- **RPO (Recovery Point Objective)** — cuánta pérdida de datos es aceptable en un desastre (p. ej. "máximo 1 hora de eventos perdidos"). No hay un valor aprobado; depende del acuerdo comercial con cada tenant.
- **RTO (Recovery Time Objective)** — cuánto tiempo puede estar el servicio caído antes de restaurar. Mismo estado: no hay valor aprobado.
- **Retención de backups** — cuántas copias históricas se conservan y por cuánto tiempo, distinto de la retención de eventos en el Indexer (§2).
- **Procedimiento de restauración** — pasos concretos, verificados, para reconstruir un Manager/Indexer/base de datos desde backup. No documentado ni probado en este repo.
- **Almacenamiento en frío (cold storage)** — si existe un nivel de retención más barato/lento para datos históricos más allá de la retención "caliente" del Indexer. No decidido.

## 4. Gates de aprobación

Ningún despliegue de Kriptome MiniSOC debe presentarse como "listo para producción" respecto a continuidad si no puede marcar, con evidencia real (no una intención documentada), estas cuatro compuertas:

| Gate | Qué certifica | Evidencia mínima requerida |
|---|---|---|
| `BACKUP_CONFIGURED` | Existe un mecanismo de backup activo y corriendo (no solo un script escrito) para Manager, Indexer y base de datos del motor de casos. | Registro de backups ejecutados exitosamente en el tiempo (no una única ejecución manual de prueba). |
| `RESTORE_TESTED` | Se ejecutó una restauración real desde un backup, en un entorno separado del de producción, y el resultado se verificó contra datos conocidos. | Fecha de la prueba, entorno usado, qué se verificó, resultado — mismo estándar de evidencia que `VALIDADO-LOGTEST`/`VALIDADO-SHADOW` en `REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml`: sin evidencia guardada, no se marca. |
| `RPO_APPROVED` | El RPO objetivo fue acordado explícitamente (con el negocio, y cuando aplica con el tenant) y la frecuencia de backup real medida es consistente con ese objetivo. | Documento/acuerdo con el valor de RPO y la frecuencia de backup que lo respalda. |
| `RTO_APPROVED` | El RTO objetivo fue acordado y el tiempo de restauración medido en la prueba de `RESTORE_TESTED` es consistente con ese objetivo. | Tiempo real medido en la prueba de restauración, comparado contra el RTO acordado. |

**Ninguno de estos cuatro gates está cumplido hoy en este repositorio.** No se marca ninguno como aprobado sin la evidencia descrita — este documento existe precisamente para que la ausencia de continuidad probada sea visible y explícita, no para simular que ya existe.

## 5. Relación con otros documentos

- `docs/architecture/POSTGRES_TENANT_ISOLATION.md` — el rol `kriptome_maintenance` (§5 de ese documento) es quien ejecutaría operaciones de backup/restore sobre la base de datos, bajo el mismo requisito de auditoría.
- `docs/architecture/INGESTION_DESIGN.md` §11 — la recuperación de checkpoint tras un reinicio es un mecanismo de continuidad de nivel de aplicación, distinto de (pero complementario a) la continuidad de infraestructura descrita aquí.

## 6. Estado de este documento

`policy_validation_status: DISEÑADO`. Ningún gate de §4 está cumplido; los valores de RPO/RTO no están acordados; no existe un procedimiento de restauración probado. Este documento es el marco para trackear ese trabajo, no una certificación de que ya se hizo.
