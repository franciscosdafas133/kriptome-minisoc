# archive/pre-v1.2.0-paths/

Este directorio documenta el mapeo de rutas ANTES/DESPUÉS de la reestructuración v1.2.0, para que los documentos `GUIA_DE_DESPLIEGUE.docx` y `EXPLICACION_DEL_TUNING.docx` (no editados, por alcance del prompt de alineación técnica) sigan siendo utilizables sin ambigüedad.

## Mapeo de rutas (v1.1.0 → v1.2.0)

| Ruta en los .docx (v1.1.0, sin cambios) | Ruta real actual (v1.2.0) |
|---|---|
| `rules/kriptome_local_rules.xml` | `wazuh/rules/kriptome_local_rules.xml` |
| `decoders/kriptome_local_decoders.xml` | `wazuh/decoders/kriptome_local_decoders.xml` |
| `config/ossec.conf.ruleset.snippet.xml` | `wazuh/config/ossec.conf.ruleset.snippet.xml` |
| `test_data/` | `test_data/` (sin cambio — fixtures de entrada) |
| `test_data/*.log`, `test_data/*.json` esperados | ver `expected_results/` (nuevo — expected results estructurados, separados de los fixtures de entrada) |

**Nota para quien ejecute el runbook de `GUIA_DE_DESPLIEGUE.docx`:** donde el documento indique `cp rules/kriptome_local_rules.xml ...`, usar `cp wazuh/rules/kriptome_local_rules.xml ...` (mismo archivo, ruta actualizada). El documento no fue editado porque está fuera del alcance de esta pasada de alineación técnica (ver `REPO_ALIGNMENT_REPORT.md` §1); este archivo es el puente explícito entre ambos.
