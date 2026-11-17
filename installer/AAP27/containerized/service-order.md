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
| Redis | `redis-unix`: local socket on **every Controller and Hub node** (no longer on EDA nodes in 2.7). `redis-tcp`: every `[redis]` host (`redis_mode=cluster`, the default) or the first `[automationgateway]` host (`redis_mode=standalone`). |
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
systemctl --user stop redis-unix                            # every Controller / Hub node
systemctl --user stop redis-tcp                             # cluster: every [redis] node; standalone: first gateway node
systemctl --user stop postgresql                            # installer-managed DB only
```

### Start

```bash
systemctl --user start postgresql
systemctl --user start redis-tcp                # cluster: every [redis] node; standalone: first gateway node
systemctl --user start redis-unix               # every Controller / Hub node
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

## Ansible playbook (installer inventory)

Save as `aap-services.yml` and run it with the **same inventory file you used for the installer**, as the install user. It uses `become: false` and `systemctl --user` units, just like the installer.

```bash
ansible-playbook -i inventory aap-services.yml -e aap_action=stop
ansible-playbook -i inventory aap-services.yml -e aap_action=start
ansible-playbook -i inventory aap-services.yml -e aap_action=restart
# only some components (order is still enforced), e.g.:
ansible-playbook -i inventory aap-services.yml -e aap_action=restart -e '{"aap_components": ["controller", "receptor"]}'
```

Components: `pcp eda gateway controller receptor hub lightspeed mcp metrics redis database`.

| Step | Hosts it acts on |
|------|------------------|
| `redis-tcp` | `redis_mode=cluster` (installer default): every `[redis]` host. `redis_mode=standalone`: first `[automationgateway]` host. |
| `redis-unix` | Any host that has it: every Controller and Hub node (EDA no longer uses it in 2.7) |
| `postgresql` | `[database]` hosts only |
| Everything else | Whatever matching units exist on each host, found with `systemctl --user list-unit-files` / `list-units` |

- **Same playbook for 2.5 / 2.6 / 2.7.** Because units are discovered per host, version differences (no `automation-eda-scheduler` in 2.7, no Lightspeed/MCP/Metrics in 2.5) need no edits, and co-located (growth) hosts just work.
- Each step is its own task under the default `linear` strategy, so it **finishes on every host before the next step starts**. Within a step, hosts run in parallel.
- `restart` is a full ordered stop, then a full ordered start. It is *not* `systemctl restart`.
- `metrics-utility-*` is handled through its `.timer` units only. The oneshot `.service` units are never started directly.
- After a start, it polls `https://<first gateway>:{{ envoy_https_port | default(443) }}/api/gateway/v1/ping/`. Use `-e aap_verify=false` to skip that, or `-e aap_ping_url=...` to override the URL.
- It does **not** drain Controller. Disable instances / wait for jobs before `stop` or `restart`.
- `Requires=` still applies when you limit components: starting Controller or Hub pulls up `redis-unix` (and a local `postgresql`), and stopping the `redis` or `database` component stops whatever requires them on that node.
- Tested with `ansible-lint` (production profile) and against simulated hosts with a fake `systemctl`, checking step order, Redis cluster vs standalone targeting, and component limiting. **Not yet run against a real AAP install.**

<details>
<summary><code>aap-services.yml</code> (containerized)</summary>

```yaml
---
# aap-services.yml: ordered stop / start / restart of AAP containerized services
# (2.5 / 2.6 / 2.7). Run with the SAME inventory file used for the installer.
#
#   ansible-playbook -i inventory aap-services.yml -e aap_action=stop
#   ansible-playbook -i inventory aap-services.yml -e aap_action=start
#   ansible-playbook -i inventory aap-services.yml -e aap_action=restart
#   # limit to components (order is still enforced):
#   ansible-playbook -i inventory aap-services.yml -e aap_action=restart -e '{"aap_components": ["controller", "receptor"]}'
#
# Components: pcp eda gateway controller receptor hub lightspeed mcp metrics redis database
#
# Units are discovered per host (systemctl --user list-unit-files / list-units),
# so the same playbook works across 2.5 / 2.6 / 2.7 and only touches units that
# exist (e.g. no eda-scheduler in 2.7, no lightspeed/mcp/metrics in 2.5).
# Redis TCP follows redis_mode from the inventory:
#   cluster (default) -> redis-tcp on every host in [redis]
#   standalone        -> redis-tcp on the first [automationgateway] host
# redis-unix is stopped/started wherever it exists (Controller/Hub nodes, single-node EDA in 2.5/2.6).
#
# Skip the post-start ping with -e aap_verify=false; override its URL with -e aap_ping_url=...
# Drain Controller (disable instances / wait for running jobs) BEFORE aap_action=stop|restart.

- name: "AAP containerized services: {{ aap_action | default('UNSET') }}"
  hosts: automationgateway:automationcontroller:automationhub:automationeda:execution_nodes:redis:database:ansiblelightspeed:ansiblemcp:automationmetrics
  gather_facts: false
  become: false
  any_errors_fatal: true
  vars:
    aap_components: [all]
    _all_components: [pcp, eda, gateway, controller, receptor, hub, lightspeed, mcp, metrics, redis, database]
    _components: "{{ _all_components if 'all' in aap_components else aap_components }}"
    _stopping: "{{ aap_action in ['stop', 'restart'] }}"
    _starting: "{{ aap_action in ['start', 'restart'] }}"
    _redis_cluster: "{{ (redis_mode | default('cluster')) == 'cluster' }}"
    _redis_tcp_host: >-
      {{ (inventory_hostname in groups.get('redis', [])) if _redis_cluster
         else (inventory_hostname == (groups.get('automationgateway', []) | first | default(''))) }}
    _patterns:
      pcp: '^pcp\.service$'
      eda: '^automation-eda-.+\.service$'
      gateway: '^automation-gateway(-proxy)?\.service$'
      controller: '^automation-controller-.+\.service$'
      controller_timers: '^metrics-utility-.+\.timer$'
      receptor: '^receptor\.service$'
      hub: '^automation-hub-.+\.service$'
      lightspeed: '^ansible-lightspeed.*\.service$'
      mcp: '^ansiblemcp\.service$'
      metrics: '^automation-metrics-.+\.service$'
      redis_unix: '^redis-unix\.service$'
      redis_tcp: '^redis-tcp\.service$'
      database: '^postgresql\.service$'

  tasks:
    - name: Validate input
      ansible.builtin.assert:
        that:
          - aap_action is defined
          - aap_action in ['stop', 'start', 'restart']
          - aap_components | difference(_all_components + ['all']) | length == 0
        fail_msg: "Pass -e aap_action=stop|start|restart; aap_components must be a subset of {{ _all_components }}"

    - name: Discover systemd user units on this host
      ansible.builtin.shell: |
        set -o pipefail
        { systemctl --user list-unit-files --no-legend --plain --type=service,timer
          systemctl --user list-units --all --no-legend --plain --type=service,timer
        } | awk '{print $1}' | grep -v '@\.' | sort -u
      args:
        executable: /bin/bash
      register: _unit_list
      changed_when: false

    - name: Set unit list
      ansible.builtin.set_fact:
        _units: "{{ _unit_list.stdout_lines }}"

    # ------------------------------------------------------------------ STOP
    - name: "Stop | pcp"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.pcp) | list }}"
      when: _stopping and 'pcp' in _components

    - name: "Stop | eda"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.eda) | list }}"
      when: _stopping and 'eda' in _components

    - name: "Stop | gateway"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.gateway) | list }}"
      when: _stopping and 'gateway' in _components

    - name: "Stop | controller (metrics-utility timers, then containers)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ (_units | select('match', _patterns.controller_timers) | list) + (_units | select('match', _patterns.controller) | list) }}"
      when: _stopping and 'controller' in _components

    - name: "Stop | receptor (controller + execution/hop nodes)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.receptor) | list }}"
      when: _stopping and 'receptor' in _components

    - name: "Stop | hub"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.hub) | list }}"
      when: _stopping and 'hub' in _components

    - name: "Stop | lightspeed / mcp / metrics"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: >-
        {{ ((_units | select('match', _patterns.lightspeed) | list) if 'lightspeed' in _components else [])
         + ((_units | select('match', _patterns.mcp) | list) if 'mcp' in _components else [])
         + ((_units | select('match', _patterns.metrics) | list) if 'metrics' in _components else []) }}
      when: _stopping

    - name: "Stop | redis-unix (local socket on component nodes)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.redis_unix) | list }}"
      when: _stopping and 'redis' in _components

    - name: "Stop | redis-tcp ([redis] group if cluster, first gateway if standalone)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.redis_tcp) | list }}"
      when: _stopping and 'redis' in _components and _redis_tcp_host | bool

    - name: "Stop | postgresql ([database] group)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped, scope: user}
      loop: "{{ _units | select('match', _patterns.database) | list }}"
      when: _stopping and 'database' in _components and inventory_hostname in groups.get('database', [])

    # ----------------------------------------------------------------- START
    - name: "Start | postgresql ([database] group)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.database) | list }}"
      when: _starting and 'database' in _components and inventory_hostname in groups.get('database', [])

    - name: "Start | redis-tcp ([redis] group if cluster, first gateway if standalone)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.redis_tcp) | list }}"
      when: _starting and 'redis' in _components and _redis_tcp_host | bool

    - name: "Start | redis-unix (local socket on component nodes)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.redis_unix) | list }}"
      when: _starting and 'redis' in _components

    - name: "Start | receptor (controller + execution/hop nodes)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.receptor) | list }}"
      when: _starting and 'receptor' in _components

    - name: "Start | hub"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.hub) | list }}"
      when: _starting and 'hub' in _components

    - name: "Start | controller (containers, then metrics-utility timers)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ (_units | select('match', _patterns.controller) | list) + (_units | select('match', _patterns.controller_timers) | list) }}"
      when: _starting and 'controller' in _components

    - name: "Start | gateway"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.gateway) | list }}"
      when: _starting and 'gateway' in _components

    - name: "Start | eda"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.eda) | list }}"
      when: _starting and 'eda' in _components

    - name: "Start | lightspeed / mcp / metrics"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: >-
        {{ ((_units | select('match', _patterns.lightspeed) | list) if 'lightspeed' in _components else [])
         + ((_units | select('match', _patterns.mcp) | list) if 'mcp' in _components else [])
         + ((_units | select('match', _patterns.metrics) | list) if 'metrics' in _components else []) }}
      when: _starting

    - name: "Start | pcp"
      ansible.builtin.systemd: {name: "{{ item }}", state: started, scope: user}
      loop: "{{ _units | select('match', _patterns.pcp) | list }}"
      when: _starting and 'pcp' in _components

    - name: "Start | verify platform gateway ping"
      ansible.builtin.uri:
        url: "{{ aap_ping_url | default('https://' ~ inventory_hostname ~ ':' ~ (envoy_https_port | default(443)) ~ '/api/gateway/v1/ping/') }}"
        validate_certs: false
      register: _ping
      until: _ping.status == 200
      retries: 20
      delay: 15
      when:
        - _starting
        - aap_verify | default(true) | bool
        - "'gateway' in _components"
        - inventory_hostname == (groups.get('automationgateway', []) | first | default(''))
```

</details>

---

## Gaps / to verify on a live host

- After a 2.6 → 2.7 upgrade, confirm `remove_scheduler.yml` ran: there should be no `automation-eda-scheduler.service` in `~/.config/systemd/user/`.

```bash
systemctl --user show -p Requires -p After automation-eda-worker-1 automation-controller-task automation-hub-api
systemctl --user list-dependencies --reverse redis-unix
systemctl --user list-unit-files 'automation-eda-*'
```
