# AAP 2.5 — Containerized service stop / start / restart order

Personal TSE notes on the safe order to stop, start, and restart AAP containers on an **AAP 2.5 containerized** install, and the systemd `Requires=` coupling that makes order matter.

Verified against lab clone `aap-25/installer/containerized_installer` (`release_2.5`). Not yet validated on a live host.

Related files in this folder: [README.md](README.md). RPM equivalent: [../rpm/service-order.md](../rpm/service-order.md). Other versions: [2.6](../../AAP26/containerized/service-order.md) · [2.7](../../AAP27/containerized/service-order.md).

> **Same as 2.6, minus the newer components:** 2.5 has no Lightspeed, MCP, Automation Metrics service, or `metrics-utility` timers. Core container names and `Requires=` wiring match 2.6.

---

## TL;DR

| Action | Order |
|--------|-------|
| **Stop** | pcp → EDA → Gateway → Controller (drain first) → receptor (Controller, then execution/hop) → Hub → redis → postgresql |
| **Start** | postgresql → redis → receptor (execution/hop) → Hub → Controller → Gateway → EDA → pcp |
| **Restart one component** | Restart only that component's containers. **Don't** restart `postgresql` or `redis-unix` on a shared node unless you mean to bounce everything that requires them. |

The hard rules are **DB first up, last down** and **Redis before the apps**. The order between Gateway / Controller / Hub / EDA is a graceful-drain choice: stop new triggers (EDA), then ingress (Gateway), then let running jobs finish before stopping Controller.

All units are **rootless user units** under the install user: always `systemctl --user ...`, run as that user, never as root. Unit files live in `~/.config/systemd/user/`.

---

## Containers / units per component

| Component | Units (`systemctl --user`) |
|-----------|----------------------------|
| Gateway | `automation-gateway`, `automation-gateway-proxy` |
| Controller | `automation-controller-web`, `automation-controller-task`, `automation-controller-rsyslog` |
| Receptor | `receptor` (Controller nodes + execution/hop nodes) |
| Hub | `automation-hub-api`, `automation-hub-content`, `automation-hub-web`, `automation-hub-worker-{1..N}` |
| EDA | `automation-eda-api`, `automation-eda-daphne`, `automation-eda-web`, `automation-eda-scheduler`, `automation-eda-worker-{1..N}`, `automation-eda-activation-worker-{1..N}` |
| Redis | `redis-unix` (local socket, used by Controller/Hub/EDA), `redis-tcp` (Gateway / cluster) |
| Database | `postgresql` (only when installer-managed `[database]`) |
| Monitoring | `pcp` (if `setup_monitoring`) |

Handy: `systemctl --user list-units 'automation-*' 'redis-*' receptor postgresql pcp`

---

## systemd coupling — the gotchas

Each role builds its container's `Requires=` list (`roles/*/defaults/main.yml` + `roles/*/tasks/facts.yml`):

| Containers | `Requires=` |
|------------|-------------|
| `automation-controller-*` | `redis-unix` (+ `postgresql` **if `[database]` is on the same node**) |
| `automation-hub-*` | `redis-unix` (+ `postgresql` if same node) |
| `automation-eda-*` | `redis-unix` (+ `postgresql` if same node) |
| `automation-gateway*` | *(none)* (+ `postgresql` if same node) |

systemd `Requires=` semantics:

- **Starting** an app container automatically starts `redis-unix` (and a local `postgresql`).
- **Stopping or restarting** `postgresql` or `redis-unix` **also stops or restarts every container on that node that requires it.**
  - Growth / all-in-one: `systemctl --user restart postgresql` bounces Controller, Hub, EDA, and Gateway.
  - `systemctl --user restart redis-unix` bounces Controller, Hub, and EDA on that node (not Gateway).
- Gateway has no Redis `Requires=`. It uses `redis-tcp` / the Redis cluster over the network, so Redis must be up first, but systemd won't enforce it.

The installer's `backup.yml` / `restore.yml` don't do a global ordered stop/start. Each role's `backup.yml` / `restore.yml` handles its own containers.

For the Red Hat documented stop/start list (the *Migrate to containerized* procedure, which starts Redis last), see the [2.6 note](../../AAP26/containerized/service-order.md#what-red-hat-documents). The unit names are the same in 2.5.

---

## Recommended procedure

Enterprise topology: run each block on the matching nodes. Growth topology: run everything on the single host.

### Stop

```bash
systemctl --user stop pcp                                   # if monitoring configured
systemctl --user stop automation-eda-scheduler 'automation-eda-activation-worker-*' 'automation-eda-worker-*' \
                      automation-eda-daphne automation-eda-api automation-eda-web
systemctl --user stop automation-gateway automation-gateway-proxy
# drain Controller first (disable instances / wait for running jobs)
systemctl --user stop automation-controller-web automation-controller-task automation-controller-rsyslog
systemctl --user stop receptor                              # Controller nodes, then execution / hop nodes
systemctl --user stop automation-hub-api automation-hub-content 'automation-hub-worker-*' automation-hub-web
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
systemctl --user start automation-eda-api automation-eda-daphne automation-eda-web automation-eda-scheduler \
                       'automation-eda-worker-*' 'automation-eda-activation-worker-*'
systemctl --user start pcp
curl -k https://<gateway>/api/gateway/v1/ping/   # verify
```

Glob patterns only match units that are **loaded**. If a worker glob matches nothing after a reboot, list the worker numbers explicitly (count = `hub_workers` / `eda_workers` / `eda_activation_workers`).

---

## Gaps / to verify on a live host

```bash
systemctl --user show -p Requires -p After automation-controller-task automation-gateway automation-hub-api
systemctl --user list-dependencies --reverse redis-unix
systemctl --user list-dependencies --reverse postgresql
```
