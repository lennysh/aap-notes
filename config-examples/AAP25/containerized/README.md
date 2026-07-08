# AAP 2.5 — Containerized Installer Inventory Reference

Reference Ansible inventories for the **AAP 2.5 containerized installer** (`ansible-automation-platform-containerized-setup-2.5-*`).

Verified against installer dump: `ansible-automation-platform-containerized-setup-2.5-25`.

For OpenShift operator manifests, see [AAP 2.5 on OpenShift](../openshift/README.md). For maintenance when refreshing after installer updates, see [CONTAINERIZED_INVENTORY_CONTEXT.md](../../CONTAINERIZED_INVENTORY_CONTEXT.md).

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

## Version notes (2.5 vs 2.6+)

- No **Ansible MCP Server** or **Automation Metrics Service** variables in the 2.5 installer catalog.
- Optional `[ansiblelightspeed]` host group is documented but commented out (same as upstream).

## Optional host groups (commented in both files)

| Group | Component | Notes |
|-------|-----------|-------|
| `[ansiblelightspeed]` | Ansible Lightspeed | Experimental; see Lightspeed section at bottom of inventory |

Enterprise-only: `[redis]` (enabled), `[execution_nodes]` (enabled)

Growth-only: `[database]` (enabled)

## Host-level variables

Set on the host line (not under `[all:vars]`):

| Variable | Groups | Values | Purpose |
|----------|--------|--------|---------|
| `receptor_type` | `execution_nodes` | `hop`, `execution` | Hop vs execution node |
| `receptor_type` | `automationcontroller` | `control`, `hybrid` | Controller Receptor role when non-default |
| `receptor_protocol` | `automationcontroller`, `execution_nodes` | `tcp`, `udp` | Receptor mesh protocol |
| `eda_type` | `automationeda` | `hybrid`, `api`, `worker`, `event-stream` | EDA node role for scaled deployments |

## Regenerate from catalog

```bash
cd /path/to/aap-notes/config-examples
python3 scripts/build_inventory.py --version 2.5
```

Variable definitions live in [`scripts/build_inventory.py`](../../scripts/build_inventory.py). See [CONTAINERIZED_INVENTORY_CONTEXT.md](../../CONTAINERIZED_INVENTORY_CONTEXT.md) for the full workflow.

## Documentation

- [AAP 2.5 containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/containerized_installation)
- [Inventory variables appendix (2.5)](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/containerized_installation/appendix-inventory-files-vars)
