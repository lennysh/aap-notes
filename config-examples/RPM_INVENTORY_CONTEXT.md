# RPM inventory maintenance context

Use this document when adding a new AAP version or refreshing RPM installer inventories after a Red Hat installer update.

## Goal

Each version directory (for example `AAP25/rpm/`) ships:

1. **`inventory-example`** — matches upstream `inventory` enabled `[all:vars]` lines exactly; adds example hosts and documents every other supported variable commented out.
2. **`vars-example.yml`** — YAML-only complex variables (lists, dictionaries).

**AAP 2.7 has no RPM installer.** Do not add `AAP27/rpm/`.

## Directory convention

```
config-examples/
├── RPM_INVENTORY_CONTEXT.md
├── .installer-dumps/               # gitignored
│   ├── 2.4/ansible-automation-platform-setup-2.4-*/
│   ├── 2.5/ansible-automation-platform-setup-2.5-*/
│   └── 2.6/ansible-automation-platform-setup-2.6-*/
├── scripts/
│   ├── build_rpm_inventory.py      # shared RPM generator
│   ├── build-rpm-inventory-2.4.py  # thin wrappers
│   ├── build-rpm-inventory-2.5.py
│   └── build-rpm-inventory-2.6.py
└── AAP{XY}/
    ├── openshift/
    ├── containerized/              # 2.5+ only
    └── rpm/                        # 2.4–2.6 only
        ├── inventory-example
        ├── vars-example.yml
        └── README.md
```

RPM and containerized installers use different tarball names:

| Method | Example dump path |
|--------|-------------------|
| RPM | `.installer-dumps/2.6/ansible-automation-platform-setup-2.6-7` |
| Containerized | `.installer-dumps/2.6/ansible-automation-platform-containerized-setup-2.6-10` |

## Profiles

| Profile | Versions | Host groups | Notes |
|---------|----------|-------------|-------|
| **legacy** | 2.4 | `automationcontroller`, `execution_nodes`, `automationhub`, `automationedacontroller`, `database`, `sso` | SSO vars, managed `[database]`, inline optional blocks in upstream inventory |
| **gateway** | 2.5, 2.6 | `automationgateway`, `automationcontroller`, `execution_nodes`, `automationhub`, `automationedacontroller`, `redis` | Gateway + Redis cluster; upstream inventory has enabled vars only (no inline optional blocks) |

`[automationcontroller:vars]` sets `peers=execution_nodes` in both profiles.

### Host-level variables (not in `[all:vars]`)

| Variable | Groups | Values | Profile |
|----------|--------|--------|---------|
| `node_type` | `automationcontroller` | `control`, `hybrid` | legacy |
| `node_type` | `execution_nodes` | `hop`, `execution` | both |
| `sso_redirect_host` | `sso` | hostname or IP | legacy |

### Complex types (use vars-example.yml)

- `automationhub_importer_settings`, `ldap_extra_settings` (dicts)
- `extra_images`, `ee_images`, `de_images`, `decision_environments`, `global_job_execution_environments` (lists)
- `nginx_user_headers`, `automationhub_user_headers`, `automationgateway_user_headers`, `automationedacontroller_*` header/origin lists

## Authoritative sources

When building or updating a version, extract the matching installer under `.installer-dumps/{version}/` and review:

| Source | Path (inside extracted installer) | What to extract |
|--------|-----------------------------------|-----------------|
| Starter inventory | `inventory` | **Enabled `[all:vars]` lines** — must not drift |
| Install guide | Red Hat docs + `README.md` | User-facing descriptions |
| Collection globals | `collections/.../automation_platform_installer/playbooks/vars/collection_global_vars.yml` | Default variable wiring |
| Install playbook | `.../playbooks/install.yml` | Host groups, conditional features |
| Role defaults | `.../roles/*/defaults/main.yml` | Defaults and inline comments |
| Preflight / check_config | `roles/preflight`, `roles/check_config_static` | Validated vars |

## Generator workflow

1. Edit `scripts/build_rpm_inventory.py`:
   - **Legacy (2.4):** `[all:vars]` content (enabled lines and upstream optional blocks) is read from the installer dump; `ENABLED_ALL_VARS` is a verification reference only
   - **Gateway (2.5+):** host groups and enabled block are read from the installer dump at generation time
   - `EXTRA_CATALOG` / `EXTRA_CATALOG_LEGACY` / `EXTRA_CATALOG_GATEWAY` — additional vars from role defaults
   - `VERSIONS` — add new AAP versions when RPM installers are added (not expected for 2.7+)
2. Run:

   ```bash
   python3 scripts/build_rpm_inventory.py              # all versions
   python3 scripts/build_rpm_inventory.py --version 2.6  # one version
   ```

3. Diff `[all:vars]` enabled lines against fresh upstream `inventory`
4. For gateway versions, diff host groups through enabled `[all:vars]` against upstream
5. Spot-check role defaults for new/changed keys
6. Run `python3 scripts/audit_inventories.py` — checks enabled-line match, bool/`None` conventions, catalog duplicates, and empty configuration sections

### Verified installer dumps

| AAP version | Dump path | `[all:vars]` match |
|-------------|-----------|-------------------|
| 2.4 | `.installer-dumps/2.4/ansible-automation-platform-setup-2.4-16` | yes |
| 2.5 | `.installer-dumps/2.5/ansible-automation-platform-setup-2.5-23` | yes |
| 2.6 | `.installer-dumps/2.6/ansible-automation-platform-setup-2.6-7` | yes |

## Adding a new version (checklist)

- [ ] Confirm Red Hat ships an RPM installer for the version (2.7 does not)
- [ ] Extract installer under `.installer-dumps/{version}/`
- [ ] Create `AAP{XY}/rpm/` and copy/adapt README from nearest version
- [ ] Add `RpmVersionConfig` to `scripts/build_rpm_inventory.py` (`profile: legacy` or `gateway`)
- [ ] For legacy: diff enabled lines and section layout against upstream `inventory` after regen
- [ ] Diff role defaults vs `EXTRA_CATALOG_*`
- [ ] Regenerate and verify enabled `[all:vars]` lines
- [ ] Update [config-examples/README.md](README.md)

## Related documentation

- [AAP 2.4 installation guide](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.4/html-single/red_hat_ansible_automation_platform_installation_guide/index)
- [AAP 2.5 RPM installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/rpm_installation)
- [AAP 2.6 RPM installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/rpm_installation)
- [Containerized inventory maintenance](CONTAINERIZED_INVENTORY_CONTEXT.md) — separate installer collection (`ansible.containerized_installer`)
