#!/usr/bin/env python3
"""Generate annotated RPM installer inventory files for AAP 2.4, 2.5, and 2.6."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AAP_REPO_ROOT = REPO_ROOT.parent


@dataclass
class RpmVersionConfig:
    version: str
    aap_dir: str
    installer_glob: str
    profile: str  # "legacy" (2.4) or "gateway" (2.5+)

    @property
    def out_dir(self) -> Path:
        return REPO_ROOT / self.aap_dir / "rpm"

    @property
    def doc_base(self) -> str:
        if self.profile == "legacy":
            return (
                "https://access.redhat.com/documentation/en-us/"
                f"red_hat_ansible_automation_platform/{self.version}/html-single/"
                "red_hat_ansible_automation_platform_installation_guide/index"
            )
        return (
            f"https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/"
            f"{self.version}/html/rpm_installation"
        )

    @property
    def ee_image_base(self) -> str:
        ns = self.version.replace(".", "")
        return f"registry.redhat.io/ansible-automation-platform-{ns}/"


VERSIONS: dict[str, RpmVersionConfig] = {
    "2.4": RpmVersionConfig(
        version="2.4",
        aap_dir="AAP24",
        installer_glob="ansible-automation-platform-setup-2.4-*",
        profile="legacy",
    ),
    "2.5": RpmVersionConfig(
        version="2.5",
        aap_dir="AAP25",
        installer_glob="ansible-automation-platform-setup-2.5-*",
        profile="gateway",
    ),
    "2.6": RpmVersionConfig(
        version="2.6",
        aap_dir="AAP26",
        installer_glob="ansible-automation-platform-setup-2.6-*",
        profile="gateway",
    ),
}


def installer_inventory_path(cfg: RpmVersionConfig) -> Path:
    dump_dir = AAP_REPO_ROOT / ".installer-dumps" / cfg.version
    matches = sorted(p for p in dump_dir.glob(cfg.installer_glob) if p.is_dir())
    if not matches:
        raise FileNotFoundError(f"No installer dump matching {dump_dir}/{cfg.installer_glob}")
    return matches[0] / "inventory"


def enabled_var_names(inventory_text: str) -> set[str]:
    in_all = False
    names: set[str] = set()
    for line in inventory_text.splitlines():
        stripped = line.strip()
        if stripped == "[all:vars]":
            in_all = True
            continue
        if in_all and stripped.startswith("["):
            break
        if not in_all or not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            names.add(stripped.split("=")[0].strip())
    return names


def section(title: str) -> list[tuple[str, str, str | None]]:
    return [("__SECTION__", title, None)]


# fmt: (name, comment, example_value) — example_value=None => vars-example.yml only
EXTRA_CATALOG: list[tuple[str, str, str | None]] = [
    *section("Bundle / offline install"),
    ("bundle_install", "Use offline bundle installer instead of pulling from registry/repos", "false"),
    ("bundle_install_folder", "Directory containing the offline bundle", "/var/lib/ansible-automation-platform-bundle"),
    *section("Package versions"),
    ("controller_package_version", "Pin Automation Controller RPM version (empty = latest from repos)", ""),
    ("automationhub_package_version", "Pin Automation Hub RPM version", ""),
    ("automationedacontroller_package_version", "Pin Automation EDA Controller RPM version", ""),
    *section("Automation Controller"),
    ("admin_username", "Controller admin username", "admin"),
    ("admin_email", "Controller admin email", "admin@example.com"),
    ("create_preload_data", "Load default job templates and preload data on first install", "true"),
    ("controller_nginx_tls_files_remote", "Controller TLS cert/key files are on the remote host", "false"),
    ("automationcontroller_client_max_body_size", "Controller nginx client_max_body_size", "5m"),
    ("nginx_disable_https", "Serve Controller over HTTP only", "false"),
    ("nginx_disable_hsts", "Disable HSTS on Controller nginx", "false"),
    ("nginx_http_port", "Controller nginx HTTP port", "80"),
    ("nginx_https_port", "Controller nginx HTTPS port", "443"),
    ("nginx_tls_protocols", "Controller nginx TLS protocols; list — use vars.yml", None),
    ("nginx_user_headers", "Custom Controller nginx headers; list — use vars.yml", None),
    *section("Receptor / execution"),
    ("receptor_listener_protocol", "Receptor listener protocol (tcp or udp)", "tcp"),
    ("node_type", "Host var on controller/execution_nodes: control|hybrid|hop|execution", "hybrid"),
    *section("Certificate authority"),
    ("aap_ca_cert_file", "Path to custom CA certificate for signing component certs", "/path/to/ca.crt"),
    ("aap_ca_key_file", "Path to custom CA private key", "/path/to/ca.key"),
    ("aap_ca_cert_files_remote", "CA cert/key files are on remote hosts", "false"),
    ("aap_ca_regenerate", "Regenerate the internally managed CA key pair", "false"),
    ("aap_service_regen_cert", "Regenerate component certificates signed by internal CA", "false"),
    ("aap_service_san_records", "Extra SAN records for component certs; list — use vars.yml", None),
    *section("Automation Hub (extra)"),
    ("automationhub_user_headers", "Custom Hub nginx headers; list — use vars.yml", None),
    ("automationhub_nginx_tls_files_remote", "Hub TLS cert/key files are on the remote host", "false"),
    ("automationhub_enable_api_access_log", "Log all Hub API access to /var/log/galaxy_api_access.log", "false"),
    ("automationhub_enable_unauthenticated_collection_access", "Allow read-only collection access without login", "false"),
    ("automationhub_enable_unauthenticated_collection_download", "Allow anonymous collection downloads", "false"),
    ("automationhub_ldap_user_search_scope", "LDAP user search scope (SUBTREE, ONELEVEL, BASE)", "SUBTREE"),
    ("automationhub_ldap_group_search_scope", "LDAP group search scope", "SUBTREE"),
    ("automationhub_ldap_user_search_filter", "LDAP user search filter", "(uid=%(user)s)"),
    ("automationhub_ldap_group_search_filter", "LDAP group search filter", "(objectClass=Group)"),
    ("automationhub_ldap_group_type_class", "LDAP group type class for django-auth-ldap", "django_auth_ldap.config:GroupOfNamesType"),
    ("ldap_extra_settings", "Extra LDAP settings dictionary; use vars.yml", None),
    *section("Automation EDA Controller (extra)"),
    ("automationedacontroller_admin_username", "EDA admin username", "admin"),
    ("automationedacontroller_admin_email", "EDA admin email", "admin@example.com"),
    ("automationedacontroller_disable_https", "Serve EDA over HTTP only", "false"),
    ("automationedacontroller_disable_hsts", "Disable HSTS on EDA nginx", "false"),
    ("automationedacontroller_nginx_tls_files_remote", "EDA TLS cert/key files are on the remote host", "false"),
    ("automationedacontroller_http_port", "EDA nginx HTTP port", "80"),
    ("automationedacontroller_https_port", "EDA nginx HTTPS port", "443"),
    ("automationedacontroller_user_headers", "Custom EDA nginx headers; list — use vars.yml", None),
    ("automationedacontroller_allowed_hostnames", "Extra allowed hostnames for EDA; list — use vars.yml", None),
    ("automationedacontroller_trusted_origins", "Trusted CSRF origins; list — use vars.yml", None),
    ("automationedacontroller_safe_plugins", "Allowlisted EDA rulebook plugins; list — use vars.yml", None),
    ("automationedacontroller_max_running_activations", "Max running activations per worker", "12"),
    ("automationedacontroller_gunicorn_workers", "EDA API gunicorn workers", "5"),
    ("automationedacontroller_activation_workers", "EDA ansible-rulebook activation workers", "5"),
    ("automationedacontroller_debug", "Enable Django debug mode for EDA workers", "false"),
    ("automationedacontroller_websocket_ssl_verify", "Verify SSL for Daphne websocket connections", "true"),
    ("decision_environments", "Decision environments to configure in EDA; list — use vars.yml", None),
    *section("Execution environments"),
    ("ee_image_base", "Base URL/path for execution environment images", "__EE_IMAGE_BASE__"),
    ("extra_images", "Additional execution environment images; list — use vars.yml", None),
    ("ee_images", "Execution environment image list override; list — use vars.yml", None),
    ("de_images", "Decision environment images; list — use vars.yml", None),
    ("global_job_execution_environments", "Default execution environments for jobs; list — use vars.yml", None),
    *section("Repository / subscription"),
    ("rpm_from_single_repo", "Install all components from ansible-automation-platform repo only", "false"),
    ("redhat_rhsm_repos", "Additional RHSM repos to enable; list — use vars.yml", None),
    ("registry_url", "Container registry URL for execution environment images", "registry.redhat.io"),
    ("registry_verify_ssl", "Verify TLS when pulling from container registry", "true"),
]

EXTRA_CATALOG_LEGACY = [
    *section("SSO (2.4 only)"),
    ("sso_host", "Hostname for external RH SSO (when not installing [sso] group)", ""),
    ("sso_redirect_host", "Host var on [sso]: URL clients use to reach SSO", "sso.example.org"),
    ("sso_use_https", "Serve managed SSO over HTTPS", "true"),
    ("sso_keystore_file_remote", "SSO keystore file is on the remote SSO host", "false"),
    ("sso_console_admin_username", "RH SSO console admin username", "admin"),
    *section("PostgreSQL (managed, 2.4)"),
    ("postgres_username", "Managed PostgreSQL superuser for local [database] installs", "awx"),
    ("postgres_database", "Managed PostgreSQL database name", "awx"),
    ("install_pg_port", "TCP port for installer-managed PostgreSQL", "5432"),
    ("receptor_listener_port", "Receptor mesh listener port", "27199"),
]

EXTRA_CATALOG_GATEWAY = [
    *section("Automation Gateway (2.5+)"),
    ("automationgateway_admin_username", "Gateway admin username", "admin"),
    ("automationgateway_admin_email", "Gateway admin email", "admin@example.com"),
    ("automationgateway_disable_https", "Serve Gateway over HTTP only", "false"),
    ("automationgateway_disable_hsts", "Disable HSTS on Gateway nginx", "false"),
    ("automationgateway_tls_files_remote", "Gateway TLS cert/key files are on the remote host", "false"),
    ("automationgateway_user_headers", "Custom Gateway nginx headers; list — use vars.yml", None),
    ("automationgateway_pg_port", "Gateway PostgreSQL port", "5432"),
    ("automationgateway_pg_sslmode", "Gateway PostgreSQL sslmode", "prefer"),
    ("automationgateway_redis_host", "Redis hostname for Gateway (default: first gateway host)", "gateway1.example.org"),
    ("automationgateway_http_port", "Gateway nginx HTTP port", "8080"),
    ("automationgateway_https_port", "Gateway nginx HTTPS port", "8443"),
    ("client_request_timeout", "End-user HTTP request timeout in seconds (minimum 10)", "30"),
    *section("Redis cluster (2.5+)"),
    ("redis_cluster_ip", "Bind IP for Redis cluster nodes", "10.0.0.1"),
    ("redis_tls_cert", "Redis server TLS certificate path", "/path/to/redis.crt"),
    ("redis_tls_key", "Redis server TLS private key path", "/path/to/redis.key"),
    ("redis_tls_files_remote", "Redis TLS files are on remote hosts", "false"),
    *section("PostgreSQL connection (optional)"),
    ("pg_port", "Controller PostgreSQL port", "5432"),
    ("pg_sslmode", "Controller PostgreSQL sslmode", "prefer"),
    ("automationhub_pg_port", "Hub PostgreSQL port", "5432"),
    ("automationhub_pg_sslmode", "Hub PostgreSQL sslmode", "prefer"),
    ("automationedacontroller_pg_port", "EDA PostgreSQL port", "5432"),
    ("automationedacontroller_pg_sslmode", "EDA PostgreSQL sslmode", "prefer"),
]

EXTRA_CATALOG_TAIL = [
    *section("Insights / misc"),
    ("ignore_preflight_errors", "Continue install when preflight checks report warnings", "false"),
    ("component_firewall_type", "Firewall integration: none, firewalld, or iptables", "none"),
    ("nginx_user_http_config", "Extra nginx http block directives; list — use vars.yml", None),
]


def catalog_for(cfg: RpmVersionConfig) -> list[tuple[str, str, str | None]]:
    parts = list(EXTRA_CATALOG) + list(EXTRA_CATALOG_TAIL)
    if cfg.profile == "legacy":
        parts = list(EXTRA_CATALOG) + EXTRA_CATALOG_LEGACY + list(EXTRA_CATALOG_TAIL)
    else:
        parts = list(EXTRA_CATALOG) + EXTRA_CATALOG_GATEWAY + list(EXTRA_CATALOG_TAIL)
    localized: list[tuple[str, str, str | None]] = []
    for name, comment, example in parts:
        if example == "__EE_IMAGE_BASE__":
            example = cfg.ee_image_base
        localized.append((name, comment, example))
    return localized

# Variables already documented in the upstream inventory template (enabled or commented inline)
UPSTREAM_INVENTORY_VARS = {
    "install_pg_port",
    "ee_from_hub_only",
    "ee_29_enabled",
    "automationhub_force_change_admin_password",
    "automationhub_main_url",
    "automationhub_require_content_approval",
    "automationhub_importer_settings",
    "automationhub_disable_https",
    "automationhub_disable_hsts",
    "automationhub_create_default_collection_signing_service",
    "automationhub_create_default_container_signing_service",
    "automationhub_collection_signing_service_key",
    "automationhub_collection_signing_service_script",
    "automationhub_container_signing_service_key",
    "automationhub_container_signing_service_script",
    "automationhub_auto_sign_collections",
    "automationhub_api_token",
    "generate_automationhub_token",
    "automationhub_authentication_backend",
    "automationhub_ldap_server_uri",
    "automationhub_ldap_bind_dn",
    "automationhub_ldap_bind_password",
    "automationhub_ldap_user_search_base_dn",
    "automationhub_ldap_group_search_base_dn",
    "automationhub_seed_collections",
    "automationedacontroller_ssl_cert",
    "automationedacontroller_ssl_key",
    "automation_controller_main_url",
    "automationedacontroller_controller_verify_ssl",
    "custom_ca_cert",
    "web_server_ssl_cert",
    "web_server_ssl_key",
    "automationhub_ssl_cert",
    "automationhub_ssl_key",
    "postgres_use_ssl",
    "postgres_ssl_cert",
    "postgres_ssl_key",
    "sso_custom_keystore_file",
    "sso_host",
    "enable_insights_collection",
}

# Enabled [all:vars] lines for 2.4 — verification reference only; generation reads upstream dump.
ENABLED_ALL_VARS = [
    "admin_password=''",
    "pg_host=''",
    "pg_port=5432",
    "pg_database='awx'",
    "pg_username='awx'",
    "pg_password=''",
    "pg_sslmode='prefer'  # set to 'verify-full' for client-side enforced SSL",
    "registry_url='registry.redhat.io'",
    "registry_username=''",
    "registry_password=''",
    "receptor_listener_port=27199",
    "automationhub_admin_password=''",
    "automationhub_pg_host=''",
    "automationhub_pg_port=5432",
    "automationhub_pg_database='automationhub'",
    "automationhub_pg_username='automationhub'",
    "automationhub_pg_password=''",
    "automationhub_pg_sslmode='prefer'",
    "automationedacontroller_admin_password=''",
    "automationedacontroller_pg_host=''",
    "automationedacontroller_pg_port=5432",
    "automationedacontroller_pg_database='automationedacontroller'",
    "automationedacontroller_pg_username='automationedacontroller'",
    "automationedacontroller_pg_password=''",
    "automationedacontroller_pg_sslmode='prefer'",
    "sso_keystore_password=''",
    "sso_console_admin_password=''",
]

# Legacy 2.4 optional blocks are read from the installer dump at generation time (see extract_all_vars_body).

_DICT_VARS = {"automationhub_importer_settings", "ldap_extra_settings"}
_LIST_VARS = {
    "nginx_tls_protocols",
    "nginx_user_headers",
    "automationhub_user_headers",
    "automationgateway_user_headers",
    "automationedacontroller_user_headers",
    "automationedacontroller_allowed_hostnames",
    "automationedacontroller_trusted_origins",
    "automationedacontroller_safe_plugins",
    "aap_service_san_records",
    "extra_images",
    "ee_images",
    "de_images",
    "decision_environments",
    "global_job_execution_environments",
    "redhat_rhsm_repos",
    "nginx_user_http_config",
}


def render_extra_catalog(cfg: RpmVersionConfig, skip: set[str]) -> list[str]:
    lines: list[str] = [
        "",
        "# Additional optional variables from installer role defaults",
        "# (not in the upstream inventory template). Complex types: vars-example.yml",
        "# -----------------------------------------------------",
    ]
    for name, comment, example in catalog_for(cfg):
        if name == "__SECTION__":
            lines.extend(["", f"# {comment}", "# -----------------------------------------------------"])
            continue
        if name in skip:
            continue
        if example is None:
            lines.append(f"# {name}=  # {comment}; see vars-example.yml")
        elif example == "":
            lines.append(f"# {name}=  # {comment}")
        else:
            lines.append(f"# {name}={example}  # {comment}")
    return lines


def _yaml_example_body(name: str, cfg: RpmVersionConfig) -> list[str]:
    if name == "automationhub_importer_settings":
        return ["# automationhub_importer_settings:", "#   ansible_test_local_image: false"]
    if name == "ldap_extra_settings":
        return ["# ldap_extra_settings:", "#   AUTH_LDAP_USER_FLAGS_BY_GROUP: {}"]
    if name == "decision_environments":
        return [
            "# decision_environments:",
            "#   - name: my-de",
            "#     image: registry.example.org/my-de:latest",
        ]
    if name in {"extra_images", "ee_images", "de_images"}:
        return [
            f"# {name}:",
            "#   - name: my-custom-ee",
            "#     image: registry.example.org/my-ee:latest",
        ]
    if name == "global_job_execution_environments":
        return [
            "# global_job_execution_environments:",
            "#   - name: Default execution environment",
            f"#     image: {cfg.ee_image_base}ee-supported-rhel8:latest",
        ]
    if name == "redhat_rhsm_repos":
        return ["# redhat_rhsm_repos:", "#   - ansible-automation-platform"]
    if name in _LIST_VARS:
        return [f"# {name}:", "#   - example-entry"]
    return [f"# {name}: {{}}"]


def build_vars_example(cfg: RpmVersionConfig) -> str:
    lines = [
        "---",
        f"# AAP {cfg.version} RPM installer optional variables — YAML-only (lists and dictionaries)",
        "#",
        "# Copy to vars.yml and pass: ./setup.sh -e @vars.yml",
        f"# Regenerate: python3 scripts/build_rpm_inventory.py --version {cfg.version}",
        "",
    ]
    skip_upstream = set(UPSTREAM_INVENTORY_VARS)
    if cfg.profile == "gateway":
        skip_upstream |= enabled_var_names(installer_inventory_path(cfg).read_text(encoding="utf-8"))
    for name, comment, example in catalog_for(cfg):
        if name == "__SECTION__":
            lines.extend(["", f"# {comment}", "# -----------------------------------------------------"])
            continue
        if name in skip_upstream and name not in _DICT_VARS and name not in _LIST_VARS:
            continue
        if example is not None and name not in _DICT_VARS and name not in _LIST_VARS:
            continue
        if name == "node_type":
            continue
        lines.append("")
        lines.append(f"# {comment}")
        lines.extend(_yaml_example_body(name, cfg))
    lines.append("")
    return "\n".join(lines)


def normalize_inventory_values(text: str) -> str:
    """Normalize Python-style literals in inventory text to Ansible conventions."""
    out: list[str] = []
    for line in text.splitlines():
        if "=" in line:
            line = re.sub(r"\bTrue\b", "true", line)
            line = re.sub(r"\bFalse\b", "false", line)
            line = re.sub(r"=\s*None\b", "=", line)
        else:
            line = (
                line.replace("Set to True", "Set to true")
                .replace("Set to False", "Set to false")
                .replace("set to True", "set to true")
                .replace("set to False", "set to false")
                .replace(" to True", " to true")
                .replace(" to False", " to false")
                .replace("True by default", "true by default")
            )
        out.append(line)
    return "\n".join(out)


def extract_all_vars_body(text: str) -> str:
    lines = text.splitlines()
    in_all = False
    body: list[str] = []
    for line in lines:
        if line.strip() == "[all:vars]":
            in_all = True
            continue
        if in_all:
            body.append(line)
    return normalize_inventory_values("\n".join(body))


def strip_upstream_preamble(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("# This section is for") or s == "[automationgateway]":
            return "\n".join(lines[i:])
    return text


def reference_header(cfg: RpmVersionConfig, installer_name: str) -> list[str]:
    return [
        f"# AAP {cfg.version} RPM installer inventory reference",
        f"# Enabled lines below match the upstream {installer_name}/inventory.",
        "# All other supported variables are listed commented out for reference.",
        f"# Install guide: {cfg.doc_base}",
        "",
    ]


def build_inventory_gateway(cfg: RpmVersionConfig) -> str:
    inv_path = installer_inventory_path(cfg)
    upstream = inv_path.read_text(encoding="utf-8")
    body = strip_upstream_preamble(upstream)
    skip = UPSTREAM_INVENTORY_VARS | enabled_var_names(body)
    parts = reference_header(cfg, inv_path.parent.name) + [body] + render_extra_catalog(cfg, skip)
    return "\n".join(parts) + "\n"


def build_inventory_legacy(cfg: RpmVersionConfig) -> str:
    inv_path = installer_inventory_path(cfg)
    upstream = inv_path.read_text(encoding="utf-8")
    all_vars_body = extract_all_vars_body(upstream)
    header = reference_header(cfg, inv_path.parent.name) + [
        "# Automation Controller Nodes",
        "# There are two valid node_types that can be assigned for this group.",
        "# A node_type=control implies that the node will only be able to run",
        "# project and inventory updates, but not regular jobs.",
        "# A node_type=hybrid will have the ability to run everything.",
        "# If you do not define the node_type, it defaults to hybrid.",
        "#",
        "# control.example node_type=control",
        "# hybrid.example  node_type=hybrid",
        "# hybrid2.example <- this will default to hybrid",
        "[automationcontroller]",
        "controller1.example.org",
        "controller2.example.org",
        "",
        "[automationcontroller:vars]",
        "peers=execution_nodes",
        "",
        "# Execution Nodes",
        "# There are two valid node_types that can be assigned for this group.",
        "# A node_type=hop implies that the node will forward jobs to an execution node.",
        "# A node_type=execution implies that the node will be able to run jobs.",
        "# If you do not define the node_type, it defaults to execution.",
        "#",
        "# hop.example        node_type=hop",
        "# execution.example  node_type=execution",
        "# execution2.example <- this will default to execution",
        "[execution_nodes]",
        "hop1.example.org node_type=hop",
        "exec1.example.org",
        "exec2.example.org",
        "",
        "[automationhub]",
        "hub1.example.org",
        "hub2.example.org",
        "",
        "[automationedacontroller]",
        "eda1.example.org",
        "eda2.example.org",
        "",
        "[database]",
        "",
        "# Single Sign-On",
        "# If sso_redirect_host is set, that will be used for application to connect to",
        "# SSO for authentication. This must be reachable from client machines.",
        "#",
        "# ssohost.example sso_redirect_host=<host/ip>",
        "[sso]",
        "sso1.example.org",
        "sso2.example.org",
        "",
        "[all:vars]",
    ]
    skip = UPSTREAM_INVENTORY_VARS | enabled_var_names(f"[all:vars]\n{all_vars_body}")
    parts = header + [all_vars_body] + render_extra_catalog(cfg, skip)
    return "\n".join(parts) + "\n"


def build_inventory(cfg: RpmVersionConfig) -> str:
    if cfg.profile == "gateway":
        return build_inventory_gateway(cfg)
    return build_inventory_legacy(cfg)


def generate_version(cfg: RpmVersionConfig) -> None:
    out_dir = cfg.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "inventory-example").write_text(build_inventory(cfg), encoding="utf-8")
    (out_dir / "vars-example.yml").write_text(build_vars_example(cfg), encoding="utf-8")
    print(f"Wrote {out_dir / 'inventory-example'}")
    print(f"Wrote {out_dir / 'vars-example.yml'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate annotated RPM installer inventories.")
    parser.add_argument(
        "--version",
        choices=sorted(VERSIONS),
        action="append",
        help="AAP version to generate (repeatable). Defaults to all supported versions.",
    )
    args = parser.parse_args()
    versions = args.version or sorted(VERSIONS)
    for version in versions:
        generate_version(VERSIONS[version])


if __name__ == "__main__":
    main()
