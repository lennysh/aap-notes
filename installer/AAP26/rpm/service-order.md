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

## Ansible playbook (installer inventory)

Save as `aap-services.yml` and run it with the **same inventory file you used for `setup.sh`**. It uses `become: true`.

```bash
ansible-playbook -i inventory aap-services.yml -e aap_action=stop
ansible-playbook -i inventory aap-services.yml -e aap_action=start
ansible-playbook -i inventory aap-services.yml -e aap_action=restart
# only some components (order is still enforced), e.g.:
ansible-playbook -i inventory aap-services.yml -e aap_action=restart -e '{"aap_components": ["hub"]}'
```

Components: `eda gateway controller hub redis receptor database`.

| Step | Hosts it acts on |
|------|------------------|
| Platform Redis | `redis_mode=cluster` (installer default): `redis-platform` on every `[redis]` host. `redis_mode=standalone`: `redis` on the first `[automationgateway]` host. |
| `postgresql` | `[database]` hosts, or the first `[automationcontroller]` host when there's no `[database]` group (installer-managed internal DB). That DB **starts first**, before Hub / Gateway need it. |
| Controller / Gateway / EDA | `automation-controller-service`, `automation-gateway-service`, `automation-eda-controller-service` on their groups |
| Hub | discovered `pulpcore-api`, `pulpcore-content`, `pulpcore-worker@N` + `nginx` on `[automationhub]` |
| `receptor` | `[execution_nodes]` (Controller's receptor follows the Controller wrapper) |

- It uses the same commands as the installer's own `playbooks/restore.yml` (service wrappers plus Hub `pulpcore-*` units), reordered for a graceful drain.
- Hub `pulpcore-worker@N` instances and the PostgreSQL unit name (`postgresql` or `postgresql-NN`) are discovered per host.
- Each step is its own task under the default `linear` strategy, so it **finishes on every host before the next step starts**.
- `restart` is a full ordered stop, then a full ordered start.
- After a start, it polls `https://<first gateway>:{{ automationgateway_https_port | default(8443) }}/api/gateway/v1/ping/` (the same admin URL the installer's `restore.yml` checks). Use `-e aap_verify=false` to skip that, or `-e aap_ping_url=...` to override the URL.
- It does **not** drain Controller. Disable instances / wait for jobs before `stop` or `restart`.
- Limiting to `controller` with an internal DB on the Controller node still stops PostgreSQL (it's `PartOf=automation-controller.service`), so Gateway / Hub / EDA lose their DB until Controller is back.
- Tested with `ansible-lint` (production profile) and against simulated hosts with a fake `systemctl`, checking step order, Redis cluster vs standalone targeting, and component limiting. **Not yet run against a real AAP install.**

<details>
<summary><code>aap-services.yml</code> (RPM 2.5 / 2.6)</summary>

```yaml
---
# aap-services.yml: ordered stop / start / restart of AAP RPM services (2.5 / 2.6).
# Run with the SAME inventory file used for setup.sh.
#
#   ansible-playbook -i inventory aap-services.yml -e aap_action=stop
#   ansible-playbook -i inventory aap-services.yml -e aap_action=start
#   ansible-playbook -i inventory aap-services.yml -e aap_action=restart
#   # limit to components (order is still enforced):
#   ansible-playbook -i inventory aap-services.yml -e aap_action=restart -e '{"aap_components": ["hub"]}'
#
# Components: eda gateway controller hub redis receptor database
#
# Mirrors the installer's own playbooks/restore.yml (wrappers + pulpcore units),
# reordered for a graceful drain. Platform Redis follows redis_mode from the inventory:
#   cluster (default) -> redis-platform on every host in [redis]
#   standalone        -> redis on the first [automationgateway] host
# Controller's local redis/nginx/supervisord/receptor (and an internal postgresql) are
# PartOf automation-controller.service and stop/start with the controller wrapper.
#
# Skip the post-start ping with -e aap_verify=false; override its URL with -e aap_ping_url=...
# Drain Controller (disable instances / wait for running jobs) BEFORE aap_action=stop|restart.

- name: "AAP RPM services: {{ aap_action | default('UNSET') }}"
  hosts: automationgateway:automationcontroller:automationhub:automationedacontroller:execution_nodes:redis:database
  gather_facts: false
  become: true
  any_errors_fatal: true
  vars:
    aap_components: [all]
    _all_components: [eda, gateway, controller, hub, redis, receptor, database]
    _components: "{{ _all_components if 'all' in aap_components else aap_components }}"
    _stopping: "{{ aap_action in ['stop', 'restart'] }}"
    _starting: "{{ aap_action in ['start', 'restart'] }}"
    _first_gateway: "{{ groups.get('automationgateway', []) | first | default('') }}"
    _first_controller: "{{ groups.get('automationcontroller', []) | first | default('') }}"
    _redis_cluster: "{{ (redis_mode | default('cluster')) == 'cluster' }}"
    _redis_unit: "{{ 'redis-platform.service' if _redis_cluster else 'redis.service' }}"
    _redis_host: >-
      {{ (inventory_hostname in groups.get('redis', [])) if _redis_cluster
         else (inventory_hostname == _first_gateway) }}
    # [database] hosts, plus an installer-managed DB on the first controller (no [database] group)
    _db_host: >-
      {{ inventory_hostname in groups.get('database', [])
         or (groups.get('database', []) | length == 0 and inventory_hostname == _first_controller) }}
    _in_eda: "{{ inventory_hostname in groups.get('automationedacontroller', []) }}"
    _in_gateway: "{{ inventory_hostname in groups.get('automationgateway', []) }}"
    _in_controller: "{{ inventory_hostname in groups.get('automationcontroller', []) }}"
    _in_hub: "{{ inventory_hostname in groups.get('automationhub', []) }}"
    _in_exec: "{{ inventory_hostname in groups.get('execution_nodes', []) }}"

  tasks:
    - name: Validate input
      ansible.builtin.assert:
        that:
          - aap_action is defined
          - aap_action in ['stop', 'start', 'restart']
          - aap_components | difference(_all_components + ['all']) | length == 0
        fail_msg: "Pass -e aap_action=stop|start|restart; aap_components must be a subset of {{ _all_components }}"

    - name: Discover systemd units on this host
      ansible.builtin.shell: |
        set -o pipefail
        { systemctl list-unit-files --no-legend --plain --type=service
          systemctl list-units --all --no-legend --plain --type=service
        } | awk '{print $1}' | grep -v '@\.' | sort -u
      args:
        executable: /bin/bash
      register: _unit_list
      changed_when: false

    - name: Set unit facts
      ansible.builtin.set_fact:
        _hub_units: "{{ _unit_list.stdout_lines | select('match', '^pulpcore-(api|content|worker@[0-9]+)\\.service$') | list }}"
        _pg_units: "{{ _unit_list.stdout_lines | select('match', '^postgresql(-[0-9]+)?\\.service$') | list }}"
        _has_receptor: "{{ 'receptor.service' in _unit_list.stdout_lines }}"

    # ------------------------------------------------------------------ STOP
    - name: "Stop | eda"
      ansible.builtin.command: automation-eda-controller-service stop
      changed_when: true
      when: _stopping and 'eda' in _components and _in_eda | bool

    - name: "Stop | gateway"
      ansible.builtin.command: automation-gateway-service stop
      changed_when: true
      when: _stopping and 'gateway' in _components and _in_gateway | bool

    - name: "Stop | controller (also stops PartOf redis/nginx/supervisord/receptor/internal postgresql)"
      ansible.builtin.command: automation-controller-service stop
      changed_when: true
      when: _stopping and 'controller' in _components and _in_controller | bool

    - name: "Stop | hub (pulpcore api/content/workers, nginx)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped}
      loop: "{{ _hub_units + ['nginx.service'] }}"
      when: _stopping and 'hub' in _components and _in_hub | bool

    - name: "Stop | platform redis ([redis] group if cluster, first gateway if standalone)"
      ansible.builtin.systemd: {name: "{{ _redis_unit }}", state: stopped}
      when: _stopping and 'redis' in _components and _redis_host | bool

    - name: "Stop | receptor (execution/hop nodes)"
      ansible.builtin.systemd: {name: receptor.service, state: stopped}
      when: _stopping and 'receptor' in _components and _in_exec | bool and _has_receptor | bool

    - name: "Stop | postgresql"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped}
      loop: "{{ _pg_units }}"
      when: _stopping and 'database' in _components and _db_host | bool

    # ----------------------------------------------------------------- START
    - name: "Start | postgresql"
      ansible.builtin.systemd: {name: "{{ item }}", state: started}
      loop: "{{ _pg_units }}"
      when: _starting and 'database' in _components and _db_host | bool

    - name: "Start | platform redis ([redis] group if cluster, first gateway if standalone)"
      ansible.builtin.systemd: {name: "{{ _redis_unit }}", state: started}
      when: _starting and 'redis' in _components and _redis_host | bool

    - name: "Start | receptor (execution/hop nodes)"
      ansible.builtin.systemd: {name: receptor.service, state: started}
      when: _starting and 'receptor' in _components and _in_exec | bool and _has_receptor | bool

    - name: "Start | hub (pulpcore api/content/workers, nginx)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started}
      loop: "{{ _hub_units + ['nginx.service'] }}"
      when: _starting and 'hub' in _components and _in_hub | bool

    - name: "Start | controller"
      ansible.builtin.command: automation-controller-service start
      changed_when: true
      when: _starting and 'controller' in _components and _in_controller | bool

    - name: "Start | gateway"
      ansible.builtin.command: automation-gateway-service start
      changed_when: true
      when: _starting and 'gateway' in _components and _in_gateway | bool

    - name: "Start | eda"
      ansible.builtin.command: automation-eda-controller-service start
      changed_when: true
      when: _starting and 'eda' in _components and _in_eda | bool

    - name: "Start | verify platform gateway ping"
      ansible.builtin.uri:
        url: "{{ aap_ping_url | default('https://' ~ inventory_hostname ~ ':' ~ (automationgateway_https_port | default(8443)) ~ '/api/gateway/v1/ping/') }}"
        validate_certs: false
      register: _ping
      until: _ping.status == 200
      retries: 20
      delay: 15
      when: _starting and aap_verify | default(true) | bool and 'gateway' in _components and inventory_hostname == _first_gateway
```

</details>

---

## Gaps / to verify on a live host

- The base `.service`/`.target` files and the `automation-gateway-service` / `automation-eda-controller-service` scripts ship in RPMs and **aren't in the installer source**. Only the installer overrides were reviewed. Check with:
  ```bash
  systemctl list-dependencies automation-gateway.target
  systemctl list-dependencies automation-controller.service
  systemctl show -p PartOf nginx supervisord redis postgresql receptor
  ```
- There are no metrics-utility timers on RPM. Those are containerized-only.
