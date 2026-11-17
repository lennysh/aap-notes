# AAP 2.6 — Containerized service stop / start / restart order

Personal TSE notes on the safe order to stop, start, and restart AAP containers on an **AAP 2.6 containerized** install, and the systemd `Requires=` coupling that makes order matter.

Verified against lab clone `aap-26/installer/containerized_installer` (`stable-2.6`) and the 2.6 product docs (*Migrate to containerized* assembly). Not yet validated on a live host.

Related files in this folder: [README.md](README.md) · [timeouts.md](timeouts.md) · [extra-settings.md](extra-settings.md). RPM equivalent: [../rpm/service-order.md](../rpm/service-order.md). Other versions: [2.5](../../AAP25/containerized/service-order.md) · [2.7](../../AAP27/containerized/service-order.md).

---

## TL;DR

| Action | Order |
|--------|-------|
| **Stop** | pcp → EDA → Gateway → Controller (drain first) → receptor (Controller, then execution/hop) → Hub → Lightspeed / MCP / Metrics → redis → postgresql |
| **Start** | postgresql → redis → receptor (execution/hop) → Hub → Controller → Gateway → EDA → Lightspeed / MCP / Metrics → pcp |
| **Restart one component** | Restart only that component's containers. **Don't** restart `postgresql` or `redis-unix` on a shared node unless you mean to bounce everything that requires them. |

The hard rules are **DB first up, last down** and **Redis before the apps**. The order *between* Gateway / Controller / Hub / EDA is a graceful-drain choice: stop new triggers (EDA), then ingress (Gateway), then let running jobs finish before stopping Controller.

All units are **rootless user units** under the install user: always `systemctl --user ...`, run as that user, never as root. Unit files live in `~/.config/systemd/user/`.

---

## Containers / units per component

| Component | Units (`systemctl --user`) |
|-----------|----------------------------|
| Gateway | `automation-gateway`, `automation-gateway-proxy` |
| Controller | `automation-controller-web`, `automation-controller-task`, `automation-controller-rsyslog` (+ timers `metrics-utility-gather.timer`, `metrics-utility-build-report.timer` if enabled) |
| Receptor | `receptor` (Controller nodes + execution/hop nodes) |
| Hub | `automation-hub-api`, `automation-hub-content`, `automation-hub-web`, `automation-hub-worker-{1..N}` |
| EDA | `automation-eda-api`, `automation-eda-daphne`, `automation-eda-web`, `automation-eda-scheduler`, `automation-eda-worker-{1..N}`, `automation-eda-activation-worker-{1..N}` |
| Redis | `redis-unix` (local socket, used by Controller/Hub/EDA), `redis-tcp` (Gateway / cluster) |
| Database | `postgresql` (only when installer-managed `[database]`) |
| Monitoring | `pcp` (if `setup_monitoring`) |
| Lightspeed | `ansible-lightspeed`, `ansible-lightspeed-chatbot`, `ansible-lightspeed-mcp-*` |
| MCP | `ansiblemcp` |
| Metrics service | `automation-metrics-web`, `automation-metrics-tasks`, `automation-metrics-scheduler` |

Handy: `systemctl --user list-units 'automation-*' 'redis-*' receptor postgresql pcp`

---

## systemd coupling — the gotchas

Each role builds its container's `Requires=` list (`roles/*/defaults/main.yml` + `roles/*/tasks/facts.yml`):

| Containers | `Requires=` |
|------------|-------------|
| `automation-controller-*` | `redis-unix` (+ `postgresql` **if `[database]` is on the same node**) |
| `automation-hub-*` (api, content, workers) | `redis-unix` (+ `postgresql` if same node) |
| `automation-eda-*` (api, daphne, workers, scheduler) | `redis-unix` (+ `postgresql` if same node) |
| `automation-gateway*`, Lightspeed, MCP, Metrics | *(none)* (+ `postgresql` if same node) |

systemd `Requires=` semantics:

- **Starting** an app container automatically starts `redis-unix` (and a local `postgresql`).
- **Stopping or restarting** `postgresql` or `redis-unix` **also stops or restarts every container on that node that requires it.**
  - Growth / all-in-one topology: `systemctl --user restart postgresql` bounces Controller, Hub, EDA, and Gateway.
  - `systemctl --user restart redis-unix` bounces Controller, Hub, and EDA on that node (not Gateway).
- Gateway has no Redis `Requires=`. It talks to `redis-tcp` / the Redis cluster over the network, so Redis must be up first, but systemd won't enforce it.

---

## What Red Hat documents

The *Migrate to containerized* assembly (`product-docs/migrate/migrate-assembly_target_containerized.md`) stops everything **except the database** in this order:

```bash
systemctl --user stop pcp
systemctl --user stop automation-controller-task automation-controller-web automation-controller-rsyslog
systemctl --user stop receptor
systemctl --user stop automation-hub-api automation-hub-content automation-hub-web automation-hub-worker-1 automation-hub-worker-2
systemctl --user stop automation-eda-scheduler automation-eda-daphne automation-eda-web automation-eda-api \
                      automation-eda-worker-1 automation-eda-worker-2 \
                      automation-eda-activation-worker-1 automation-eda-activation-worker-2
systemctl --user stop automation-gateway automation-gateway-proxy
systemctl --user stop redis-unix redis-tcp   # gateway node (standalone) or every [redis] node (cluster)
```

It then **starts them in the same order, with Redis last**. That only works because `Requires=redis-unix` pulls `redis-unix` up automatically when Controller/Hub/EDA start. It isn't a clean dependency order, so flag it if a customer copies it verbatim, especially for `redis-tcp` / Gateway.

The installer's `backup.yml` / `restore.yml` don't do a global ordered stop/start. Each role's `backup.yml` / `restore.yml` handles its own containers.

---

## Recommended procedure

Enterprise topology: run each block on the matching nodes. Growth topology: run everything on the single host.

### Stop

```bash
# 0. All nodes, if monitoring is configured
systemctl --user stop pcp

# 1. EDA — stop activations launching new jobs
systemctl --user stop automation-eda-scheduler 'automation-eda-activation-worker-*' 'automation-eda-worker-*' \
                      automation-eda-daphne automation-eda-api automation-eda-web

# 2. Gateway — cut user/API traffic
systemctl --user stop automation-gateway automation-gateway-proxy

# 3. Controller — first drain (disable instances / wait for running jobs)
systemctl --user stop metrics-utility-gather.timer metrics-utility-build-report.timer 2>/dev/null
systemctl --user stop automation-controller-web automation-controller-task automation-controller-rsyslog
systemctl --user stop receptor            # Controller nodes, then execution / hop nodes

# 4. Hub
systemctl --user stop automation-hub-api automation-hub-content 'automation-hub-worker-*' automation-hub-web

# 5. Optional components (if deployed)
systemctl --user stop 'ansible-lightspeed*' ansiblemcp 'automation-metrics-*'

# 6. Redis — standalone: first gateway node; cluster: every [redis] node
systemctl --user stop redis-unix redis-tcp

# 7. Database (installer-managed only)
systemctl --user stop postgresql
```

### Start

```bash
systemctl --user start postgresql
systemctl --user start redis-tcp redis-unix
systemctl --user start receptor                 # execution / hop nodes, then Controller nodes
systemctl --user start automation-hub-api automation-hub-content automation-hub-web 'automation-hub-worker-*'
systemctl --user start automation-controller-rsyslog automation-controller-task automation-controller-web
systemctl --user start automation-gateway-proxy automation-gateway
systemctl --user start automation-eda-api automation-eda-daphne automation-eda-web automation-eda-scheduler \
                       'automation-eda-worker-*' 'automation-eda-activation-worker-*'
systemctl --user start 'ansible-lightspeed*' ansiblemcp 'automation-metrics-*'   # if deployed
systemctl --user start metrics-utility-gather.timer metrics-utility-build-report.timer 2>/dev/null
systemctl --user start pcp
curl -k https://<gateway>/api/gateway/v1/ping/   # verify
```

Glob patterns only match units that are **loaded**. If `systemctl --user start 'automation-hub-worker-*'` matches nothing after a reboot, list the worker numbers explicitly (count = `hub_workers` / `eda_workers` / `eda_activation_workers`).

Starting Gateway before EDA means activations that restart can reach Controller and Hub through Gateway.

---

## Gaps / to verify on a live host

```bash
systemctl --user show -p Requires -p After automation-controller-task automation-gateway automation-hub-api
systemctl --user list-dependencies --reverse redis-unix
systemctl --user list-dependencies --reverse postgresql
```
