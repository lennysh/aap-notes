# Containerized inventory maintenance context

Use this document when adding a new AAP version (2.5, 2.7, …) or refreshing inventories after a Red Hat installer update.

## Goal

Each version directory (for example `AAP26/containerized/`) ships two inventory reference files:

1. **Enterprise** — `inventory-example`; matches upstream `inventory` enabled lines exactly.
2. **Growth** — `inventory-growth-example`; matches upstream `inventory-growth` enabled lines exactly.

All other user-configurable variables appear **commented out** with a one-line description and an example/default value where applicable.

## Directory convention

```
config-examples/
├── CONTAINERIZED_INVENTORY_CONTEXT.md
├── .installer-dumps/               # gitignored — extracted installer tarballs
│   └── ansible-automation-platform-containerized-setup-{XY}-*/
├── scripts/
│   └── build-inventory-{XY}.py     # generator for that version
└── AAP{XY}/                        # e.g. AAP25, AAP26, AAP27
    └── containerized/
        ├── inventory-example
        ├── inventory-growth-example
        ├── vars-example.yml
        └── README.md
```

OpenShift operator examples live in the sibling `AAP{XY}/openshift/` folder under the same version directory.

## Authoritative sources (check in this order)

When building or updating a version, extract the matching installer tarball to `.installer-dumps/` and review:

| Source | Path (inside extracted installer) | What to extract |
|--------|-----------------------------------|-----------------|
| Starter inventories | `inventory`, `inventory-growth` | **Enabled lines only** — must not drift |
| Variable appendix | Installer README + Red Hat docs | User-facing descriptions |
| Collection README | `collections/ansible_collections/ansible/containerized_installer/README.md` | Full variable tables (primary catalog) |
| Install playbook | `.../playbooks/install.yml` | Conditional features (`when:` vars), host groups |
| Role defaults | `.../roles/*/defaults/main.yml` | Defaults not listed in README |
| Preflight role | `.../roles/preflight/tasks/*.yml` | Validated vars, host-level constraints |
| Changelog | `.../changelogs/changelog.yaml` | New/renamed/removed variables |

### Host groups referenced by `install.yml` (2.6)

```
automationgateway
automationcontroller
execution_nodes
automationhub
automationeda
ansiblelightspeed
ansiblemcp
automationmetrics
database
redis
```

Not every topology uses every group. Comment unused groups in each reference file with a short note (as in `AAP26/containerized/inventory-example`).

### Host-level variables (not in `[all:vars]`)

| Variable | Allowed on | Values |
|----------|------------|--------|
| `receptor_type` | `execution_nodes` | `execution`, `hop` |
| `receptor_type` | `automationcontroller` | `control`, `hybrid` |
| `receptor_protocol` | `automationcontroller`, `execution_nodes` | `tcp`, `udp` |
| `eda_type` | `automationeda` | `hybrid`, `api`, `worker`, `event-stream` |

Validated in `roles/preflight/tasks/receptor.yml` and `automationeda.yml`.

### Install playbook conditionals (2.6)

Variables that gate install behavior via `when:` in `install.yml`:

| Variable | Default | Effect |
|----------|---------|--------|
| `tune_host_limits` | `true` | Host tuning role |
| `redis_mode` | `cluster` | Cluster vs standalone Redis placement |
| `setup_monitoring` | `false` | PCP installation |
| `controller_postinstall` | `false` | Controller postinstall role |
| `hub_postinstall` | `false` | Hub postinstall role |
| `hub_seed_collections` | `true` | Upload bundled collections (offline install) |
| `bundle_install` | `false` | Offline install; requires `bundle_dir` |

### Variables in code but not always in README tables

Include these if preflight or templates reference them:

- `hub_main_url` — Hub public URL (preflight)
- `gateway_pg_socket`, `controller_pg_socket`, `hub_pg_socket`, `eda_pg_socket` — unix socket DB connections
- `hub_seed_collections` — growth inventory sets `false`
- `feature_flags` — dict; keys must start with `feature_`
- `custom_ca_cert` — org CA PEM added to the platform trust bundle for outbound TLS to external services (CyberArk, corporate DBs, APIs); required for `*_pg_cert_auth` with `verify-ca`/`verify-full`; does not automatically apply to Execution Environments (see `eda_podman_mounts` for EDA decision environments)

### TLS CA variables (do not confuse)

| Variable | Purpose |
|----------|---------|
| `ca_tls_cert` / `ca_tls_key` | AAP **internal** CA used to sign component certificates (Gateway, Controller, Redis, etc.) |
| `custom_ca_cert` | **Additional external** CA to **trust** when AAP platform containers make outbound TLS connections |

### Complex types (use vars-example.yml, not INI inventory)

Generated in `AAP26/containerized/vars-example.yml` by `build_vars_example()` — one commented block per variable where `example_value is None` in the catalog:

- `*_extra_settings` (list of `{setting, value}`)
- `feature_flags`, `hub_galaxy_importer`, `hub_azure_extra_settings`, `hub_s3_extra_settings`
- `ee_extra_images`, `de_extra_images`, `receptor_peers`
- `*_nginx_https_protocols`, `*_nginx_user_headers`, `eda_safe_plugins`
- `lightspeed_chatbot_model_extra_settings`, `lightspeed_chatbot_agent_extra_settings`
- `postgresql_extra_settings`
- `hub_data_path_exclude`, `*_postinstall_ignore_files`

## Generator workflow (2.6)

1. Edit `scripts/build-inventory-2.6.py`:
   - `CATALOG`, `GATEWAY_VARS`, `CONTROLLER_VARS`, … — optional variable definitions
   - `ENTERPRISE_ENABLED` / `GROWTH_ENABLED` — vars that must stay uncommented
   - `ENTERPRISE_ENABLED_VALUES` / `GROWTH_ENABLED_VALUES` — exact upstream values
   - `ENTERPRISE_HOSTS` / `GROWTH_HOSTS` — group sections
2. Run from `config-examples/`:

   ```bash
   python3 scripts/build-inventory-2.6.py
   ```

   Writes `AAP26/containerized/inventory-example`, `inventory-growth-example`, and `vars-example.yml`.

3. Diff enabled sections against fresh upstream `inventory` / `inventory-growth`
4. Spot-check new installer README tables against catalog

## Adding a new version (checklist)

- [ ] Create `AAP{XY}/containerized/` and copy/adapt `AAP26/containerized/README.md`
- [ ] Copy `scripts/build-inventory-2.6.py` → `scripts/build-inventory-{XY}.py` and set `OUT_DIR` to `AAP{XY}/containerized`
- [ ] Update doc URLs to the correct AAP `{X.Y}` documentation paths
- [ ] Replace upstream starter paths and enabled var sets from new `inventory` files
- [ ] Diff `containerized_installer/README.md` variable tables vs prior version catalog
- [ ] Diff all `roles/*/defaults/main.yml` for new/changed keys
- [ ] Read `install.yml` for new host groups or `when:` conditionals
- [ ] Regenerate and verify enabled blocks byte-match upstream starters (except added header comments)
- [ ] Update [config-examples/README.md](README.md) version table

## AI assistant prompt template

When asking an agent to refresh inventories:

```
Refresh the AAP {X.Y} containerized inventory reference in aap-notes.

Installer extracted at: config-examples/.installer-dumps/ansible-automation-platform-containerized-setup-{X.Y}-*/

Requirements:
- Enabled lines must match upstream inventory and inventory-growth exactly
- Add any new variables from install.yml, role defaults, preflight, and containerized_installer README
- Keep complex types in vars-example.yml (generated alongside inventories)
- Update scripts/build-inventory-{XY}.py and regenerate
- Update CONTAINERIZED_INVENTORY_CONTEXT.md if host groups or conventions changed

Follow config-examples/CONTAINERIZED_INVENTORY_CONTEXT.md.
```

## Related documentation

- [AAP 2.6 containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation)
- [Inventory variables appendix (2.6)](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars)
