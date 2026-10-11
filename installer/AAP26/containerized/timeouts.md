# AAP 2.6 — Containerized installer timeout / wait variables

Personal TSE notes for every inventory/extra-var timeout (and closely related wait/retry) knob in the **AAP 2.6 containerized installer**, plus hardcoded task waits that **cannot** be tuned via inventory.

Verified against lab clone `aap-26/installer/containerized_installer` (`stable-2.6`).

Related files in this folder: [README.md](README.md) · [extra-settings.md](extra-settings.md) · [vars-example.yml](vars-example.yml).

---

## Why this matters (stretched / multi-region installs)

When the installer control host runs in one region (e.g. East) and half the managed VMs are in another (West/Central), SSH RTT, image pulls, Redis cluster formation, DB migrations, and API readiness polls all take longer.

There are **two timeout families**:

| Family | What it affects | Tunable via inventory? |
|--------|-----------------|------------------------|
| **Runtime HTTP stack** | nginx / uwsgi / gunicorn / envoy / JWT / gRPC after install | Yes — primarily `client_request_timeout` (cascades) |
| **Install-time task waits** | image pull, migrate, PG ready, API ready, redis cluster create, postinstall async | Partially — only a few vars; most `retries`/`delay` are hardcoded |

Raising `client_request_timeout` helps **runtime API latency**. It does **not** stretch most migrate/init `until` loops.

---

## Index — inventory / extra vars

| Variable | Default | Tunable | Cascades / notes |
|----------|---------|---------|------------------|
| [`client_request_timeout`](#client_request_timeout-cascade) | **30** (min 10) | Yes | Fans out to most HTTP timeouts below |
| [`container_pull_timeout`](#install-time-tunable-vars) | **600** | Yes | Podman image pull/load task `timeout` (seconds) |
| [`controller_postinstall_async_delay`](#install-time-tunable-vars) | **1** | Yes | Controller configuration async poll delay |
| [`controller_postinstall_async_retries`](#install-time-tunable-vars) | **30** | Yes | Controller configuration async poll count |
| [`hub_postinstall_async_delay`](#install-time-tunable-vars) | **1** | Yes | Hub AH configuration async poll delay |
| [`hub_postinstall_async_retries`](#install-time-tunable-vars) | **30** | Yes | Hub AH configuration async poll count |
| [`controller_nginx_read_timeout`](#derived-from-client_request_timeout) | 15 | Yes (or via cascade) | `max(crt,10)/2` |
| [`controller_uwsgi_timeout`](#derived-from-client_request_timeout) | 10 | Yes | `max(crt,10)/3` |
| [`controller_uwsgi_timeout_grace_period`](#derived-from-client_request_timeout) | **2** | Yes | Fixed default (not derived) |
| [`eda_nginx_read_timeout`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` |
| [`eda_gunicorn_timeout`](#derived-from-client_request_timeout) | 10 | Yes | `max(crt,10)/3` |
| [`eda_gunicorn_timeout_grace_period`](#derived-from-client_request_timeout) | **2** | Yes | Fixed default |
| [`gateway_nginx_read_timeout`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` |
| [`gateway_uwsgi_timeout`](#derived-from-client_request_timeout) | 10 | Yes | `max(crt,10)/3` |
| [`gateway_uwsgi_timeout_grace_period`](#derived-from-client_request_timeout) | **2** | Yes | Fixed default |
| [`gateway_jwt_expiration_buffer_in_seconds`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` |
| [`gateway_grpc_auth_service_timeout`](#derived-from-client_request_timeout) | **15s** | Yes | `max(crt,10)/2` + literal `s` suffix |
| [`envoy_request_timeout`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` — used in `proxy.yml.j2`; **not** in installer README table |
| [`hub_nginx_read_timeout`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` |
| [`hub_nginx_send_timeout`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` — **not** in installer README table |
| [`hub_gunicorn_timeout`](#derived-from-client_request_timeout) | 10 | Yes | `max(crt,10)/3` |
| [`hub_gunicorn_timeout_grace_period`](#derived-from-client_request_timeout) | **2** | Yes | Fixed default |
| [`automationmetrics_nginx_read_timeout`](#derived-from-client_request_timeout) | 15 | Yes | `max(crt,10)/2` |
| [`automationmetrics_gunicorn_timeout`](#derived-from-client_request_timeout) | 10 | Yes | `max(crt,10)/3` |
| [`automationmetrics_dispatcherd_timeout`](#other-timeout-vars) | **1200** | Yes | Dispatcherd worker timeout (seconds) |
| [`automationmetrics_scheduler_check_interval`](#other-timeout-vars) | **30** | Yes | Scheduler poll interval (seconds) |
| [`lightspeed_nginx_read_timeout`](#derived-from-client_request_timeout) | **60** | Yes | `max(max(crt,10)/2, 60)` |
| [`lightspeed_uwsgi_timeout`](#derived-from-client_request_timeout) | **60** | Yes | `max(crt, 180)/3` |
| [`lightspeed_uwsgi_timeout_grace_period`](#derived-from-client_request_timeout) | **2** | Yes | Fixed default |
| [`eda_extra_settings` → `RULEBOOK_READINESS_TIMEOUT_SECONDS`](#eda-rulebook-readiness) | example **120** | Yes | Via extras list; runtime EDA, not installer task wait |

`crt` = `client_request_timeout`.

---

## `client_request_timeout` cascade

**Default:** `30`  
**Documented minimum:** `10`  
**Defined in:** role defaults for controller, hub, eda, gateway, lightspeed, automationmetrics (each role defaults to 30; inventory/`-e` overrides for all).

Jinja used by most components:

```jinja
{{ (([(client_request_timeout | int), 10] | max) / 2) | int }}   # nginx / envoy / jwt / grpc base
{{ (([(client_request_timeout | int), 10] | max) / 3) | int }}   # uwsgi / gunicorn
```

| `client_request_timeout` | `/2` (nginx, envoy, jwt, grpc) | `/3` (uwsgi, gunicorn) |
|--------------------------|--------------------------------|------------------------|
| 30 (default) | 15 | 10 |
| 60 | 30 | 20 |
| 120 | 60 | 40 |

Lightspeed is special-cased (higher floors) — see table above.

**Source defaults (examples):**

- `roles/automationcontroller/defaults/main.yml` — `client_request_timeout`, `controller_*`
- `roles/automationgateway/defaults/main.yml` — `client_request_timeout`, `gateway_*`, `envoy_request_timeout`
- `roles/automationhub/defaults/main.yml` — `client_request_timeout`, `hub_*`
- `roles/automationeda/defaults/main.yml` — `client_request_timeout`, `eda_*`
- `roles/common/defaults/main.yml` — `container_pull_timeout`

---

## Derived from `client_request_timeout`

Override individually only when one component needs a different value than the cascade.

### Controller

| Variable | Default @ crt=30 | Formula / notes |
|----------|------------------|-----------------|
| `controller_nginx_read_timeout` | 15 | `max(crt,10)/2` → nginx `uwsgi_read_timeout` |
| `controller_uwsgi_timeout` | 10 | `max(crt,10)/3` → uwsgi `harakiri` |
| `controller_uwsgi_timeout_grace_period` | 2 | uwsgi `harakiri-graceful-timeout` |

### Gateway

| Variable | Default @ crt=30 | Formula / notes |
|----------|------------------|-----------------|
| `gateway_nginx_read_timeout` | 15 | `max(crt,10)/2` |
| `gateway_uwsgi_timeout` | 10 | `max(crt,10)/3` |
| `gateway_uwsgi_timeout_grace_period` | 2 | fixed |
| `gateway_jwt_expiration_buffer_in_seconds` | 15 | `max(crt,10)/2` |
| `gateway_grpc_auth_service_timeout` | `15s` | `max(crt,10)/2` with `s` suffix → `GRPC_SERVER_AUTH_SERVICE_TIMEOUT` |
| `envoy_request_timeout` | 15 | `max(crt,10)/2` → `proxy.yml.j2` `request_timeout` |

### Hub

| Variable | Default @ crt=30 | Formula / notes |
|----------|------------------|-----------------|
| `hub_nginx_read_timeout` | 15 | `max(crt,10)/2` → `proxy_read_timeout` |
| `hub_nginx_send_timeout` | 15 | `max(crt,10)/2` → `proxy_send_timeout` |
| `hub_gunicorn_timeout` | 10 | `max(crt,10)/3` → pulp-api / pulp-content |
| `hub_gunicorn_timeout_grace_period` | 2 | `--graceful-timeout` |

### EDA

| Variable | Default @ crt=30 | Formula / notes |
|----------|------------------|-----------------|
| `eda_nginx_read_timeout` | 15 | `max(crt,10)/2` |
| `eda_gunicorn_timeout` | 10 | `max(crt,10)/3` |
| `eda_gunicorn_timeout_grace_period` | 2 | fixed |

### Automation Metrics

| Variable | Default @ crt=30 | Formula / notes |
|----------|------------------|-----------------|
| `automationmetrics_nginx_read_timeout` | 15 | `max(crt,10)/2` |
| `automationmetrics_gunicorn_timeout` | 10 | `max(crt,10)/3` |

### Lightspeed

| Variable | Default @ crt=30 | Formula / notes |
|----------|------------------|-----------------|
| `lightspeed_nginx_read_timeout` | **60** | `max(max(crt,10)/2, 60)` |
| `lightspeed_uwsgi_timeout` | **60** | `max(crt, 180)/3` |
| `lightspeed_uwsgi_timeout_grace_period` | 2 | fixed |

---

## Install-time tunable vars

These are the inventory knobs that actually affect **installer task** waiting (as opposed to runtime HTTP).

| Variable | Default | Where used |
|----------|---------|------------|
| `container_pull_timeout` | **600** | `roles/common` image pull/load; postgresql image pull — Ansible task `timeout:` |
| `controller_postinstall_async_delay` | **1** | Mapped to `controller_configuration_async_delay` in postinstall |
| `controller_postinstall_async_retries` | **30** | Mapped to `controller_configuration_async_retries` |
| `hub_postinstall_async_delay` | **1** | Mapped to `ah_configuration_async_delay` |
| `hub_postinstall_async_retries` | **30** | Mapped to `ah_configuration_async_retries` |

At defaults, controller/hub postinstall async budget ≈ `delay × retries` = **~30 seconds**. For slow cross-region configuration API work, raise both delay and retries.

Image pull **retry cadence** (`retries: 6`, `delay: 10`) is hardcoded; only the per-attempt `timeout` uses `container_pull_timeout`.

---

## Other timeout vars

| Variable | Default | Notes |
|----------|---------|-------|
| `automationmetrics_dispatcherd_timeout` | **1200** | Dispatcherd worker timeout (seconds) |
| `automationmetrics_scheduler_check_interval` | **30** | Scheduler `--check-interval` (seconds); poll interval, not a failure timeout |

---

## EDA rulebook readiness

Not a top-level timeout var — set via `eda_extra_settings` (see [extra-settings.md](extra-settings.md)):

```yaml
eda_extra_settings:
  - setting: RULEBOOK_READINESS_TIMEOUT_SECONDS
    value: 120
```

Runtime EDA behavior after install; does not change installer migrate/API wait loops.

---

## Hardcoded waits (not inventory-tunable)

These are the waits that commonly surface under WAN latency. **You cannot raise them via inventory** without patching the installer (unsupported).

| Area | Hardcoded values | Approx budget |
|------|------------------|---------------|
| Image pull retries (`common`) | `retries: 6`, `delay: 10` + `container_pull_timeout` | Retry cadence fixed; pull timeout tunable |
| Component init/migrate (controller, gateway, eda, hub, lightspeed) | mostly `retries: 5`, `delay: 60` | ~5 minutes |
| PG readiness (controller, hub, eda, metrics) | `retries: 30`, `delay: 10` | ~5 minutes |
| PG readiness (gateway, lightspeed) | `retries: 5`, `delay: 60` | ~5 minutes |
| Gateway API / proxy ready | `retries: 30`, `delay: 10` | ~5 minutes |
| Hub ready before collection/image upload | `retries: 5`, `delay: 60` | ~5 minutes |
| Hub collection upload URI | `request_timeout: 60`, `timeout: 60` | 60 seconds |
| Redis cluster create (`redis/tasks/cluster.yml`) | `timeout: 120` | **120 seconds** |
| Redis `cluster-node-timeout` (`redis.conf.j2`) | **15000** ms | fixed |
| Envoy CDS/LDS control-plane REST (`envoy.yaml.j2`) | `request_timeout` / `refresh_delay` **5s** | fixed (not `envoy_request_timeout`) |
| Controller `wait_for` port (`license.yml`) | no explicit timeout → Ansible default | typically **300s** |
| Container `stop_timeout` (controller/lightspeed) | **30** | fixed |

### Redis / Envoy nuance

- `envoy_request_timeout` (inventory, cascaded) feeds **Gateway proxy** request timeout in `proxy.yml.j2`.
- Envoy **control-plane** CDS/LDS REST timeouts in `envoy.yaml.j2` are separate and hardcoded to **5 seconds**.
- Redis cluster **create** task timeout (**120s**) and runtime `cluster-node-timeout` (**15s**) are both hardcoded — high risk for multi-region Redis.

---

## Ansible connection timeouts (not installer schema)

Installer `ansible.cfg` does **not** set `timeout`, SSH, or gather timeouts. For East→West SSH lag, use Ansible knobs (inventory / control-host ansible.cfg), for example:

```ini
[all:vars]
ansible_ssh_timeout=60
# or task-level / ansible.cfg:
# timeout = 60
```

```ini
[ssh_connection]
# ControlPersist / pipelining options as appropriate for your environment
```

These are **Ansible** settings, not AAP containerized-installer variables.

---

## Practical inventory snippet (stretch / multi-region)

```ini
[all:vars]
# Cascades nginx/uwsgi/gunicorn/envoy/JWT/gRPC (runtime HTTP)
client_request_timeout=120

# Slow / cross-region image pulls
container_pull_timeout=1800

# Configuration collection async waits (install-time)
controller_postinstall_async_delay=5
controller_postinstall_async_retries=120
hub_postinstall_async_delay=5
hub_postinstall_async_retries=120

# Optional Ansible SSH (not installer-native)
ansible_ssh_timeout=60
```

Or via `-e` / YAML extras file (same names).

Only override individual `*_nginx_*` / `*_uwsgi_*` / `*_gunicorn_*` when one component must differ from the cascade.

---

## What to tell the customer

1. Set **`client_request_timeout`** if API/proxy HTTP timeouts are the concern (runtime).
2. Set **`container_pull_timeout`** + postinstall async delay/retries if install tasks are slow.
3. Do **not** expect inventory knobs to fix migrate/init failures past the hardcoded ~5 minute `until` budgets — or Redis cluster create past **120s**.
4. For SSH lag from the install host to remote regions, raise Ansible SSH/task timeouts separately.
5. Multi-region Redis cluster and cross-DC database latency remain architectural risks; timeouts only buy time — they do not fix RTT/bandwidth.

---

## Source map

| Path under `aap-26/installer/containerized_installer/` | Content |
|--------------------------------------------------------|---------|
| `README.md` | Documented inventory vars + defaults |
| `roles/*/defaults/main.yml` | Defaults and cascade Jinja |
| `roles/common/tasks/main.yml`, `bundle_images.yml`, `postgresql.yml` | `container_pull_timeout` usage |
| `roles/*/tasks/init.yml`, `postgresql.yml`, `postinstall.yml` | Hardcoded retries/delays |
| `roles/redis/tasks/cluster.yml` | Hardcoded `timeout: 120` |
| `roles/redis/templates/redis.conf.j2` | `cluster-node-timeout 15000` |
| `roles/automationgateway/templates/proxy.yml.j2` | `envoy_request_timeout` |
| `roles/automationgateway/templates/envoy.yaml.j2` | Hardcoded CDS/LDS 5s |
| `ansible.cfg` | No timeout settings |

---

**Document version:** 1.0  
**Last review:** 2026-04-10  
**Based on:** `aap-26/installer/containerized_installer` @ `stable-2.6`
