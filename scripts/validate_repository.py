#!/usr/bin/env python3
"""Validación local de contratos del repositorio kriptome-minisoc.

Ejecuta las mismas comprobaciones principales que
.github/workflows/validate-contracts.yml. No requiere red ni un Manager
Wazuh real -- valida únicamente sintaxis y contratos de datos versionados
en este repositorio.

Uso:
    python scripts/validate_repository.py

Código de salida: 0 si todo pasa, distinto de cero si algo falla.
"""
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)

FAILURES = []
PASS_COUNT = 0


def ok(section):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"[PASS] {section}")


def fail(section, detail):
    FAILURES.append((section, detail))
    print(f"[FAIL] {section} -- {detail}")


# --------------------------------------------------------------------------
# 1. JSON syntax
# --------------------------------------------------------------------------
def check_json_syntax():
    section = "JSON syntax"
    json_files = glob.glob("specifications/**/*.json", recursive=True) + \
        glob.glob("examples/**/*.json", recursive=True) + \
        glob.glob("policies/**/*.json", recursive=True)
    bad = []
    for f in json_files:
        try:
            json.load(open(f, encoding="utf-8"))
        except json.JSONDecodeError as e:
            bad.append(f"{f}:{e.lineno} -- {e.msg}")
    if bad:
        for b in bad:
            fail(section, b)
    else:
        ok(f"{section} ({len(json_files)} archivos)")


# --------------------------------------------------------------------------
# 2. JSON Schema valid (Draft 2020-12)
# --------------------------------------------------------------------------
def check_json_schemas_valid():
    section = "JSON schemas"
    try:
        import jsonschema
    except ImportError:
        fail(section, "jsonschema no instalado (pip install jsonschema)")
        return
    schema_files = glob.glob("specifications/*.schema.json") + \
        glob.glob("examples/**/*.schema.json", recursive=True)
    bad = []
    for f in schema_files:
        schema = json.load(open(f, encoding="utf-8"))
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            bad.append(f"{f} -- {e.message}")
    if bad:
        for b in bad:
            fail(section, b)
    else:
        ok(f"{section} ({len(schema_files)} schemas, Draft 2020-12)")


def _load_schema_store():
    """Precarga los schemas de specifications/ en un dict {$id: schema} para
    resolver $ref locales sin tocar la red (los $id son URLs https://kriptome.internal/...
    que no existen de verdad)."""
    store = {}
    for f in glob.glob("specifications/*.schema.json"):
        s = json.load(open(f, encoding="utf-8"))
        if "$id" in s:
            store[s["$id"]] = s
    return store


# --------------------------------------------------------------------------
# 3. Examples vs schemas
# --------------------------------------------------------------------------
def check_examples_against_schemas():
    section = "Example validation"
    try:
        import jsonschema
        from jsonschema import RefResolver
    except ImportError:
        fail(section, "jsonschema no instalado")
        return

    store = _load_schema_store()

    def validate(schema_path, instance, label):
        schema = json.load(open(schema_path, encoding="utf-8"))
        resolver = RefResolver.from_schema(schema, store=store)
        validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
        errors = list(validator.iter_errors(instance))
        if errors:
            for e in errors:
                fail(section, f"{label} vs {schema_path}: {e.message} (path: {list(e.path)})")
            return False
        return True

    any_checked = False

    # AUTH_BRUTEFORCE_SUCCESS
    auth_in_path = "examples/client_notifications/AUTH_BRUTEFORCE_SUCCESS.input.json"
    auth_out_path = "examples/client_notifications/AUTH_BRUTEFORCE_SUCCESS.output.json"
    if os.path.exists(auth_in_path) and os.path.exists(auth_out_path):
        any_checked = True
        auth_in = json.load(open(auth_in_path, encoding="utf-8"))
        auth_out = json.load(open(auth_out_path, encoding="utf-8"))
        validate("specifications/normalized_event.schema.json", auth_in["normalized_event"], "AUTH.normalized_event")
        validate("specifications/auth_evidence.schema.json", auth_in["auth_evidence"], "AUTH.auth_evidence")
        validate("specifications/asset_context.schema.json", auth_in["asset_context"], "AUTH.asset_context")
        validate("specifications/risk_result.schema.json", auth_in["risk_result"], "AUTH.risk_result")
        validate("specifications/procedure.schema.json", auth_in["procedure"], "AUTH.procedure")
        validate("specifications/client_notification.schema.json", auth_out, "AUTH.output")

    # VULNERABILITY
    vuln_in_path = "examples/client_notifications/VULNERABILITY.input.json"
    vuln_out_path = "examples/client_notifications/VULNERABILITY.output.json"
    if os.path.exists(vuln_in_path) and os.path.exists(vuln_out_path):
        any_checked = True
        vuln_in = json.load(open(vuln_in_path, encoding="utf-8"))
        vuln_out = json.load(open(vuln_out_path, encoding="utf-8"))
        validate("specifications/normalized_event.schema.json", vuln_in["normalized_event"], "VULN.normalized_event")
        validate("specifications/enrichment_result.schema.json", vuln_in["enrichment_result"], "VULN.enrichment_result")
        validate("specifications/asset_context.schema.json", vuln_in["asset_context"], "VULN.asset_context")
        validate("specifications/risk_result.schema.json", vuln_in["risk_result"], "VULN.risk_result")
        validate("specifications/procedure.schema.json", vuln_in["procedure"], "VULN.procedure")
        validate("specifications/client_notification.schema.json", vuln_out, "VULN.output")

    # Bundle completo (envelope) vs example_input_bundle.schema.json
    bundle_schema_path = "examples/client_notifications/example_input_bundle.schema.json"
    if os.path.exists(bundle_schema_path):
        for inp in [auth_in_path, vuln_in_path]:
            if os.path.exists(inp):
                inst = json.load(open(inp, encoding="utf-8"))
                validate(bundle_schema_path, inst, f"bundle:{os.path.basename(inp)}")

    if any_checked and not FAILURES:
        ok(section)
    elif not any_checked:
        fail(section, "no se encontraron ejemplos para validar")


# --------------------------------------------------------------------------
# 4. YAML syntax
# --------------------------------------------------------------------------
def check_yaml_syntax():
    section = "YAML syntax"
    try:
        import yaml
    except ImportError:
        fail(section, "PyYAML no instalado (pip install pyyaml)")
        return
    patterns = [
        "policies/**/*.yaml",
        "procedures/**/*.yaml",
        "REGLAS_TUNEADAS/expected_results/**/*.yaml",
        "specifications/*.yaml",
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    files = sorted(set(files))
    bad = []
    for f in files:
        try:
            list(yaml.safe_load_all(open(f, encoding="utf-8").read()))
        except yaml.YAMLError as e:
            bad.append(f"{f} -- {e}")
    if bad:
        for b in bad:
            fail(section, b)
    else:
        ok(f"{section} ({len(files)} archivos)")


# --------------------------------------------------------------------------
# 5. XML well-formedness
# --------------------------------------------------------------------------
def check_xml_wellformed():
    section = "XML well-formedness"
    patterns = [
        "REGLAS_TUNEADAS/wazuh/**/*.xml",
        "REGLAS_TUNEADAS/experimental/**/*.xml",
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p, recursive=True))
    files = sorted(set(files))
    bad = []
    for f in files:
        txt = open(f, encoding="utf-8").read()
        try:
            # Los archivos son fragmentos (sin un unico root), se envuelven
            # para validar solo buena formación, no un XSD de Wazuh.
            ET.fromstring("<root>" + txt + "</root>")
        except ET.ParseError as e:
            bad.append(f"{f} -- {e}")
    if bad:
        for b in bad:
            fail(section, b)
    else:
        ok(f"{section} ({len(files)} archivos, no valida funcionamiento real en Wazuh)")


# --------------------------------------------------------------------------
# 6. Required files
# --------------------------------------------------------------------------
def check_required_files():
    section = "Required files"
    required = [
        "DOCUMENTATION_SOURCE_OF_TRUTH.md",
        "specifications/tenant.schema.json",
        "specifications/tenant_asset_assignment.schema.json",
        "specifications/case_summary.schema.json",
        "specifications/asset_context.schema.json",
        "specifications/auth_evidence.schema.json",
        "specifications/risk_result.schema.json",
        "specifications/procedure.schema.json",
        "procedures/README.md",
        "implementation/multi_tenant_two_tenant_plan.md",
    ]
    missing = [f for f in required if not os.path.exists(f)]
    if missing:
        for m in missing:
            fail(section, f"falta {m}")
    else:
        ok(f"{section} ({len(required)} archivos obligatorios presentes)")


# --------------------------------------------------------------------------
# 7. Forbidden active references
# --------------------------------------------------------------------------
def check_forbidden_references():
    section = "Forbidden active references"

    # Archivos donde estas referencias son HISTÓRICAS/documentales y por
    # tanto están explícitamente permitidas (no se buscan ahí).
    excluded_files = {
        "REGLAS_TUNEADAS/CHANGELOG.md",
        "REPO_ALIGNMENT_REPORT.md",
        "DOCUMENTATION_SOURCE_OF_TRUTH.md",
        "policies/case_types/VULNERABILITY_KEV.yaml",  # archivo de deprecación explícito
        "examples/client_notifications/README.md",     # explica por qué se corrigieron estos patrones
        "procedures/README.md",
        "README.md",
        "scripts/validate_repository.py",               # este mismo script los menciona como patrones a buscar
    }
    excluded_dirs = ("REGLAS_TUNEADAS/archive/",)

    forbidden_patterns = [
        r"Bloque A/B/C",
        r"como_responder",
        r"EJEMPLO-NO-REAL",
    ]

    search_globs = ["**/*.md", "**/*.json", "**/*.yaml", "**/*.yml"]
    hits = []
    for g in search_globs:
        for f in glob.glob(g, recursive=True):
            norm = f.replace("\\", "/")
            if norm in excluded_files:
                continue
            if any(norm.startswith(d) for d in excluded_dirs):
                continue
            if ".git/" in norm or norm.startswith(".git"):
                continue
            try:
                txt = open(f, encoding="utf-8").read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            for pat in forbidden_patterns:
                if re.search(pat, txt):
                    hits.append(f"{norm}: referencia activa no histórica a '{pat}'")

    if hits:
        for h in hits:
            fail(section, h)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 8. Consistency checks específicos de v1.3.1
# --------------------------------------------------------------------------
def check_v131_consistency():
    section = "v1.3.1 consistency"
    problems = []

    # NormalizedEvent no debe duplicar campos de capas posteriores
    ne = json.load(open("specifications/normalized_event.schema.json", encoding="utf-8"))
    forbidden_fields = [
        "asset_alias", "environment", "criticality", "business_service",
        "first_seen_at", "last_seen_at", "failed_attempt_count",
        "successful_login_count", "risk_score", "risk_factors",
    ]
    leaked = [f for f in forbidden_fields if f in ne.get("properties", {})]
    if leaked:
        problems.append(f"normalized_event.schema.json todavía expone campos de otras capas: {leaked}")

    # cisa_kev debe exigir kev_result (revisar que exista la regla allOf/if/then)
    er = json.load(open("specifications/enrichment_result.schema.json", encoding="utf-8"))
    er_text = json.dumps(er)
    if "cisa_kev" not in er_text or "kev_result" not in er_text or "allOf" not in er:
        problems.append("enrichment_result.schema.json no parece tener la regla condicional cisa_kev -> kev_result")

    # case_type de vulnerabilidad estable
    if not os.path.exists("policies/case_types/VULNERABILITY.yaml"):
        problems.append("falta policies/case_types/VULNERABILITY.yaml (case_type estable)")
    if os.path.exists("policies/case_types/VULNERABILITY_KEV.yaml"):
        vk_text = open("policies/case_types/VULNERABILITY_KEV.yaml", encoding="utf-8").read()
        if "DEPRECATED" not in vk_text and "status: DEPRECATED" not in vk_text:
            problems.append("VULNERABILITY_KEV.yaml existe pero no está marcado DEPRECATED")

    # asset_context debe tener environment_type + site_type, no environment
    ac = json.load(open("specifications/asset_context.schema.json", encoding="utf-8"))
    if "environment" in ac.get("properties", {}):
        problems.append("asset_context.schema.json todavía tiene el campo 'environment' plano (debe ser environment_type + site_type)")
    if "environment_type" not in ac.get("properties", {}) or "site_type" not in ac.get("properties", {}):
        problems.append("asset_context.schema.json no tiene environment_type/site_type")

    if problems:
        for p in problems:
            fail(section, p)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 9. CSV drift: routing_matrix.csv historico vs routing_matrix.derived.csv
#    (generado desde policies/case_types/*.yaml, ver scripts/generate_routing_matrix.py)
# --------------------------------------------------------------------------
def check_csv_drift():
    section = "CSV drift (routing matrix)"
    derived_path = "REGLAS_TUNEADAS/routing/routing_matrix.derived.csv"
    if not os.path.exists(derived_path):
        fail(section, f"falta {derived_path} -- ejecutar scripts/generate_routing_matrix.py --check")
        return
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/generate_routing_matrix.py", "--check"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            fail(section, f"routing_matrix.derived.csv desactualizado respecto a policies/case_types/*.yaml -- {result.stdout.strip()} {result.stderr.strip()}")
        else:
            ok(section)
    except Exception as e:
        fail(section, f"no se pudo ejecutar generate_routing_matrix.py --check -- {e}")


# --------------------------------------------------------------------------
# 10. Markdown internal links (enlaces relativos a archivos del propio repo)
# --------------------------------------------------------------------------
def check_markdown_internal_links():
    section = "Markdown internal links"
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    bad = []
    md_files = glob.glob("**/*.md", recursive=True)
    for f in md_files:
        norm = f.replace("\\", "/")
        if ".git/" in norm:
            continue
        try:
            txt = open(f, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        base_dir = os.path.dirname(f)
        for link in link_re.findall(txt):
            target = link.split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("/"):
                continue  # rutas absolutas del host, no se resuelven aqui
            candidate = os.path.normpath(os.path.join(base_dir, target))
            if not os.path.exists(candidate):
                bad.append(f"{norm}: enlace roto a '{target}'")
    if bad:
        for b in bad:
            fail(section, b)
    else:
        ok(f"{section} ({len(md_files)} archivos .md revisados)")


# --------------------------------------------------------------------------
# 11. Prohibicion: data.labels.* (las labels de Wazuh viven en agent.labels.*,
#     nunca en data.labels.* -- ver specifications/wazuh_alert_field_paths.md)
# --------------------------------------------------------------------------
def check_no_data_labels():
    section = "Prohibicion data.labels.*"
    pattern = re.compile(r"data\.labels\.(client_id|client_code|asset_id|asset_code)")
    excluded_files = {
        "specifications/wazuh_alert_field_paths.md",  # documenta el error para explicarlo
        "scripts/validate_repository.py",
    }
    hits = []
    for g in ["**/*.md", "**/*.json", "**/*.yaml", "**/*.yml", "**/*.xml", "**/*.conf", "**/*.example"]:
        for f in glob.glob(g, recursive=True):
            norm = f.replace("\\", "/")
            if norm in excluded_files or ".git/" in norm:
                continue
            try:
                txt = open(f, encoding="utf-8").read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            if pattern.search(txt):
                hits.append(f"{norm}: referencia a data.labels.* (debe ser agent.labels.*)")
    if hits:
        for h in hits:
            fail(section, h)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 12. Prohibicion: contactos/PII en labels de agente (client_name, asset_alias,
#     email, telefono dentro de un bloque <labels> de agent-conf)
# --------------------------------------------------------------------------
def check_no_pii_in_agent_labels():
    section = "Prohibicion PII en agent labels"
    hits = []
    forbidden_label_keys = ("client_name", "asset_alias", "contact_email", "contact_phone", "email", "telefono")
    for f in glob.glob("REGLAS_TUNEADAS/agent-conf/**/*", recursive=True):
        norm = f.replace("\\", "/")
        if not os.path.isfile(f):
            continue
        try:
            txt = open(f, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        for key in forbidden_label_keys:
            if re.search(rf'<label\s+key="{key}"', txt):
                hits.append(f"{norm}: label prohibida '{key}' (PII/dato de negocio, no un codigo operativo -- ver specifications/wazuh_alert_field_paths.md)")
    if hits:
        for h in hits:
            fail(section, h)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 13. Prohibicion: regla 100040 (CISA KEV custom) cargada como produccion
# --------------------------------------------------------------------------
def check_100040_not_production():
    section = "100040 no cargada en produccion"
    problems = []
    if not os.path.exists("REGLAS_TUNEADAS/experimental/100040_cisa_kev.xml"):
        problems.append("falta REGLAS_TUNEADAS/experimental/100040_cisa_kev.xml (debe existir como EXPERIMENTAL, no borrado)")
    snippet = "REGLAS_TUNEADAS/wazuh/config/ossec.conf.ruleset.snippet.xml"
    if os.path.exists(snippet):
        txt = open(snippet, encoding="utf-8").read()
        if "experimental" in txt.lower() and re.search(r"<rule_dir>\s*etc/rules/experimental", txt):
            problems.append(f"{snippet}: parece cargar etc/rules/experimental -- 100040 no debe estar activa en produccion")
    active_rules = "REGLAS_TUNEADAS/wazuh/rules/kriptome_local_rules.xml"
    if os.path.exists(active_rules):
        txt = open(active_rules, encoding="utf-8").read()
        if re.search(r'<rule\s+id="100040"', txt):
            problems.append(f"{active_rules}: la regla 100040 aparece activa en el ruleset de produccion")
    if problems:
        for p in problems:
            fail(section, p)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 14. Prohibicion: assert como control de tenant/seguridad
# --------------------------------------------------------------------------
def check_no_assert_as_control():
    section = "Prohibicion assert como control de seguridad"
    pattern = re.compile(r"^\s*assert\s+tenant", re.MULTILINE)
    hits = []
    for g in ["**/*.py", "**/*.md"]:
        for f in glob.glob(g, recursive=True):
            norm = f.replace("\\", "/")
            if ".git/" in norm:
                continue
            try:
                txt = open(f, encoding="utf-8").read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            for m in pattern.finditer(txt):
                # Permitir el propio ejemplo documentado como "INCORRECTO" (contexto negativo)
                context = txt[max(0, m.start() - 200):m.start()]
                if "INCORRECTO" in context or "incorrecto" in context or "nunca:" in context.lower():
                    continue
                hits.append(f"{norm}: uso de 'assert tenant...' como posible control de seguridad")
    if hits:
        for h in hits:
            fail(section, h)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 15. Single state machine: case.schema.json no debe redefinir un enum de
#     estados propio distinto al de policies/case_state_machine.yaml
# --------------------------------------------------------------------------
def check_single_state_machine():
    section = "Single state machine"
    problems = []
    sm_path = "policies/case_state_machine.yaml"
    case_schema_path = "specifications/case.schema.json"
    if not os.path.exists(sm_path):
        problems.append(f"falta {sm_path}")
    else:
        import yaml
        sm = yaml.safe_load(open(sm_path, encoding="utf-8"))
        raw_states = sm.get("states", [])
        sm_states = set()
        for s in raw_states:
            if isinstance(s, dict) and "name" in s:
                sm_states.add(s["name"])
            elif isinstance(s, str):
                sm_states.add(s)
        cs = json.load(open(case_schema_path, encoding="utf-8"))
        case_states = set(cs.get("properties", {}).get("status", {}).get("enum", []))
        if sm_states and case_states and sm_states != case_states:
            problems.append(f"case.schema.json.status enum {sorted(case_states)} no coincide con policies/case_state_machine.yaml states {sorted(sm_states)}")
        legacy_states = {"open", "pending_human_review", "pending_client_response", "closed_resolved", "closed_false_positive", "closed_auto", "reopened"}
        if case_states & legacy_states:
            problems.append(f"case.schema.json todavia usa estados legacy: {case_states & legacy_states}")
    if problems:
        for p in problems:
            fail(section, p)
    else:
        ok(section)


# --------------------------------------------------------------------------
# 16. Duplicate case_types en policies/case_types/*.yaml (excluyendo DEPRECATED)
# --------------------------------------------------------------------------
def check_duplicate_case_types():
    section = "Duplicate case_types"
    import yaml
    seen = {}
    problems = []
    for f in sorted(glob.glob("policies/case_types/*.yaml")):
        data = yaml.safe_load(open(f, encoding="utf-8"))
        if not data:
            continue
        status = data.get("policy_validation_status") or data.get("status")
        if status == "DEPRECATED":
            continue
        ct = data.get("case_type")
        if not ct:
            continue
        if ct in seen:
            problems.append(f"case_type '{ct}' duplicado entre {seen[ct]} y {f}")
        else:
            seen[ct] = f
    if problems:
        for p in problems:
            fail(section, p)
    else:
        ok(f"{section} ({len(seen)} case_types activos, sin duplicados)")


# --------------------------------------------------------------------------
# 17. Referencias a schemas inexistentes: todo "specifications/X.schema.json"
#     mencionado en .md/.yaml debe existir como archivo real
# --------------------------------------------------------------------------
def check_referenced_schemas_exist():
    section = "Referencias a schemas inexistentes"
    pattern = re.compile(r"specifications/([a-zA-Z0-9_\-]+\.schema\.json)")
    missing = set()
    for g in ["**/*.md", "**/*.yaml", "**/*.yml"]:
        for f in glob.glob(g, recursive=True):
            norm = f.replace("\\", "/")
            if ".git/" in norm:
                continue
            try:
                txt = open(f, encoding="utf-8").read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            for name in pattern.findall(txt):
                path = f"specifications/{name}"
                if not os.path.exists(path):
                    missing.add(f"{path} (referenciado en {norm})")
    if missing:
        for m in sorted(missing):
            fail(section, m)
    else:
        ok(section)


def main():
    print(f"Validando repositorio en: {REPO_ROOT}\n")
    check_json_syntax()
    check_json_schemas_valid()
    check_examples_against_schemas()
    check_yaml_syntax()
    check_xml_wellformed()
    check_required_files()
    check_forbidden_references()
    check_v131_consistency()
    check_csv_drift()
    check_markdown_internal_links()
    check_no_data_labels()
    check_no_pii_in_agent_labels()
    check_100040_not_production()
    check_no_assert_as_control()
    check_single_state_machine()
    check_duplicate_case_types()
    check_referenced_schemas_exist()

    print()
    print(f"Resultado: {PASS_COUNT} secciones OK, {len(FAILURES)} fallos.")
    if FAILURES:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
