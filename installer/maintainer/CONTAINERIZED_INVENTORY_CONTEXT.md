# Containerized inventory maintenance context

Use this document when adding a new AAP version (2.5, 2.7, …) or refreshing inventories after a Red Hat installer update.

## Goal

Each version directory (for example `AAP26/containerized/`) ships two inventory reference files:

1. **Enterprise** — `inventory-example`; matches upstream `inventory` enabled lines exactly.
2. **Growth** — `inventory-growth-example`; matches upstream `inventory-growth` enabled lines exactly.

All other user-configurable variables appear **commented out** with a one-line description and an example/default value where applicable.

## Directory convention

```
aap-notes/
├── .installer-dumps/               # gitignored (repo root)
├── installer/
│   ├── maintainer/CONTAINERIZED_INVENTORY_CONTEXT.md
│   ├── scripts/build_inventory.py  # --version 2.5|2.6|2.7|all
│   └── AAP{XY}/containerized/      # inventories, vars-example.yml, install-playbook-tasks.md, README.md
└── openshift/
    └── AAP{XY}/                    # operator CR examples (separate from installer)
```

## Authoritative sources (check in this order)

RPM and containerized installers use different tarball names:

| Method | Example dump path |
|--------|-------------------|
| RPM | `.installer-dumps/2.4/ansible-automation-platform-setup-2.4-16` |
| Containerized | `.installer-dumps/2.6/ansible-automation-platform-containerized-setup-2.6-10` |

When building or updating a version, extract the matching installer under `.installer-dumps/{version}/` and review:

| Source | Path (inside extracted installer) | What to extract |
|--------|-----------------------------------|-----------------|
| Starter inventories | `inventory`, `inventory-growth` | **Enabled lines only** — must not drift |
| Variable appendix | Installer README + Red Hat docs | User-facing descriptions |
| Collection README | `collections/ansible_collections/ansible/containerized_installer/README.md` | Full variable tables (primary catalog) |
| Install playbook | `.../playbooks/install.yml` | Conditional features (`when:` vars), host groups |
| Install playbook tasks (generated) | `installer/AAP{XY}/containerized/install-playbook-tasks.md` | Recursive task reference from `install.yml` (co-located with inventories) |
| Role defaults | `.../roles/*/defaults/main.yml` | Defaults not listed in README |
| Preflight role | `.../roles/preflight/tasks/*.yml` | Validated vars, host-level constraints |
| Changelog | `.../changelogs/changelog.yaml` | New/renamed/removed variables |

### Host groups referenced by `install.yml` (2.6+)

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

**2.7 change:** `[automationmetrics]` is enabled in the upstream starter inventories when `[automationcontroller]` is deployed.

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

## Generator workflow

1. Edit `scripts/build_inventory.py`:
   - `CATALOG`, `GATEWAY_VARS`, `CONTROLLER_VARS`, … — optional variable definitions
   - `VERSIONS` — per-version flags (`include_mcp`, `include_metrics`, `metrics_in_starter`, `include_eda_redis`)
   - `ENTERPRISE_ENABLED` / enabled-value helpers — vars that must stay uncommented per topology
2. Run from repo root or `installer/`:

   ```bash
   python3 installer/scripts/build_inventory.py              # 2.5, 2.6, and 2.7
   python3 installer/scripts/build_inventory.py --version 2.7
   ```

   Writes `AAP{XY}/containerized/inventory-example`, `inventory-growth-example`, and `vars-example.yml`.

3. Diff enabled sections against fresh upstream `inventory` / `inventory-growth` from `.installer-dumps/{version}/`
4. Spot-check new installer README tables against catalog
5. Regenerate install playbook task docs: `python3 installer/scripts/extract_install_playbook_tasks.py --version {X.Y} --method containerized`

### Verified installer dumps

| AAP version | Dump path | Enabled lines match |
|-------------|-----------|---------------------|
| 2.5 | `.installer-dumps/2.5/ansible-automation-platform-containerized-setup-2.5-25` | yes |
| 2.6 | `.installer-dumps/2.6/ansible-automation-platform-containerized-setup-2.6-10` | yes |
| 2.7 | `.installer-dumps/2.7/ansible-automation-platform-containerized-setup-2.7-2` | yes |

## Adding a new version (checklist)

- [ ] Create `AAP{XY}/containerized/` and copy/adapt the nearest version README
- [ ] Add a `VersionConfig` entry to `scripts/build_inventory.py` (`VERSIONS` dict)
- [ ] Update doc URLs and `registry_ns_aap` for the new version
- [ ] Replace upstream starter paths and enabled var sets from new `inventory` files
- [ ] Diff `containerized_installer/README.md` variable tables vs prior version catalog
- [ ] Diff all `roles/*/defaults/main.yml` for new/changed keys
- [ ] Read `install.yml` for new host groups or `when:` conditionals
- [ ] Regenerate and verify enabled blocks byte-match upstream starters (except added header comments)
- [ ] Update [installer/README.md](../README.md) version table

## AI assistant prompt template

When asking an agent to refresh inventories:

```
Refresh the AAP {X.Y} containerized inventory reference in aap-notes.

Installer extracted at: aap-notes/.installer-dumps/{X.Y}/ansible-automation-platform-containerized-setup-{X.Y}-*/

Requirements:
- Enabled lines must match upstream inventory and inventory-growth exactly
- Add any new variables from install.yml, role defaults, preflight, and containerized_installer README
- Keep complex types in vars-example.yml (generated alongside inventories)
- Update installer/scripts/build_inventory.py and regenerate
- Update installer/maintainer/CONTAINERIZED_INVENTORY_CONTEXT.md if host groups or conventions changed

Follow installer/maintainer/CONTAINERIZED_INVENTORY_CONTEXT.md.
```

## Related documentation

- [AAP 2.6 containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation)
- [Inventory variables appendix (2.6)](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-inventory-files-vars)
