# Mapeo de campos de notificación

Tabla de trazabilidad: qué texto ve el cliente, de qué campo técnico sale, en qué objeto vive, y su sensibilidad. Sirve para auditar que ningún dato sensible o no verificado llegue al cuerpo del correo, y para que cualquier implementación futura sepa exactamente de dónde traer cada dato.

Convenciones de la tabla:
- **Puede mostrarse al cliente**: si es "No", el campo solo puede ir en `technical_appendix` / `detalle_soporte_tecnico`.
- **Fallback**: qué se muestra/hace si el campo es `null` o no está disponible.
- **Sensibilidad**: `pública` (sin riesgo), `interna` (dato operativo, no confidencial), `sensible` (dato que podría ayudar a un atacante o exponer información privada si se filtra).

| Texto visible | Campo | Objeto de origen | Fuente original | Obligatorio/Opcional | Fallback | Puede mostrarse al cliente | Sensibilidad |
|---|---|---|---|---|---|---|---|
| Código del caso | `case_id` | `client_notification` | Generado al abrir el caso (`case.schema.json`) | Obligatorio | — (siempre presente) | Sí | interna |
| Equipo afectado | `asset_alias` | `incident_facts` / `asset_context` | Label `agent.labels.asset_alias` (ver `REGLAS_TUNEADAS/agent-conf/`) | Obligatorio si el case_type tiene asset | Si null: usar `asset_id` con advertencia interna de onboarding incompleto (nunca mostrar el `asset_id` crudo al cliente) | Sí | pública |
| Función del equipo | `business_service` | `incident_facts` / `asset_context` | Registro manual de CMDB en onboarding (no hay fuente automática) | Opcional | Omitir la frase si es null (no inventar un servicio) | Sí | interna |
| Entorno | `environment` | `incident_facts` / `asset_context` | Label `agent.labels.environment` | Opcional | Omitir | No (dato técnico interno, va a `technical_appendix` si se necesita) | interna |
| Criticidad | `criticality` | `incident_facts` / `asset_context` | Label `agent.labels.criticality` | Opcional (pero alimenta `priority_level`, que sí es obligatorio) | Tratar como `medium` solo a nivel de cálculo de riesgo, nunca mostrar un valor inventado al cliente | No directamente (se traduce a `nivel_de_atencion`) | interna |
| Cuenta utilizada | `target_user` | `incident_facts` / `auth_evidence` | `win.eventdata.targetUserName` / `dstuser` (ver `GUIA_CAMPOS_ENRIQUECIMIENTO.docx`) | Opcional (solo case_types de autenticación) | Omitir la frase con la cuenta si es null | Sí, **pero solo con la redacción correcta según `matching_user_verified`** (ver `auth_evidence.schema.json`) | sensible |
| Dirección de origen | `source_ip` | `incident_facts` | `srcip` / `win.eventdata.ipAddress` / `office365.ClientIP` | Opcional | Omitir | No en el cuerpo dirigido al cliente (va a `technical_appendix`); el cuerpo dice "una dirección de internet" sin mostrar la IP cruda, salvo que el cliente la pida | sensible |
| Tipo de conexión | `access_type` | `incident_facts` | Traducción de `win.eventdata.logonType` (ver `auth_evidence.logon_type_label`) | Opcional | Omitir la frase | Sí (ya traducido a lenguaje simple, p. ej. "por escritorio remoto") | interna |
| Equipo de origen | `workstation_name` | `incident_facts` | `win.eventdata.workstationName` | Opcional | Omitir | No (va a `technical_appendix`) | sensible |
| Primera actividad | `first_seen_at` | `incident_facts` / `case_summary` | Timestamp del primer evento correlacionado | Opcional | Usar solo `last_seen_at` si `first_seen_at` es null | Sí (en formato de fecha/hora local de Perú) | interna |
| Última actividad | `last_seen_at` | `incident_facts` / `case_summary` | Timestamp del evento más reciente | Opcional | Usar `timestamp` del evento individual | Sí | interna |
| Hora del acceso exitoso | `successful_login_at` | `incident_facts` / `auth_evidence` | Timestamp del evento de login exitoso (100012/100013) | Opcional (solo si `successful_login_count > 0`) | Omitir la frase | Sí | interna |
| Intentos fallidos | `failed_attempt_count` | `incident_facts` / `auth_evidence` / `case_summary` | Contador de la correlación (100010/100011/60204, según regla) | Opcional | Omitir el número, describir cualitativamente ("varios intentos") si no hay conteo exacto | Sí, **con la redacción correcta**: solo se puede vincular al `target_user` si `matching_user_verified=true`; si no, se describe "desde la misma dirección" sin nombrar la cuenta en esa frase (ver regla crítica en `auth_evidence.schema.json`) | interna |
| Accesos exitosos | `successful_login_count` | `incident_facts` / `auth_evidence` | Contador de eventos de login exitoso en la ventana | Opcional | Asumir 1 si el caso es `AUTH_BRUTEFORCE_SUCCESS` (por definición hubo al menos uno) | Sí | interna |
| Ubicación aproximada | `geo_country` / `geo_city` | `incident_facts` | Enriquecimiento externo GeoIP (`enrichment_result`, tipo `geoip`) — **nunca nativo de Wazuh** | Opcional | Omitir la frase de ubicación si el enriquecimiento no se resolvió (`query_failed=true` o pendiente) | Sí, solo si el enriquecimiento se completó | interna |
| Proveedor de Internet | `isp_or_asn` | `incident_facts` | Enriquecimiento externo (GeoIP/reputación) | Opcional | Omitir | Sí, si está disponible | interna |
| Reputación | `reputation_verdict` | `incident_facts` | Enriquecimiento externo `ip_reputation` / `hash_reputation` | Opcional | Omitir la frase de reputación (no asumir "desconocida" como si fuera un veredicto) | Sí, en lenguaje simple (p. ej. "dirección conocida por ataques anteriores") | interna |
| Origen visto anteriormente | `source_seen_before` | `incident_facts` | Caché de IOC de la App (histórico interno, no un proveedor externo) | Opcional | Omitir | Sí | interna |
| Origen autorizado | `authorized_source_match` | `incident_facts` | Comparación contra lista de fuentes autorizadas del tenant (si el cliente la configuró) | Opcional | Si no hay lista configurada: `null`, y NO se afirma "no autorizado" — se omite la frase | Sí, solo cuando hay una lista configurada para comparar | interna |
| Nivel de riesgo | `priority_level` | `risk_explanation` / `risk_result` | Calculado por la política del `case_type` (`policies/case_types/*.yaml`) — **no es una copia de `rule_level`** | Obligatorio | No aplica (siempre calculado antes de notificar) | Sí, traducido a "Informativo/Atención/Urgente/Crítico" | interna |
| Factores de riesgo | `risk_factors` | `risk_explanation` / `risk_result` | Lista de factores concretos (ver `risk_result.schema.json` enum de `factor`) | Opcional | Lista vacía si el modelo aún no calcula factores (nunca inventar un factor) | Sí, redactados en lenguaje simple en `por_que_importa` (no como lista técnica) | interna |
| Acciones | `customer_actions` | `action_plan` | `procedure.schema.json` — **la IA no inventa acciones fuera de un procedure aprobado** | Obligatorio | Si no hay `procedure` aprobado: el caso va a cola humana, no se comunica con acciones improvisadas | Sí | pública |
| Prohibiciones | `do_not_do` | `action_plan` | `procedure.schema.json` | Obligatorio (aunque sea lista vacía) | Lista vacía si el procedimiento no define ninguna | Sí | pública |
| Evidencia a conservar | `evidence_to_preserve` | `action_plan` | `procedure.schema.json` | Opcional | Omitir la sección si está vacía | Sí | pública |
| Plazo | `recommended_deadline` | `action_plan` | `procedure.schema.json`, ajustado por Kriptome (no se copia literal el `dueDate` de CISA cuando aplica KEV) | Opcional | Si null: "sin plazo específico" (no inventar un número de horas) | Sí, traducido a lenguaje simple (p. ej. "72 horas") | pública |
| Contacto de escalamiento | `escalation_contact` | `action_plan` | Configuración del SLA del tenant | Opcional | Usar el contacto genérico de soporte de Kriptome | Sí | interna |

## Campos que NUNCA aparecen en el cuerpo dirigido al cliente

Estos solo existen en `technical_appendix` / `detalle_soporte_tecnico`, y solo se muestran si el cliente tiene soporte técnico propio que los necesite:

`rule_ids`, `event_ids`, `raw_event_references`, `mitre_ids`, `hostname`, `workstation_name` (fuera de la traducción a `access_type`), `source_ip` (fuera de la mención genérica "una dirección de internet"), `logon_type` crudo (solo se muestra su traducción `access_type`), `provider_references`.

## Regla general de fallback

Ningún campo de esta tabla se rellena con un valor inventado cuando falta el dato real. La regla por defecto es **omitir la frase correspondiente**, no sustituirla por un placeholder genérico ("desconocido", "N/A") que podría leerse como un dato real. La única excepción documentada es la traducción de estados explícitos (p. ej. `kev_status='no_cve'` sí se representa como un valor explícito, porque documenta *por qué* algo no se hizo, no rellena un dato ausente).
