# AAP 2.6 — RPM Installer Inventory Reference

Reference Ansible inventory for the **AAP 2.6 RPM installer** (`ansible-automation-platform-setup-2.6-*`, run via `setup.sh`).

Verified against installer dump: `ansible-automation-platform-setup-2.6-7`.

For OpenShift operator manifests, see [AAP 2.6 on OpenShift](../../openshift/AAP26/README.md). For containerized deployment, see [AAP 2.6 containerized inventories](../containerized/README.md). For maintenance when refreshing after installer updates, see [RPM_INVENTORY_CONTEXT.md](../../maintainer/RPM_INVENTORY_CONTEXT.md).

## Files

| File | Upstream equivalent | Purpose |
|------|---------------------|---------|
| [inventory-example](inventory-example) | `inventory` | Annotated inventory with example hosts and all installer variables |
| [vars-example.yml](vars-example.yml) | — | YAML-only options (lists/dicts); use with `./setup.sh -e @vars.yml` |
| [install-playbook-tasks.md](install-playbook-tasks.md) | `playbooks/install.yml` | Install playbook tasks in execution order (recursive role expansion) |

Unlike the containerized installer, the RPM installer ships a **single** `inventory` template (no growth topology).

## Enabled settings (unchanged from upstream)

**Host groups:** `automationgateway`, `automationcontroller`, `execution_nodes`, `automationhub`, `automationedacontroller`, `redis`

**Group vars:** `[automationcontroller:vars]` sets `peers=execution_nodes`

**Required `[all:vars]`:** registry credentials plus per-component admin passwords and external PostgreSQL connection settings (`*_pg_host`, `*_pg_database`, `*_pg_username`, `*_pg_password`). Fill these in before running `setup.sh`.

Example hosts match the upstream template.

## Host-level variables

Set on the host line (not under `[all:vars]`):

| Variable | Groups | Values | Purpose |
|----------|--------|--------|---------|
| `node_type` | `execution_nodes` | `hop`, `execution` | Hop vs execution node (default: execution) |

## Quick start

```bash
cp inventory-example /path/to/my-inventory
# edit placeholders; optionally: cp vars-example.yml vars.yml
cd /path/to/ansible-automation-platform-setup-2.6-*/
./setup.sh -i /path/to/my-inventory
# or with extra vars:
./setup.sh -i /path/to/my-inventory -e @/path/to/vars.yml
```

## Regenerate from catalog

```bash
cd /path/to/aap-notes/installer
python3 scripts/build_rpm_inventory.py --version 2.6
```

Variable definitions live in [`scripts/build_rpm_inventory.py`](../../scripts/build_rpm_inventory.py).

## Documentation

- [AAP 2.6 RPM installation guide](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/rpm_installation)
