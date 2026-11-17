# AAP 2.6 — RPM service stop / start / restart order

Personal TSE notes on the safe order to stop, start, and restart AAP services on an **AAP 2.6 RPM** install, and the systemd coupling that makes order matter.

Verified against lab clone `aap-26/installer/rpm_installer` (`stable-2.6`). Not yet validated on a live host.

Related files in this folder: [README.md](README.md) · [install-playbook-tasks.md](install-playbook-tasks.md). Containerized equivalent: [../containerized/service-order.md](../containerized/service-order.md). Other versions: [2.4 RPM](../../AAP24/rpm/service-order.md) · [2.5 RPM](../../AAP25/rpm/service-order.md).

---

## TL;DR

| Action | Order |
|--------|-------|
| **Stop** | EDA → Gateway → Controller (drain first) → Hub → Redis → receptor on execution/hop nodes → external PostgreSQL |
| **Start** | PostgreSQL → Redis → receptor on execution/hop nodes → Hub → Controller → Gateway → EDA |
| **Restart one component** | Use that component's wrapper. Watch out for the `PartOf=` coupling below (an internal DB goes down with it). |

The hard rules are **DB first up, last down** and **Redis before the apps**. The order *between* Gateway / Controller / Hub / EDA isn't enforced by systemd. The order above is chosen to drain work gracefully: stop new triggers (EDA), then ingress (Gateway), then let running jobs finish before stopping Controller.

---

## Service wrappers / units per component

| Component | Control command | Underlying units |
|-----------|-----------------|------------------|
| Controller | `automation-controller-service start\|stop\|restart\|status` | `automation-controller.service` plus `$CONTROLLER_SERVICES` from `/etc/sysconfig/automation-controller`: `redis`, `nginx`, `supervisord`, `receptor` (+ `postgresql` if the DB is internal) |
| Gateway | `automation-gateway-service start\|stop` | `automation-gateway.target` → `nginx`, `supervisord`, `automation-gateway-proxy` (+ `postgresql` if internal) |
| EDA | `automation-eda-controller-service start\|stop` | `<eda>.target` → EDA units, `nginx` (workers) |
| Hub | *(no wrapper)* `systemctl stop pulpcore-api pulpcore-content 'pulpcore-worker@*' nginx` | api / content / workers are `PartOf=pulpcore.service` |
| Redis (standalone) | `systemctl stop\|start redis` | runs on the **first** `[automationgateway]` host |
| Redis (cluster) | `systemctl stop\|start redis-platform` | every `[redis]` host |
| Execution / hop | `systemctl stop\|start receptor` | — |

`automation-controller-service` source (controller repo `tools/scripts/automation-controller-service`): `start|stop|restart` just runs `systemctl <action> automation-controller.service`. The other units follow because of the `PartOf=` overrides below. `status`/`enable`/`disable` also act on `$CONTROLLER_SERVICES`.

---

## systemd coupling — the gotchas

The installer drops `PartOf=` overrides, so **stopping or restarting the parent also stops or restarts the child**:

| Parent | Children (`PartOf=`) | Source |
|--------|----------------------|--------|
| `automation-controller.service` | `nginx`, `supervisord`, `redis`, **local `postgresql`** | `roles/automationcontroller/files/override.conf`, applied in `roles/automationcontroller/tasks/tasks.yml:99-114` |
| `automation-controller.service` | `receptor` (Controller nodes only) | `roles/receptor/templates/systemd_receptor_override.conf.j2` |
| `automation-gateway.target` | `nginx`, `supervisord`, internal `postgresql`; target also has `Wants=/After=postgresql.service` | `roles/automationgateway/tasks/main.yml:66-82`, `roles/systemd/templates/override.conf.j2`, `roles/systemd/files/override-internal-postgresql.conf` |
| `<eda>.target` | EDA worker units (+ `Wants=nginx`) | `roles/automationedacontroller/templates/override-automationedacontroller.conf.j2` |
| `pulpcore.service` | `pulpcore-api`, `pulpcore-content`, `pulpcore-worker@N` | `roles/automationhub/templates/pulpcore-*.service.j2` |

What this means in practice:

- **Internal DB on a Controller node:** `automation-controller-service stop` **also stops PostgreSQL**. Gateway, Hub, and EDA lose their database if they share it. That's why the installer's own `restore.yml` starts postgres again straight after stopping Controller (`playbooks/restore.yml:93-97`).
- **Shared nodes / all-in-one:** `nginx` and `supervisord` are shared. Stopping one component's wrapper can stop the shared `nginx`/`supervisord` under the other components on the same host.
- **Starting Gateway** pulls in an internal postgres through `Wants=`.

---

## What the installer itself does

`playbooks/restore.yml` (a full outage, not a graceful drain):

| Step | Stop (`:86-198`) | Start (`:264-385`) |
|------|------------------|--------------------|
| 1 | `automation-controller-service stop` (all Controller nodes) | `automation-controller-service start` |
| 2 | Hub: `pulpcore-api`, `pulpcore-content`, running `pulpcore-worker@*`, `nginx` | `redis-platform` (if clustered) |
| 3 | `automation-eda-controller-service stop` | Hub services |
| 4 | `automation-gateway-service stop` | `automation-eda-controller-service start` |
| 5 | `redis` on first gateway (standalone) / `redis-platform` (clustered) | `redis` on first gateway (standalone) |
| 6 | — | `automation-gateway-service start`, then poll `/api/gateway/v1/ping/` until 200 |

---

## Recommended procedure

### Stop

```bash
# 1. EDA nodes — stop activations from launching new jobs
automation-eda-controller-service stop

# 2. Gateway nodes — cut user/API traffic
automation-gateway-service stop

# 3. Controller nodes — first drain: disable instances / wait for running jobs to finish
automation-controller-service stop        # NOTE: also stops an internal postgresql on this node

# 4. Hub nodes
systemctl stop pulpcore-api pulpcore-content 'pulpcore-worker@*' nginx

# 5. Redis
systemctl stop redis            # standalone: first [automationgateway] host
systemctl stop redis-platform   # cluster: every [redis] host

# 6. Execution / hop nodes
systemctl stop receptor

# 7. External / dedicated [database] host (if installer-managed)
systemctl stop postgresql
```

### Start

```bash
systemctl start postgresql                     # [database] host
systemctl start redis-platform                 # [redis] hosts (cluster)  -- or --
systemctl start redis                          # first gateway host (standalone)
systemctl start receptor                       # execution / hop nodes
systemctl start pulpcore-api pulpcore-content 'pulpcore-worker@*' nginx   # hub
automation-controller-service start            # controller
automation-gateway-service start               # gateway
automation-eda-controller-service start        # eda
curl -k https://<gateway>/api/gateway/v1/ping/ # verify
```

Starting Gateway before EDA means activations that restart can reach Controller and Hub through Gateway. The installer starts EDA before Gateway and that works, so this is a preference, not a requirement.

---

## Gaps / to verify on a live host

- The base `.service`/`.target` files and the `automation-gateway-service` / `automation-eda-controller-service` scripts ship in RPMs and **aren't in the installer source**. Only the installer overrides were reviewed. Check with:
  ```bash
  systemctl list-dependencies automation-gateway.target
  systemctl list-dependencies automation-controller.service
  systemctl show -p PartOf nginx supervisord redis postgresql receptor
  ```
- There are no metrics-utility timers on RPM. Those are containerized-only.
