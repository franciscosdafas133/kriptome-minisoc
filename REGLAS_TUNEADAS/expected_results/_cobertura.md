# Cobertura de expected_results/ vs reglas custom

| Regla custom | Fixture | Expected result | Motivo si falta |
|---|---|---|---|
| 100010 (roll-up SSH) | `test_data/ssh_samples.log` | `ssh_samples.expected.yaml` | — |
| 100011 (brute force Win por cuenta) | `test_data/windows_4625_eventchannel.json` | `windows_4625_eventchannel.expected.yaml` | — |
| 100012 (login SSH OK tras BF) | `test_data/ssh_samples.log` | `ssh_samples.expected.yaml` | — |
| 100013 (login Win OK tras BF) | `test_data/windows_4625_eventchannel.json` | `windows_4625_eventchannel.expected.yaml` | — |
| 100030 (FIM whitelist) | **no existe fixture de texto** | no aplica a `wazuh-logtest` | FIM lo genera el módulo `syscheck` sobre cambios reales de archivos, no un log de texto reproducible por `wazuh-logtest -q`. Se valida end-to-end (agente → Manager → Indexer), igual que FIM/Vulnerability Detector/SCA en general (ver nota final de `RESULTADOS_ESPERADOS.docx`). No se inventa un fixture sintético de syscheck porque el formato interno de esos eventos no es un log de texto — sería fabricar una prueba no representativa. |
| 100040 (CISA KEV) — EXPERIMENTAL | no aplica | no aplica | La regla está en `experimental/`, no en el set activo. No se crea fixture porque (a) la regla no se carga en producción y (b) depende del módulo Vulnerability Detector, no de logtest. |

**Regla general aplicada:** no se inventó ningún fixture ni expected result para reglas cuyo evento de origen no es un log de texto reproducible por `wazuh-logtest`. Esto es consistente con la instrucción de "no inventar resultados de pruebas": mejor una casilla vacía documentada que un fixture fabricado que aparente cobertura donde no la hay.
