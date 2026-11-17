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

## Ansible playbook (installer inventory)

Save as `aap-services.yml` and run it with the **same inventory file you used for `setup.sh`**. It uses `become: true`.

```bash
ansible-playbook -i inventory aap-services.yml -e aap_action=stop
ansible-playbook -i inventory aap-services.yml -e aap_action=start
ansible-playbook -i inventory aap-services.yml -e aap_action=restart
# only some components (order is still enforced), e.g.:
ansible-playbook -i inventory aap-services.yml -e aap_action=restart -e '{"aap_components": ["eda"]}'
```

Components: `eda controller hub sso redis receptor database`.

| Step | Hosts it acts on |
|------|------------------|
| EDA | `automation-eda-controller.target` + `nginx` on `[automationedacontroller]` (same as the installer's `restore.yml`) |
| Controller | `automation-controller-service` on `[automationcontroller]` |
| Hub | discovered `pulpcore-api`, `pulpcore-content`, `pulpcore-worker@N` + `nginx` on `[automationhub]` |
| SSO | `{{ sso_app_name | default('rh-sso7') }}.service` on `[sso]` |
| Local `redis` | `[automationhub]` / `[automationedacontroller]` hosts that have it (Controller's redis follows the Controller wrapper) |
| `postgresql` | `[database]` hosts, or the first `[automationcontroller]` host when there's no `[database]` group. That DB **starts first**. |
| `receptor` | `[execution_nodes]` |

- It uses the same commands as the installer's own `playbooks/restore.yml` (service wrappers plus Hub `pulpcore-*` units), reordered for a graceful drain.
- Hub `pulpcore-worker@N` instances and the PostgreSQL unit name (`postgresql` or `postgresql-NN`) are discovered per host.
- Each step is its own task under the default `linear` strategy, so it **finishes on every host before the next step starts**.
- `restart` is a full ordered stop, then a full ordered start.
- After a start, it polls `https://<first controller>:{{ nginx_https_port | default(443) }}/api/v2/ping/`. Use `-e aap_verify=false` to skip that, or `-e aap_ping_url=...` to override the URL.
- It does **not** drain Controller. Disable instances / wait for jobs before `stop` or `restart`.
- Limiting to `controller` with an internal DB on the Controller node still stops PostgreSQL (it's `PartOf=automation-controller.service`), so Hub / EDA lose their DB until Controller is back.
- Tested with `ansible-lint` (production profile) and against simulated hosts with a fake `systemctl`, checking step order, Redis cluster vs standalone targeting, and component limiting. **Not yet run against a real AAP install.**

<details>
<summary><code>aap-services.yml</code> (RPM 2.4)</summary>

```yaml
---
# aap-services.yml: ordered stop / start / restart of AAP 2.4 RPM services.
# Run with the SAME inventory file used for setup.sh.
#
#   ansible-playbook -i inventory aap-services.yml -e aap_action=stop
#   ansible-playbook -i inventory aap-services.yml -e aap_action=start
#   ansible-playbook -i inventory aap-services.yml -e aap_action=restart
#   # limit to components (order is still enforced):
#   ansible-playbook -i inventory aap-services.yml -e aap_action=restart -e '{"aap_components": ["eda"]}'
#
# Components: eda controller hub sso redis receptor database
#
# 2.4 has no gateway and no platform redis. Each node runs a local redis; Controller's
# redis/nginx/supervisord/receptor (and an internal postgresql) are PartOf
# automation-controller.service and stop/start with the controller wrapper.
# The redis step handles the local redis on Hub / EDA nodes.
#
# Skip the post-start ping with -e aap_verify=false; override its URL with -e aap_ping_url=...
# Drain Controller (disable instances / wait for running jobs) BEFORE aap_action=stop|restart.

- name: "AAP 2.4 RPM services: {{ aap_action | default('UNSET') }}"
  hosts: automationcontroller:automationhub:automationedacontroller:execution_nodes:sso:database
  gather_facts: false
  become: true
  any_errors_fatal: true
  vars:
    aap_components: [all]
    _all_components: [eda, controller, hub, sso, redis, receptor, database]
    _components: "{{ _all_components if 'all' in aap_components else aap_components }}"
    _stopping: "{{ aap_action in ['stop', 'restart'] }}"
    _starting: "{{ aap_action in ['start', 'restart'] }}"
    _first_controller: "{{ groups.get('automationcontroller', []) | first | default('') }}"
    _sso_unit: "{{ sso_app_name | default('rh-sso7') }}.service"
    _eda_units: [automation-eda-controller.target, nginx.service]
    # [database] hosts, plus an installer-managed DB on the first controller (no [database] group)
    _db_host: >-
      {{ inventory_hostname in groups.get('database', [])
         or (groups.get('database', []) | length == 0 and inventory_hostname == _first_controller) }}
    _in_eda: "{{ inventory_hostname in groups.get('automationedacontroller', []) }}"
    _in_controller: "{{ inventory_hostname in groups.get('automationcontroller', []) }}"
    _in_hub: "{{ inventory_hostname in groups.get('automationhub', []) }}"
    _in_sso: "{{ inventory_hostname in groups.get('sso', []) }}"
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
        _has_redis: "{{ 'redis.service' in _unit_list.stdout_lines }}"
        _has_receptor: "{{ 'receptor.service' in _unit_list.stdout_lines }}"

    # ------------------------------------------------------------------ STOP
    - name: "Stop | eda (automation-eda-controller.target, nginx)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped}
      loop: "{{ _eda_units }}"
      when: _stopping and 'eda' in _components and _in_eda | bool

    - name: "Stop | controller (also stops PartOf redis/nginx/supervisord/receptor/internal postgresql)"
      ansible.builtin.command: automation-controller-service stop
      changed_when: true
      when: _stopping and 'controller' in _components and _in_controller | bool

    - name: "Stop | hub (pulpcore api/content/workers, nginx)"
      ansible.builtin.systemd: {name: "{{ item }}", state: stopped}
      loop: "{{ _hub_units + ['nginx.service'] }}"
      when: _stopping and 'hub' in _components and _in_hub | bool

    - name: "Stop | sso"
      ansible.builtin.systemd: {name: "{{ _sso_unit }}", state: stopped}
      when: _stopping and 'sso' in _components and _in_sso | bool

    - name: "Stop | local redis (hub / eda nodes)"
      ansible.builtin.systemd: {name: redis.service, state: stopped}
      when: _stopping and 'redis' in _components and (_in_hub | bool or _in_eda | bool) and _has_redis | bool

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

    - name: "Start | receptor (execution/hop nodes)"
      ansible.builtin.systemd: {name: receptor.service, state: started}
      when: _starting and 'receptor' in _components and _in_exec | bool and _has_receptor | bool

    - name: "Start | local redis (hub / eda nodes)"
      ansible.builtin.systemd: {name: redis.service, state: started}
      when: _starting and 'redis' in _components and (_in_hub | bool or _in_eda | bool) and _has_redis | bool

    - name: "Start | sso"
      ansible.builtin.systemd: {name: "{{ _sso_unit }}", state: started}
      when: _starting and 'sso' in _components and _in_sso | bool

    - name: "Start | hub (pulpcore api/content/workers, nginx)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started}
      loop: "{{ _hub_units + ['nginx.service'] }}"
      when: _starting and 'hub' in _components and _in_hub | bool

    - name: "Start | controller"
      ansible.builtin.command: automation-controller-service start
      changed_when: true
      when: _starting and 'controller' in _components and _in_controller | bool

    - name: "Start | eda (automation-eda-controller.target, nginx)"
      ansible.builtin.systemd: {name: "{{ item }}", state: started}
      loop: "{{ _eda_units }}"
      when: _starting and 'eda' in _components and _in_eda | bool

    - name: "Start | verify controller ping"
      ansible.builtin.uri:
        url: "{{ aap_ping_url | default('https://' ~ inventory_hostname ~ ':' ~ (nginx_https_port | default(443)) ~ '/api/v2/ping/') }}"
        validate_certs: false
      register: _ping
      until: _ping.status == 200
      retries: 20
      delay: 15
      when: _starting and aap_verify | default(true) | bool and 'controller' in _components and inventory_hostname == _first_controller
```

</details>

---

## Gaps / to verify on a live host

- The base unit files ship in RPMs. Only the installer overrides were reviewed.
- Confirm the SSO unit name. `rh-sso7` comes from `sso_app_name` and could be overridden in the inventory.
  ```bash
  systemctl list-dependencies automation-controller.service
  systemctl list-dependencies automation-eda-controller.target
  systemctl show -p PartOf nginx supervisord redis postgresql receptor
  ```
