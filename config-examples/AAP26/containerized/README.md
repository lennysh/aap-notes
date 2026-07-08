# AAP 2.6 — Containerized Installer Inventory Reference

Reference Ansible inventories for the **AAP 2.6 containerized installer** (`ansible-automation-platform-containerized-setup-2.6-*`).

For OpenShift operator manifests, see [AAP 2.6 on OpenShift](../openshift/README.md). For maintenance when adding versions or refreshing after installer updates, see [CONTAINERIZED_INVENTORY_CONTEXT.md](../../CONTAINERIZED_INVENTORY_CONTEXT.md).

## Files

| File | Upstream equivalent | Topology |
|------|---------------------|----------|
| [inventory-example](inventory-example) | `inventory` | Enterprise — separate hosts, external PostgreSQL, Redis cluster |
| [inventory-growth-example](inventory-growth-example) | `inventory-growth` | Container growth — single host, managed `[database]`, `redis_mode=standalone` |
| [vars-example.yml](vars-example.yml) | — | YAML-only options (lists/dicts); all commented; use with `-e @vars.yml` |

## Enabled settings (unchanged from upstream)

### Enterprise (`inventory-example`)

**Host groups:** `automationgateway`, `automationcontroller`, `execution_nodes`, `automationhub`, `automationeda`, `redis`

**Required `[all:vars]`:** registry credentials, PostgreSQL admin credentials, and per-component admin passwords with external DB connection settings (`*_pg_host`, `*_pg_database`, `*_pg_username`, `*_pg_password`).

### Growth (`inventory-growth-example`)

**Host groups:** `automationgateway`, `automationcontroller`, `automationhub`, `automationeda`, `database`

**Required `[all:vars]`:** `ansible_connection=local`, `redis_mode=standalone`, `controller_percent_memory_capacity=0.5`, `hub_seed_collections=false`, plus admin/registry credentials with `*_pg_host` pointing at the local host.

## Optional host groups (commented in both files)

Uncomment and populate when deploying these components:

| Group | Component | Notes |
|-------|-----------|-------|
| `[ansiblelightspeed]` | Ansible Lightspeed | Experimental; see Lightspeed section at bottom of inventory |
| `[ansiblemcp]` | Ansible MCP Server | Requires Gateway |
| `[automationmetrics]` | Automation Metrics Service | AAP 2.6+; requires `[automationgateway]` and metrics DB vars |

Enterprise-only: `[redis]` (enabled), `[execution_nodes]` (enabled)

Growth-only: `[database]` (enabled)

## Host-level variables

Set on the host line (not under `[all:vars]`):

| Variable | Groups | Values | Purpose |
|----------|--------|--------|---------|
| `receptor_type` | `execution_nodes` | `hop`, `execution` | Hop vs execution node (see starter `hop1.example.org receptor_type='hop'`) |
| `receptor_type` | `automationcontroller` | `control`, `hybrid` | Controller Receptor role when non-default |
| `receptor_protocol` | `automationcontroller`, `execution_nodes` | `tcp`, `udp` | Receptor mesh protocol |
| `eda_type` | `automationeda` | `hybrid`, `api`, `worker`, `event-stream` | EDA node role for scaled deployments |

## Commented optional variables

Below the enabled `[all:vars]` block, variables are grouped roughly as in the upstream installer README:

- Common / installer-wide (registry, TLS CA, offline bundle, feature flags)
  - `ca_tls_cert` / `ca_tls_key` — AAP internal signing CA; `custom_ca_cert` — org CA for trusting external HTTPS (e.g. CyberArk, corporate APIs/DBs)
- Host tuning (`tune_host_limits`, sysctl/ulimit overrides)
- Container image tags
- PostgreSQL, Redis, Receptor
- Performance Co-Pilot (`setup_monitoring`)
- Per-component settings (Gateway, Controller, Hub, EDA, Lightspeed, MCP, Metrics)
- Log gathering (for `ansible.containerized_installer.log_gathering`, not install)

List and dictionary variables (for example `controller_extra_settings`, `feature_flags`, `hub_s3_extra_settings`) do not work well in INI inventory syntax. They are documented as placeholders in the inventory files and fully exemplified in **[vars-example.yml](vars-example.yml)** — every YAML-only variable, commented out with example structure.

```bash
cp vars-example.yml vars.yml
# edit vars.yml — uncomment and customize what you need
ansible-playbook -i inventory-example ansible.containerized_installer.install -e @vars.yml
```

Example (from `vars-example.yml` after uncommenting):

```yaml
controller_extra_settings:
  - setting: USE_X_FORWARDED_HOST
    value: true
```

## Regenerate from catalog

```bash
cd /path/to/aap-notes/config-examples
python3 scripts/build-inventory-2.6.py
```

Variable definitions live in [`scripts/build-inventory-2.6.py`](../../scripts/build-inventory-2.6.py). When Red Hat ships a new 2.6 installer refresh, diff the upstream README and role defaults against that catalog, then regenerate. See [CONTAINERIZED_INVENTORY_CONTEXT.md](../../CONTAINERIZED_INVENTORY_CONTEXT.md) for the full workflow.
