# AAP 2.6 → 2.7 — Containerized Installer Inventory Migration Guide

**Audience:** Customers (or support) taking a **working AAP 2.6 containerized inventory** and pointing the **2.7 containerized installer** at it without first editing the file.

**Goal:** List the inventory tweaks that must be done **before** the first `ansible-playbook` run, so preflight does not fail repeatedly.

**Compared trees (lab clones):**

| Tree | Branch / tip | Collection version |
|------|----------------|--------------------|
| `aap-26/installer/containerized_installer` | `stable-2.6` | `galaxy.yml` → `2.6.0` |
| `aap-27/installer/containerized_installer` | `stable-2.7` | `galaxy.yml` → `2.7.0` |

**Primary evidence:** sample inventories under `samples/`, preflight asserts under `roles/preflight/tasks/`, role defaults, and README variable tables.

This guide is about **inventory / vars / host groups**. It is not a full platform upgrade runbook (backup, downtime, DB migrations, etc.).

---

## Executive summary — will a reused 2.6 inventory fail?

**Yes, for almost every Controller-based 2.6 inventory that did not already deploy Automation Metrics.**

In 2.6, `[automationmetrics]` and its vars were **commented / optional** in the starter samples. In 2.7, preflight **requires** an `[automationmetrics]` host whenever `[automationcontroller]` is present, unless you explicitly opt out with `automationmetrics_skip_install=true`.

Typical first failure:

```text
You must have a host set in the [automationmetrics] section
```

After you add the group, the next failures are usually missing metrics DB vars (`automationmetrics_pg_*` / `automationmetrics_controller_read_pg_*`).

EDA customers on **external PostgreSQL without `postgresql_admin_password`** hit a **second** new hard requirement: `eda_event_stream_pg_password` (or event-stream cert auth).

---

## Pre-flight checklist (edit inventory first)

Work top-to-bottom. Stop when your topology does not include that component.

### 1. Automation Metrics (Controller present) — **almost always required**

| Action | Detail |
|--------|--------|
| **Add host group** | Uncomment / add `[automationmetrics]` with at least one hostname (dedicated host for enterprise; same host as AAP for growth). |
| **Add metrics DB vars** | At minimum: `automationmetrics_pg_host`, `automationmetrics_pg_password`. Enterprise sample also sets `automationmetrics_pg_database`, `automationmetrics_pg_username`. |
| **Add Controller read-access vars** | Required when Controller is deployed: `automationmetrics_controller_read_pg_host`, `automationmetrics_controller_read_pg_password`. Optionally set `automationmetrics_controller_read_pg_database` / `_username` (must match Controller DB name if set). |
| **Or opt out** | Set `automationmetrics_skip_install=true` **and leave `[automationmetrics]` empty/absent**. Opt-out only suppresses the *requirement*; the install play still targets any hosts listed under `[automationmetrics]`. |

**Why (2.7 code):**

- Preflight includes metrics checks when the metrics group is non-empty **or** Controller is present and skip is false — `aap-27/.../roles/preflight/tasks/main.yml`.
- Assert: metrics host required when Controller present and not skipped — `aap-27/.../roles/preflight/tasks/automationmetrics.yml` (`You must have a host set in the [automationmetrics] section`).
- Same file still requires `automationmetrics_pg_host` / password (unless cert auth) and controller-read host/password when Controller is present.
- 2.6 only ran metrics preflight when the group was already populated — `aap-26/.../roles/preflight/tasks/main.yml`.
- Samples: metrics group + vars **enabled** in 2.7 `samples/inventory` and `samples/inventory-growth`; **commented** in 2.6 counterparts.

**Growth vs enterprise var minimums (from samples):**

```ini
# Growth (managed [database]) — typical minimum
[automationmetrics]
aap.example.org

automationmetrics_pg_host=aap.example.org
automationmetrics_pg_password=<set your own>
automationmetrics_controller_read_pg_host=aap.example.org
automationmetrics_controller_read_pg_password=<set your own>
```

```ini
# Enterprise (external DB) — sample also sets DB name/user
[automationmetrics]
metrics1.example.org

automationmetrics_pg_host=externaldb.example.org
automationmetrics_pg_database=<set your own>
automationmetrics_pg_username=<set your own>
automationmetrics_pg_password=<set your own>
automationmetrics_controller_read_pg_host=externaldb.example.org
automationmetrics_controller_read_pg_database=<set your own>
automationmetrics_controller_read_pg_username=<set your own>
automationmetrics_controller_read_pg_password=<set your own>
```

**Ops note:** Metrics needs a Postgres DB for itself, plus a **read-only** user on the Controller DB. With `postgresql_admin_password` set, the installer can create that read-only user; without admin password, create it manually first (documented in 2.7 README Metrics section).

---

### 2. EDA — remove Redis inventory knobs; add event-stream DB awareness

| Action | Detail |
|--------|--------|
| **Remove / ignore** | All `eda_redis_*` inventory variables (`eda_redis_host`, `eda_redis_password`, `eda_redis_port`, `eda_redis_username`, `eda_redis_disable_tls`, `eda_redis_tls_cert`, `eda_redis_tls_key`). Removed from 2.7 README and role defaults. Leaving them set is usually harmless (unused) but is misleading. |
| **Expect cleanup on upgrade** | 2.7 EDA role runs `remove_redis.yml` to tear down legacy EDA Redis artifacts (unix-socket redis uninstall in some topologies, `eda_redis_password` podman secret, redis TLS files under EDA conf). |
| **External DB, no admin password** | If `[database]` is empty **and** `postgresql_admin_password` is unset, you **must** set `eda_event_stream_pg_password` **or** enable `eda_event_stream_pg_cert_auth` (+ TLS cert/key + `custom_ca_cert`). Pre-create user `eda_event_stream` (or your `eda_event_stream_pg_username`) on the external DB. |
| **External DB with admin password** | Installer can create the event-stream DB user; password may be auto-generated — no inventory change required for a basic upgrade. |
| **Managed `[database]`** | Same as admin-password path for creation; event-stream password defaults to auto-generated. |
| **Optional event persistence** | Only if enabling `eda_event_persistence_deploy_db=true`: configure `eda_event_persistence_pg_*`. With external DB and no admin password, `eda_event_persistence_pg_password` (or cert auth) is required and the user must be pre-created. Default is `false` — most 2.6 inventories can ignore this. |

**Why (2.7 code):**

- Defaults dropped Redis; added event-stream / event-persistence DB defaults — `aap-27/.../roles/automationeda/defaults/main.yml` (`eda_container_requires: []`, no `eda_redis_*`).
- New asserts — `aap-27/.../roles/preflight/tasks/automationeda.yml`.
- Preflight no longer validates `eda_redis_tls_*`; validates `eda_event_stream_pg_tls_*` when cert auth is on — `nodes.yml`.

---

### 3. Hardcoded image / registry overrides — **check and fix**

Defaults changed between trees. A 2.6 inventory that **pinned** old defaults will keep pulling 2.6 namespaces/tags unless updated.

| Variable | 2.6 default | 2.7 default | Migration action |
|----------|-------------|-------------|------------------|
| `registry_ns_aap` | `ansible-automation-platform-26` | `ansible-automation-platform-27` | Remove the pin, or set to `...-27` (or your disconnected mirror equivalent). |
| `ee_minimal_image` | `ee-minimal-rhel9:latest` | `ee-minimal-rhel9:2.16` | Only matters if you override; consider aligning with 2.7 default / content sync. |
| `de_minimal_image` | *(not in 2.6 README)* | `de-minimal-rhel9:latest` | New optional image var; no inventory change required unless you customize DEs. |

Source: `roles/common/defaults/main.yml` in each tree.

---

### 4. Lightspeed (only if `[ansiblelightspeed]` is used)

| Action | Detail |
|--------|--------|
| **No new required vars** for a basic Lightspeed deploy that already worked on 2.6. | |
| **New optional vars** | `lightspeed_streaming_timeout` (default `3600`), computed `lightspeed_request_timeout` / `lightspeed_idle_timeout`. |
| **BYOK (new)** | If setting `lightspeed_chatbot_byok_image`, you must also set `lightspeed_chatbot_model_url`, have **podman** already installed on that host, and **pre-load** the image (`podman load ...`) before install. Preflight fails otherwise. |

2.7 samples **removed** the large commented Lightspeed block from the starter inventories (still documented in README). That does not remove Lightspeed support — only the sample hints.

---

### 5. Gateway / Envoy TLS (optional customization)

New inventory knobs (all optional; defaults keep prior behavior):

- `envoy_http_port` (80), `envoy_https_port` (443), `envoy_disable_https`
- `envoy_tls_cert`, `envoy_tls_key`, `envoy_tls_remote`

If you set Envoy TLS paths, preflight validates cert/key match (including PQC/ML-DSA via openssl). No change needed if you never set them.

---

### 6. Upgrade path gate (in-place upgrades, not greenfield)

On hosts in `[automationgateway]`, 2.7 runs `upgrade_check.yml`: if an `automation-gateway` container already exists, installed gateway version must be **≥ `2.6`** (`aap_minimum_upgrade_version` in `roles/preflight/vars/main.yml`).

Unsupported jump (e.g. older than 2.6 → 2.7) fails preflight with `Unsupported upgrade path detected`.

---

## Inventory diff at a glance

### Host groups

| Group | 2.6 starter samples | 2.7 starter samples | Preflight change |
|-------|---------------------|---------------------|------------------|
| `[automationmetrics]` | Commented (optional) | **Enabled** | **Required** if Controller present unless `automationmetrics_skip_install=true` |
| `[ansiblelightspeed]` / `[ansiblemcp]` | Commented optional | Still commented optional | Unchanged requirement model |
| Others (gateway, controller, hub, eda, redis, database, execution_nodes) | As before | As before | No new “must add group” rules found |

### Variables — add / remove / watch

| Category | Change |
|----------|--------|
| **Must add** (typical Controller inventory) | `[automationmetrics]` host(s) + `automationmetrics_pg_*` + `automationmetrics_controller_read_pg_*` **or** `automationmetrics_skip_install=true` |
| **Must add** (EDA + external DB, no `postgresql_admin_password`) | `eda_event_stream_pg_password` **or** event-stream cert-auth vars; pre-create DB user |
| **Should remove** | `eda_redis_*` |
| **New optional** | `eda_event_stream_pg_*`, `eda_event_persistence_*`, `envoy_*`, Lightspeed timeout/BYOK vars, `automationmetrics_skip_install`, `de_minimal_image` |
| **Watch overrides** | `registry_ns_aap` still pointing at `-26`; stale image tags |

### README “Required” column

Programmatic compare of README tables: **no variable flipped from Optional → Required in the tables**. The breaking behavior is enforced in **preflight logic** (metrics group required with Controller; event-stream credentials for certain external-DB topologies), not by flipping the README Required column for existing vars.

---

## Likely failure sequence (reused 2.6 inventory)

1. **Metrics host missing** → `You must have a host set in the [automationmetrics] section`
2. **Metrics PG host/password missing** → `automationmetrics_pg_host must be set...` / `automationmetrics_pg_password must be set...`
3. **Controller read PG host/password missing** → `automationmetrics_controller_read_pg_host must be set...` / `..._password must be set...`
4. **(EDA + external DB, no admin password)** → event stream auth assert mentioning `eda_event_stream_pg_password` / cert auth
5. **(Optional)** Wrong `registry_ns_aap` → pull/auth failures later (not always preflight)
6. **(In-place from &lt; 2.6)** → `Unsupported upgrade path detected`

Fix inventory for steps 1–4 **before** re-running install.

---

## Minimal “patch my 2.6 inventory” recipes

### A. Keep Metrics (recommended / default product path)

1. Add `[automationmetrics]` with a real host.
2. Copy the metrics `[all:vars]` block from 2.7 `samples/inventory` or `samples/inventory-growth` matching your topology.
3. Ensure Postgres capacity/users exist (metrics DB + Controller read-only access).
4. Delete any `eda_redis_*` lines.
5. If EDA uses external DB **without** admin password: add `eda_event_stream_pg_password=...` and pre-create the user.
6. Fix any `registry_ns_aap=ansible-automation-platform-26` override to `-27` or remove it.
7. Run 2.7 installer.

### B. Skip Metrics for this run

```ini
# [all:vars]
automationmetrics_skip_install=true
```

- Do **not** populate `[automationmetrics]`.
- Still clean up `eda_redis_*` / event-stream / registry overrides as above if they apply.

---

## What did *not* change (for inventory reuse)

- Core required groups for a full platform install (gateway, controller, hub, eda, redis/database patterns) remain the same model.
- Existing required admin/DB vars for gateway/controller/hub/eda (`*_admin_password`, `*_pg_host`, etc.) remain required under the same conditions.
- Redis **cluster/standalone** inventory model for Gateway/Controller/Hub is unchanged; only **EDA’s own Redis** integration was removed.
- Lightspeed / MCP remain optional host groups.

---

## Source map (for deeper RCA)

| Topic | 2.6 path | 2.7 path |
|-------|----------|----------|
| Sample enterprise inventory | `aap-26/.../samples/inventory` | `aap-27/.../samples/inventory` |
| Sample growth inventory | `aap-26/.../samples/inventory-growth` | `aap-27/.../samples/inventory-growth` |
| Preflight include rules | `.../roles/preflight/tasks/main.yml` | same (metrics `when:` widened) |
| Metrics asserts | `.../preflight/tasks/automationmetrics.yml` | same + host-required assert + `skip_install` |
| EDA asserts | `.../preflight/tasks/automationeda.yml` | + event stream / persistence asserts |
| EDA defaults | `.../automationeda/defaults/main.yml` | Redis removed; event-stream DB added |
| Upgrade gate | *(absent)* | `.../preflight/tasks/upgrade_check.yml` + `vars/main.yml` |
| Variable catalog | `.../README.md` | `.../README.md` |

---

## Related notes in this folder

- [README.md](README.md) — 2.7 inventory reference / enabled settings
- [inventory-example](inventory-example) / [inventory-growth-example](inventory-growth-example) — annotated 2.7 inventories
- [vars-example.yml](vars-example.yml) — YAML-only options
- Upstream docs: [2.7 containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation), [inventory variables appendix](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation/appendix-inventory-files-vars)
