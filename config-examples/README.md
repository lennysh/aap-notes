# AAP Config Examples

Reference configuration for deploying [Ansible Automation Platform (AAP)](https://www.redhat.com/en/technologies/management/ansible). These are **not production-ready templates** — replace placeholder values, trim options you do not need, and validate against your environment before use.

Examples are grouped by **AAP version** and **deployment method**:

| Method | What you get | Local tooling (gitignored) |
|--------|--------------|----------------------------|
| **OpenShift** | Kubernetes manifests (CRs + secrets) for the AAP Operator | `.crd-dumps/<version>/` |
| **RPM** | Annotated Ansible inventory for the RPM installer (`setup.sh`) | `.installer-dumps/` |
| **Containerized** | Annotated Ansible inventories for the containerized installer | `.installer-dumps/` |

## Repository layout

```
config-examples/
├── README.md
├── CONTAINERIZED_INVENTORY_CONTEXT.md   # maintenance guide for containerized inventories
├── RPM_INVENTORY_CONTEXT.md             # maintenance guide for RPM inventories
├── .crd-dumps/                          # OpenShift operator CRD dumps (local)
├── .installer-dumps/                  # installer tarballs — RPM and containerized (local)
│   ├── 2.4/ansible-automation-platform-setup-2.4-*/
│   ├── 2.5/ansible-automation-platform-setup-2.5-*/   # RPM
│   ├── 2.5/ansible-automation-platform-containerized-setup-2.5-*/
│   ├── 2.6/ansible-automation-platform-setup-2.6-*/   # RPM
│   ├── 2.6/ansible-automation-platform-containerized-setup-2.6-*/
│   └── 2.7/ansible-automation-platform-containerized-setup-2.7-*/
├── scripts/
│   ├── build_inventory.py             # containerized generator (2.5–2.7)
│   ├── build_rpm_inventory.py         # RPM generator (2.4–2.6)
│   ├── build-inventory-2.5.py         # containerized thin wrapper
│   ├── build-inventory-2.6.py
│   ├── build-inventory-2.7.py
│   ├── build-rpm-inventory-2.4.py     # RPM thin wrapper
│   ├── build-rpm-inventory-2.5.py
│   └── build-rpm-inventory-2.6.py
├── AAP24/
│   ├── openshift/
│   └── rpm/
├── AAP25/
│   ├── openshift/
│   ├── containerized/
│   └── rpm/
├── AAP26/
│   ├── openshift/
│   ├── containerized/
│   └── rpm/
└── AAP27/
    ├── openshift/
    └── containerized/                 # no RPM installer for 2.7
```

Containerized inventories for 2.5, 2.6, and 2.7 use `scripts/build_inventory.py`. RPM inventories for 2.4, 2.5, and 2.6 use `scripts/build_rpm_inventory.py`. **AAP 2.7 has no RPM installer** — use containerized or OpenShift only.

## OpenShift operator examples

Kubernetes manifests for the Red Hat AAP Operator on OpenShift. Secrets are kept in separate YAML files from Custom Resources.

| Folder | AAP version | Deployment model | Docs |
|--------|-------------|------------------|------|
| [`AAP24/openshift/`](AAP24/openshift/) | 2.4 | Component CRs (`AutomationController`, `AutomationHub`, `EDA`) | [README](AAP24/openshift/README.md) |
| [`AAP25/openshift/`](AAP25/openshift/) | 2.5 | Platform CR (`AnsibleAutomationPlatform`) | [README](AAP25/openshift/README.md) |
| [`AAP26/openshift/`](AAP26/openshift/) | 2.6 | Platform CR | [README](AAP26/openshift/README.md) |
| [`AAP27/openshift/`](AAP27/openshift/) | 2.7 | Platform CR | [README](AAP27/openshift/README.md) |

All OpenShift examples target the `aap` namespace. Create it (or change `namespace` everywhere) before deploying. Do **not** deploy AAP into the `default` namespace.

### AAP 2.4 vs 2.5+ (OpenShift)

**AAP 2.4** uses one Custom Resource per component. Apply component secret manifests, then `controller.yml`, `hub.yml`, and `eda.yml`. See [AAP24/openshift/README.md](AAP24/openshift/README.md) for the full secret catalog.

**AAP 2.5 and later** use a single **`AnsibleAutomationPlatform`** CR with nested `spec.controller`, `spec.hub`, and `spec.eda` blocks. Apply `secrets-aap.yml`, then `aap.yml`. The [AAP 2.5 README](AAP25/openshift/README.md) is the primary reference; 2.6 and 2.7 READMEs call out version-specific deltas.

### Regenerating OpenShift examples

CR example YAML is generated from operator CRD dumps using [generate-aap-cr-examples](https://github.com/lennysh/openshift-playground/tree/devel/generate-aap-cr-examples) in **openshift-playground**. Each version README includes the exact command and output path.

## RPM installer examples (2.4–2.6)

Annotated inventory for the **RPM installer** (`ansible.automation_platform_installer`, run via `setup.sh`). **Enabled `[all:vars]` lines match the upstream `inventory` template**; example hosts and additional optional variables are added for reference.

**AAP 2.7 has no RPM installer** — use [containerized](#containerized-installer-examples) or [OpenShift](#openshift-operator-examples) examples instead.

| Folder | AAP version | Installer dump | Profile | Docs |
|--------|-------------|----------------|---------|------|
| [`AAP24/rpm/`](AAP24/rpm/) | 2.4 | `setup-2.4-16` | Legacy (SSO, `[database]`) | [README](AAP24/rpm/README.md) |
| [`AAP25/rpm/`](AAP25/rpm/) | 2.5 | `setup-2.5-23` | Gateway (`[automationgateway]`, `[redis]`) | [README](AAP25/rpm/README.md) |
| [`AAP26/rpm/`](AAP26/rpm/) | 2.6 | `setup-2.6-7` | Gateway | [README](AAP26/rpm/README.md) |

| File | Upstream equivalent | Purpose |
|------|---------------------|---------|
| `inventory-example` | `inventory` | Single topology — external PostgreSQL |
| `vars-example.yml` | — | YAML-only options; use with `./setup.sh -e @vars.yml` |

### Quick start (RPM)

```bash
cp AAP26/rpm/inventory-example /path/to/my-inventory
cd /path/to/ansible-automation-platform-setup-2.6-*/
./setup.sh -i /path/to/my-inventory
```

Use `AAP24/rpm/` or `AAP25/rpm/` for those versions.

### Regenerating RPM inventories

```bash
cd /path/to/aap-notes/config-examples
python3 scripts/build_rpm_inventory.py              # all versions (2.4–2.6)
python3 scripts/build_rpm_inventory.py --version 2.5  # one version
```

See [RPM_INVENTORY_CONTEXT.md](RPM_INVENTORY_CONTEXT.md) for the maintenance workflow.

## Containerized installer examples

Annotated Ansible inventory files for the **containerized installer** (`ansible.containerized_installer`). **Enabled lines match the upstream starter inventories**; every other supported variable is listed commented out with a short explanation.

| Folder | AAP version | Installer dump | Docs |
|--------|-------------|----------------|------|
| [`AAP25/containerized/`](AAP25/containerized/) | 2.5 | `2.5-25` | [README](AAP25/containerized/README.md) |
| [`AAP26/containerized/`](AAP26/containerized/) | 2.6 | `2.6-10` | [README](AAP26/containerized/README.md) |
| [`AAP27/containerized/`](AAP27/containerized/) | 2.7 | `2.7-2` | [README](AAP27/containerized/README.md) |

Each version directory includes:

| File | Upstream equivalent | Topology |
|------|---------------------|----------|
| `inventory-example` | `inventory` | Enterprise — external PostgreSQL, Redis cluster |
| `inventory-growth-example` | `inventory-growth` | Container growth — single host, managed database |
| `vars-example.yml` | — | YAML-only options (lists/dicts); use with `-e @vars.yml` |

### Quick start

```bash
cp AAP26/containerized/inventory-example /path/to/my-inventory
# edit placeholders; optionally: cp vars-example.yml vars.yml and pass -e @vars.yml
ansible-playbook -i /path/to/my-inventory ansible.containerized_installer.install
```

Use `AAP25/containerized/` or `AAP27/containerized/` for those versions.

### Regenerating containerized inventories

```bash
cd /path/to/aap-notes/config-examples
python3 scripts/build_inventory.py              # all versions
python3 scripts/build_inventory.py --version 2.7  # one version
```

See [CONTAINERIZED_INVENTORY_CONTEXT.md](CONTAINERIZED_INVENTORY_CONTEXT.md) for the full maintenance workflow when adding a new AAP version or refreshing after a Red Hat installer update.

Place extracted installers under `.installer-dumps/` (gitignored). This repo does not redistribute Red Hat software.

## Using with Cursor / other agents

`@`-mention the folder that matches your deployment method and AAP version:

- **OpenShift 2.4** — `config-examples/AAP24/openshift/`
- **RPM 2.4–2.6** — `config-examples/AAP24/rpm/`, `AAP25/rpm/`, or `AAP26/rpm/` (or `config-examples/RPM_INVENTORY_CONTEXT.md` when refreshing). **No RPM installer for 2.7.**
- **OpenShift 2.5+** — `config-examples/AAP25/openshift/` (use AAP26/AAP27 for version-specific fields)
- **Containerized** — `config-examples/AAP25/containerized/`, `AAP26/containerized/`, or `AAP27/containerized/` (or `config-examples/CONTAINERIZED_INVENTORY_CONTEXT.md` when refreshing inventories)

Pair with [`rbac/`](../rbac/) when questions span both deployment and access control.

## Constraints

- **Not production templates** — placeholder passwords, example hostnames, and commented optional blocks are intentional.
- **External Postgres (OpenShift)** — Hub requires the `hstore` extension when using an external database.
- **Operator-generated secrets (OpenShift)** — Pre-provision secrets for GitOps and migration when you need deterministic credentials.
- **Hub storage (OpenShift)** — S3 or Azure, not both.
- **Installer sources** — Keep tarballs local under `.installer-dumps/`; they are not committed.
