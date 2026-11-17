# AAP 2.4 — RPM service stop / start / restart order

Personal TSE notes on the safe order to stop, start, and restart AAP services on an **AAP 2.4 RPM** install, and the systemd coupling that makes order matter.

Verified against lab clone `aap-24/installer/rpm_installer` (`release_2.4`). Not yet validated on a live host.

Related files in this folder: [README.md](README.md) · [install-playbook-tasks.md](install-playbook-tasks.md). Later versions: [2.5 RPM](../../AAP25/rpm/service-order.md) · [2.6 RPM](../../AAP26/rpm/service-order.md).

---

## How 2.4 differs from 2.5+

- **No platform gateway.** Controller, Hub, and EDA each serve their own UI/API through local `nginx`. There's no `automation-gateway-service`.
- **No platform Redis** (`[redis]` group / `redis-platform`). Each component node runs a **local `redis`** on a unix socket (Hub: `unix:///var/run/redis/redis.sock`, `roles/automationhub/tasks/main.yml:143`).
- **No `automation-eda-controller-service` wrapper.** EDA is controlled through `automation-eda-controller.target`.
- **Optional `[sso]` group:** RH-SSO (Keycloak) for Hub. The unit is `rh-sso7` (`roles/sso/defaults/main.yml: sso_app_name`).

---

## TL;DR

| Action | Order |
|--------|-------|
| **Stop** | EDA → Controller (drain first) → Hub → SSO → receptor on execution/hop nodes → external PostgreSQL |
| **Start** | PostgreSQL → receptor on execution/hop nodes → SSO → Hub → Controller → EDA |
| **Restart one component** | Use that component's command. Watch out for `PartOf=`: an internal DB on the Controller node goes down with Controller. |

The hard rule is **DB first up, last down**. The order between components is a graceful-drain choice: stop EDA so rulebooks stop launching jobs, then drain Controller. On 2.4, EDA → Controller and Hub → Controller traffic goes direct (no gateway), so start Hub before Controller (EE pulls) and Controller before EDA.

---

## Service commands / units per component

| Component | Control command | Underlying units |
|-----------|-----------------|------------------|
| Controller | `automation-controller-service start\|stop\|restart\|status` | `automation-controller.service` + `$CONTROLLER_SERVICES` from `/etc/sysconfig/automation-controller`: `redis`, `nginx`, `supervisord`, `receptor` (+ `postgresql` if internal) |
| Hub | `systemctl stop pulpcore-api pulpcore-content 'pulpcore-worker@*' nginx` | api / content / workers are `PartOf=pulpcore.service` |
| EDA | `systemctl stop\|start automation-eda-controller.target nginx` | `automation-eda-controller`, `automation-eda-controller-daphne`, `automation-eda-controller-scheduler` (EDA ≥ 1.0.3), `automation-eda-controller-worker@N`, `automation-eda-controller-activation-worker@N` (≥ 1.0.3) (`roles/automationedacontroller/tasks/main.yml:42-48`, `workers.yml`) |
| SSO | `systemctl stop\|start rh-sso7` | RH-SSO / Keycloak (JBoss) |
| Execution / hop | `systemctl stop\|start receptor` | — |

---

## systemd coupling — the gotchas

| Parent | Children (`PartOf=`) | Source |
|--------|----------------------|--------|
| `automation-controller.service` | `nginx`, `supervisord`, `redis`, **local `postgresql`** | `roles/automationcontroller/files/override.conf` (same as 2.5/2.6) |
| `automation-controller.service` | `receptor` (Controller nodes only) | `roles/receptor/templates/systemd_receptor_override.conf.j2` |
| `pulpcore.service` | `pulpcore-api`, `pulpcore-content`, `pulpcore-worker@N` | `roles/automationhub/templates/pulpcore-*.service.j2` |

- **Internal DB on the Controller node:** `automation-controller-service stop` **also stops PostgreSQL**, and Hub and EDA lose their database if they share it. The installer's `restore.yml:58-69` restarts postgres on the primary straight away for exactly this reason.
- **Shared nodes:** `nginx` and `redis` are shared by every component on a host. Stopping Controller stops them under Hub or EDA if they're co-located.
- Unlike 2.5+, there are no `automation-gateway.target` or EDA `.target.d` postgres overrides in 2.4.

---

## What the installer itself does

`playbooks/restore.yml` (a full outage, not a graceful drain):

| Step | Stop | Start |
|------|------|-------|
| 1 | `automation-controller-service stop` (then postgres started again on primary if internal) | `automation-controller-service start` |
| 2 | Hub: `pulpcore-api`, `pulpcore-content`, running `pulpcore-worker@*`, `nginx` | Hub services |
| 3 | EDA: `automation-eda-controller.target`, `nginx` | EDA: same list |

SSO isn't stopped or started by `restore.yml`.

---

## Recommended procedure

### Stop

```bash
# 1. EDA nodes
systemctl stop automation-eda-controller.target nginx

# 2. Controller nodes — first drain: disable instances / wait for running jobs
automation-controller-service stop        # NOTE: also stops an internal postgresql on this node

# 3. Hub nodes
systemctl stop pulpcore-api pulpcore-content 'pulpcore-worker@*' nginx

# 4. SSO node (if [sso] is deployed)
systemctl stop rh-sso7

# 5. Execution / hop nodes
systemctl stop receptor

# 6. External / dedicated [database] host (if installer-managed)
systemctl stop postgresql
```

### Start

```bash
systemctl start postgresql                     # [database] host
systemctl start receptor                       # execution / hop nodes
systemctl start rh-sso7                        # sso (if deployed)
systemctl start pulpcore-api pulpcore-content 'pulpcore-worker@*' nginx   # hub
automation-controller-service start            # controller
systemctl start automation-eda-controller.target nginx                    # eda
```

---

## Gaps / to verify on a live host

- The base unit files ship in RPMs. Only the installer overrides were reviewed.
- Confirm the SSO unit name. `rh-sso7` comes from `sso_app_name` and could be overridden in the inventory.
  ```bash
  systemctl list-dependencies automation-controller.service
  systemctl list-dependencies automation-eda-controller.target
  systemctl show -p PartOf nginx supervisord redis postgresql receptor
  ```
