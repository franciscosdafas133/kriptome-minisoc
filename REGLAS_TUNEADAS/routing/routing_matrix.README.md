# `routing_matrix.csv` — estado de origen (v1.3.1)

**`routing_matrix.csv`** (12 columnas: Familia, RuleID, Significado real, Ruta Kriptome, Umbral, Ventana, Correlación, Fingerprint, Cambio material, IA, Comunicación, Acción de tuning) es el archivo **histórico**, mantenido a mano, con granularidad por-regla-nativa que ninguna policy captura todavía con la misma fidelidad (umbrales, ventanas de correlación específicas de cada variante de regla, notas de tuning). Sigue siendo la referencia completa para auditoría regla-por-regla.

**`routing_matrix.derived.csv`** (10 columnas: case_type, rule_id, wazuh_family, rule_validation_status, fingerprint_fields, wazuh_route, client_priority_level, human_review_required, policy_validation_status, policy_file) es un artefacto **generado automáticamente** desde `policies/case_types/*.yaml` mediante `scripts/generate_routing_matrix.py`. Sirve para verificar consistencia (¿el fingerprint que dice la policy coincide con lo esperado? ¿hay `case_type` duplicados?) — no reemplaza al CSV histórico todavía porque cubre menos columnas.

## Regla de mantenimiento

- El CSV histórico (`routing_matrix.csv`) sigue editándose a mano mientras las policies no capturen el 100% de su información.
- El CSV derivado (`routing_matrix.derived.csv`) **nunca se edita a mano** — se regenera con `python scripts/generate_routing_matrix.py` cada vez que cambia una policy. El CI verifica que no haya drift (`python scripts/generate_routing_matrix.py --check`).
- Cuando las policies capturen suficiente detalle como para que el CSV derivado reemplace al histórico, esa decisión debe registrarse como ADR (ver `docs/adr/`) y actualizarse `DOCUMENTATION_SOURCE_OF_TRUTH.md`.

Ver `DOCUMENTATION_SOURCE_OF_TRUTH.md`, fila "Origen de `routing_matrix.csv`", para el registro formal de esta decisión.
