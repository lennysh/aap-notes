# AAP 2.7 — Containerized service stop / start / restart order

Personal TSE notes on the safe order to stop, start, and restart AAP containers on an **AAP 2.7 containerized** install, and the systemd `Requires=` coupling that makes order matter.

Verified against lab clone `aap-27/installer/containerized_installer` (`stable-2.7`). Not yet validated on a live host.

Related files in this folder: [README.md](README.md) · [timeouts.md](timeouts.md) · [migration-2.6-to-2.7.md](migration-2.6-to-2.7.md). There's no RPM installer for 2.7. Other versions: [2.5](../../AAP25/containerized/service-order.md) · [2.6](../../AAP26/containerized/service-order.md).

---

## What changed vs 2.6

| Change | Effect on stop/start | Source |
|--------|----------------------|--------|
| **EDA workers moved from `rqworker` (Redis) to `dispatcherd`** (`aap-eda-manage dispatcherd --worker-class DefaultWorker\|ActivationWorker`) | EDA containers **no longer `Requires=redis-unix`** (`eda_container_requires: []`). Restarting `redis-unix` no longer bounces EDA. | `roles/automationeda/tasks/containers.yml`, `roles/automationeda/defaults/main.yml` |
| **`automation-eda-scheduler` container removed** | Don't include it in stop/start lists. If it's still listed in a 2.6 runbook, `systemctl` will just report the unit isn't found. On upgrade, the installer stops and disables the legacy unit, removes the container, and deletes the unit file. | `roles/automationeda/tasks/containers.yml`, `roles/automationeda/tasks/remove_scheduler.yml` (called from `tasks/main.yml:47`) |
| Everything else (Gateway, Controller, Hub, Redis, Lightspeed, MCP, Metrics, timers) | Same unit names and `Requires=` as 2.6 | — |

---

## TL;DR

| Action | Order |
|--------|-------|
| **Stop** | pcp → EDA → Gateway → Controller (drain first) → receptor (Controller, then execution/hop) → Hub → Lightspeed / MCP / Metrics → redis → postgresql |
| **Start** | postgresql → redis → receptor (execution/hop) → Hub → Controller → Gateway → EDA → Lightspeed / MCP / Metrics → pcp |
| **Restart one component** | Restart only that component's containers. **Don't** restart `postgresql` (any co-located app) or `redis-unix` (Controller / Hub) on a shared node unless you mean to bounce those too. |

The hard rules are **DB first up, last down** and **Redis before the apps**. The order between Gateway / Controller / Hub / EDA is a graceful-drain choice: stop new triggers (EDA), then ingress (Gateway), then let running jobs finish before stopping Controller.

All units are **rootless user units** under the install user: always `systemctl --user ...`, run as that user, never as root. Unit files live in `~/.config/systemd/user/`.

---

## Containers / units per component

| Component | Units (`systemctl --user`) |
|-----------|----------------------------|
| Gateway | `automation-gateway`, `automation-gateway-proxy` |
| Controller | `automation-controller-web`, `automation-controller-task`, `automation-controller-rsyslog` (+ timers `metrics-utility-gather.timer`, `metrics-utility-build-report.timer` if enabled) |
| Receptor | `receptor` (Controller nodes + execution/hop nodes) |
| Hub | `automation-hub-api`, `automation-hub-content`, `automation-hub-web`, `automation-hub-worker-{1..N}` |
| EDA | `automation-eda-api`, `automation-eda-daphne`, `automation-eda-web`, `automation-eda-worker-{1..N}`, `automation-eda-activation-worker-{1..N}` (**no scheduler**) |
| Redis | `redis-unix` (local socket, used by Controller/Hub), `redis-tcp` (Gateway / cluster) |
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
| `automation-hub-*` | `redis-unix` (+ `postgresql` if same node) |
| `automation-eda-*` | *(none — changed in 2.7)* (+ `postgresql` if same node) |
| `automation-gateway*`, Lightspeed, MCP, Metrics | *(none)* (+ `postgresql` if same node) |

systemd `Requires=` semantics:

- **Starting** a Controller or Hub container automatically starts `redis-unix` (and a local `postgresql`).
- **Stopping or restarting** `postgresql` or `redis-unix` **also stops or restarts every container on that node that requires it.**
  - Growth / all-in-one: `systemctl --user restart postgresql` bounces Controller, Hub, EDA, and Gateway.
  - `systemctl --user restart redis-unix` bounces Controller and Hub only (EDA and Gateway don't require it).
- EDA now depends on **PostgreSQL** for task dispatch (`dispatcherd`). With an external DB, EDA workers have no systemd dependency at all, so make sure the DB is reachable before starting EDA.

The installer's `backup.yml` / `restore.yml` don't do a global ordered stop/start. Each role handles its own containers.

---

## Recommended procedure

Enterprise topology: run each block on the matching nodes. Growth topology: run everything on the single host.

### Stop

```bash
systemctl --user stop pcp                                   # if monitoring configured
systemctl --user stop 'automation-eda-activation-worker-*' 'automation-eda-worker-*' \
                      automation-eda-daphne automation-eda-api automation-eda-web
systemctl --user stop automation-gateway automation-gateway-proxy
# drain Controller first (disable instances / wait for running jobs)
systemctl --user stop metrics-utility-gather.timer metrics-utility-build-report.timer 2>/dev/null
systemctl --user stop automation-controller-web automation-controller-task automation-controller-rsyslog
systemctl --user stop receptor                              # Controller nodes, then execution / hop nodes
systemctl --user stop automation-hub-api automation-hub-content 'automation-hub-worker-*' automation-hub-web
systemctl --user stop 'ansible-lightspeed*' ansiblemcp 'automation-metrics-*'   # if deployed
systemctl --user stop redis-unix redis-tcp                  # standalone: first gateway node; cluster: every [redis] node
systemctl --user stop postgresql                            # installer-managed DB only
```

### Start

```bash
systemctl --user start postgresql
systemctl --user start redis-tcp redis-unix
systemctl --user start receptor                 # execution / hop nodes, then Controller nodes
systemctl --user start automation-hub-api automation-hub-content automation-hub-web 'automation-hub-worker-*'
systemctl --user start automation-controller-rsyslog automation-controller-task automation-controller-web
systemctl --user start automation-gateway-proxy automation-gateway
systemctl --user start automation-eda-api automation-eda-daphne automation-eda-web \
                       'automation-eda-worker-*' 'automation-eda-activation-worker-*'
systemctl --user start 'ansible-lightspeed*' ansiblemcp 'automation-metrics-*'   # if deployed
systemctl --user start metrics-utility-gather.timer metrics-utility-build-report.timer 2>/dev/null
systemctl --user start pcp
curl -k https://<gateway>/api/gateway/v1/ping/   # verify
```

Glob patterns only match units that are **loaded**. If a worker glob matches nothing after a reboot, list the worker numbers explicitly (count = `hub_workers` / `eda_workers` / `eda_activation_workers`).

---

## Gaps / to verify on a live host

- After a 2.6 → 2.7 upgrade, confirm `remove_scheduler.yml` ran: there should be no `automation-eda-scheduler.service` in `~/.config/systemd/user/`.

```bash
systemctl --user show -p Requires -p After automation-eda-worker-1 automation-controller-task automation-hub-api
systemctl --user list-dependencies --reverse redis-unix
systemctl --user list-unit-files 'automation-eda-*'
```
