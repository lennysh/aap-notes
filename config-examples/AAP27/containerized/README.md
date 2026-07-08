# AAP 2.7 — Containerized Installer Inventory Reference

Reference Ansible inventories for the **AAP 2.7 containerized installer** (`ansible-automation-platform-containerized-setup-2.7-*`).

Verified against installer dump: `ansible-automation-platform-containerized-setup-2.7-2`.

For OpenShift operator manifests, see [AAP 2.7 on OpenShift](../openshift/README.md). For the shared platform model and optional-variable catalog, see [AAP 2.6 containerized README](../AAP26/containerized/README.md). For maintenance when refreshing after installer updates, see [CONTAINERIZED_INVENTORY_CONTEXT.md](../../CONTAINERIZED_INVENTORY_CONTEXT.md).

## Files

| File | Upstream equivalent | Topology |
|------|---------------------|----------|
| [inventory-example](inventory-example) | `inventory` | Enterprise — external PostgreSQL, Redis cluster, **Automation Metrics** |
| [inventory-growth-example](inventory-growth-example) | `inventory-growth` | Container growth — single host, managed `[database]`, metrics on same host |
| [vars-example.yml](vars-example.yml) | — | YAML-only options (lists/dicts); all commented; use with `-e @vars.yml` |

## Enabled settings (unchanged from upstream)

### Enterprise (`inventory-example`)

**Host groups:** `automationgateway`, `automationcontroller`, `execution_nodes`, `automationhub`, `automationeda`, **`automationmetrics`**, `redis`

**Required `[all:vars]`:** same component DB/admin/registry settings as 2.5/2.6, plus:

- `automationmetrics_pg_host`, `automationmetrics_pg_database`, `automationmetrics_pg_username`, `automationmetrics_pg_password`
- `automationmetrics_controller_read_pg_host`, `automationmetrics_controller_read_pg_password`

When `[automationcontroller]` is present, **Automation Metrics Service is required** unless you set `automationmetrics_skip_install=true` (documented in optional variables).

### Growth (`inventory-growth-example`)

**Host groups:** `automationgateway`, `automationcontroller`, `automationhub`, `automationeda`, **`automationmetrics`**, `database`

**Required `[all:vars]`:** growth defaults from 2.5/2.6, plus `automationmetrics_pg_host`, `automationmetrics_pg_password`, `automationmetrics_controller_read_pg_host`, and `automationmetrics_controller_read_pg_password`.

## Version notes (2.7 vs 2.6)

- **`[automationmetrics]`** is enabled in both starter inventories (not optional).
- **EDA external Redis variables** (`eda_redis_*`) are removed; EDA uses PostgreSQL/dispatcherd.
- New **EDA event stream / event persistence** database variables (`eda_event_stream_pg_*`, `eda_event_persistence_*`) appear in optional variables.
- New **Lightspeed** timeout and BYOK variables (`lightspeed_streaming_timeout`, `lightspeed_chatbot_byok_image`, etc.).
- **`automationmetrics_skip_install`** — opt out of metrics when Controller is deployed.

## Regenerate from catalog

```bash
cd /path/to/aap-notes/config-examples
python3 scripts/build_inventory.py --version 2.7
```

Variable definitions live in [`scripts/build_inventory.py`](../../scripts/build_inventory.py). See [CONTAINERIZED_INVENTORY_CONTEXT.md](../../CONTAINERIZED_INVENTORY_CONTEXT.md) for the full workflow.

## Documentation

- [AAP 2.7 containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation)
- [Inventory variables appendix (2.7)](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation/appendix-inventory-files-vars)
