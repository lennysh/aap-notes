# AAP 2.7 Operator — CPU & Memory Requirements (per Pod)

Customer-facing sizing reference for Architecture Review Boards and capacity planning on OpenShift.

| Item | Value |
|------|--------|
| **Product version** | Ansible Automation Platform **2.7** |
| **Install method** | AAP Operator (`AnsibleAutomationPlatform` CR) |
| **Source of truth** | Operator role defaults under `aap-27/operator/*` + gateway-operator sample CR |
| **Generated** | 2026-10-12 |
| **Related** | [AAP 2.6 resource requirements](../AAP26/resource-requirements.md) |

---

## 2.7 vs 2.6 (what changed for sizing)

| Change | Impact on capacity planning |
|--------|-----------------------------|
| **EDA Redis removed** | No `eda-redis` pod. Task queuing uses PostgreSQL `pg_notify` / dispatcherd. |
| **EDA scheduler pod removed** | Scheduling is integrated into dispatcherd workers; no separate scheduler Deployment. |
| **`spec.eda.redis` / `eda_redis_secret`** | Deprecated and ignored on upgrade; operator cleans up legacy Redis objects. |
| Gateway / Controller / Hub defaults | Same request values as 2.6 for the compared fields. |

**Net effect on default request footprint (standard platform install):** about **−150m CPU / −612Mi RAM** vs AAP 2.6 after multi-container-aware EDA math (removal of EDA scheduler ×2 and EDA Redis ×1). EDA API still counts as **3×** `api.resource_requirements`; event-stream as **2×**.

> Note: The sample CR `aap-resource-requirements.yml` in the gateway operator still shows EDA `scheduler` / `ui` blocks for historical completeness. Under a platform CR, **EDA UI remains disabled**, and **scheduler/redis are not deployed** in 2.7. Size only the pods that actually exist.

---

## Definitions (read this first)

| Term | Meaning |
|------|---------|
| **Pod** | Smallest deployable unit on OpenShift/Kubernetes. One pod can hold one or more **containers** that share the pod’s network/storage. |
| **Container** | A process image running inside a pod (e.g. Gateway `api` and `proxy` are two containers in one gateway pod). |
| **Replica** | How many identical copies of a pod the Deployment/StatefulSet keeps running. Totals in this doc are usually **per-pod value × replicas**. |
| **req** / **request** | Kubernetes `resources.requests` — CPU/memory the scheduler **reserves** for the container. Used for placement and for most capacity-planning floors. |
| **lim** / **limit** | Kubernetes `resources.limits` — CPU/memory **ceiling**. The container may use up to this; exceeding memory usually gets the pod OOM-killed. Many operator defaults omit limits. |
| **CPU `m`** | Millicores. `1000m` = 1 full CPU/vCPU core. Example: `100m` = 0.1 core. |
| **CPU bare number** | Whole cores when written without `m` (e.g. `2` or `"256"` = 2 or 256 cores). |
| **RAM `Mi` / `Gi`** | Mebibytes / gibibytes (binary). `1024Mi` = 1Gi. Not the same as decimal MB/GB, but close enough for planning. |
| **Operator default** | Values the AAP operators apply if you do **not** set custom `resource_requirements` on the CR. |
| **Sample CR example** | Example values from the in-repo `aap-resource-requirements.yml` (requests **and** limits). A tuning / ResourceQuota starting point — **not** always larger than the operator default. |
| **ARB floor** | Suggested Architecture Review Board planning number: the **higher** of operator-default vs sample **requests**, usually keeping default replica counts. |
| **CR** | Custom Resource — here, typically `AnsibleAutomationPlatform` (and nested Controller/Hub/EDA specs). |
| **ResourceQuota** | Namespace policy that requires pods to declare requests/limits and caps total usage. |
| **Steady-state** | Resources after pods are running (excludes one-shot **init containers** and temporary backup/restore/migration jobs). |
| **Init container** | Runs once at pod start, then exits. Not counted in steady-state totals. |
| **EE** | Execution Environment — container image used to run Ansible. Control-plane EE sidecars are in the steady-state tables; **job EE pods** are in [§7](#7-ephemeral-execution-pods-automation-job--activation-job-). |
| **Mesh / execution node** | Where playbook jobs often run outside the control-plane pods. Size separately (not the same as Container Group `automation-job-*` pods). |
| **Container Group** | Controller instance group that launches each job as an OpenShift Pod (`automation-job-<job_id>`). |
| **`automation-job-*`** | Ephemeral Controller Container Group job pod (one per running job). See [§7.1](#71-controller-container-group--automation-job-job_id). |
| **`activation-job-*`** | Ephemeral EDA Kubernetes Job for a running activation; pod template `activation-pod-*`. See [§7.2](#72-eda-activations--activation-job-activation_id-rulebook_process_id). |
| **Ephemeral / peak concurrent** | Resources that exist only while jobs/activations run. Plan for the **maximum** number expected at once, not the steady-state platform footprint. |
| **Dispatcherd** | EDA’s PostgreSQL/`pg_notify`-based task queue in 2.7 (replaces the former EDA Redis + scheduler pods). |
| **OOM** | Out of memory — kubelet kills a container that exceeds its memory **limit**. |
| **Shared CR resource block** | Some EDA pods apply the **same** `resource_requirements` from the CR to **every** app container in that pod (e.g. EDA API: `eda-api` + `daphne` + `nginx` each get the full `api.resource_requirements`). Pod totals are therefore **N ×** the CR field. |

### Column legend (tables below)

| Column shorthand | Means |
|------------------|--------|
| Default CPU / RAM req | Operator-default **requests** |
| Sample CPU / RAM req | Sample-CR **requests** |
| Sample CPU / RAM lim | Sample-CR **limits** |
| ARB floor | Higher of the two request columns (see Definitions) |

---

## How to read this document

Two columns are used throughout — **do not read them as “min vs larger recommendation”**:

| Column | Meaning |
|--------|---------|
| **Operator default** | Out-of-the-box Kubernetes **requests** if you do **not** customize the CR. Most containers have **no** **limits**. |
| **Sample CR example** | Values from `aap-resource-requirements.yml` (requests **and** limits). A ResourceQuota / tuning starting point — it can be **lower or higher** than the operator default depending on the field. |

**Gateway gotcha:** operator ships Gateway `api`/`proxy` at **750Mi** each; the sample sets Gateway `api` to **256Mi** (and does not override `proxy`), so sample Gateway memory **requests** can look *lower* than an unmodified install. That is not a “size up from minimum” table.

**ARB planning rule of thumb for requests:** use the **higher** of (operator default, sample) per container when reserving capacity (unless you intentionally apply the lower customize values). For **limits**, use the sample (or your own tuned values).

**Important distinctions**

1. **Requests ≠ production capacity.** Operator defaults are sized to *schedule*, not large job loads. Controller **task** capacity on OpenShift is derived from **limits** on the task container when set.
2. **Multi-container pods** sum container requests/limits (Gateway API+proxy; Controller web/task sidecars).
3. **Init containers** are startup-only and excluded from steady-state totals.
4. **Steady-state tables exclude** mesh execution/hop nodes, backup/restore jobs, and playbook-launched customer workloads. **Container Group `automation-job-*` and EDA `activation-job-*` pods** are documented in [§7](#7-ephemeral-execution-pods-automation-job--activation-job-) (peak concurrent), not in §6 totals.
5. **EDA UI** is **disabled** when managed via the platform CR (`ui_disabled: true`).
6. **Hub Postgres** still defaults to `postgres_resource_requirements: {}` — set explicitly for ResourceQuota clusters.
7. **Gateway Envoy (`proxy`)** still ships CPU **limit** `256` by design (FD/thread safety). Do not size the cluster to that number.

---

## Assumed topology (standard platform install)

| Component | Enabled | Managed Postgres | Notes |
|-----------|---------|------------------|-------|
| Platform Gateway (API + Envoy proxy) | Yes | Yes (standalone Redis) | Entry point / platform UI |
| Automation Controller | Yes | Yes | Web + task Deployments |
| Private Automation Hub | Yes | Yes | Content/worker default replicas **2** |
| Event-Driven Ansible | Yes | Yes | No Redis; no scheduler pod; UI disabled |
| Lightspeed / MCP / Metrics | No | — | Optional; see [Optional components](#optional-components) |

---

## 1. Platform Gateway

**Pod:** `<aap>-gateway` — containers `api` + `proxy` (Envoy). Replicas = `spec.api.replicas` (default **1**).

| Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|-----------|----------------------|---------------------|---------------------|
| `api` | 50m / **750Mi** | 100m / **256Mi** ↓ | 500m / 1000Mi |
| `proxy` | 50m / **750Mi** | 50m\* / **750Mi**\* | 256† / *(none)* |
| **Pod total** | **100m / 1500Mi** | **150m / 1006Mi** | — |

\* Sample CR does **not** override `proxy`; operator defaults apply unless you set `spec.proxy.resource_requirements`.  
† Operator default CPU limit `256` (intentional Envoy FD/thread cap—not a sizing recommendation).  
↓ Sample **lowers** the API memory request vs operator default — not a size-up.

| Pod | Replicas | Default CPU / RAM (total) | Sample CPU / RAM req (total) |
|-----|----------|---------------------------|------------------------------|
| gateway | 1 | 100m / 1500Mi | 150m / 1006Mi |
| gateway-redis | 1 | 50m / 100Mi | 100m / 256Mi |
| gateway-postgres | 1 | 200m / **512Mi** | 100m / **256Mi** ↓ |

**Redis / Postgres (limits from sample)**

| Pod | Sample CPU lim | Sample RAM lim |
|-----|----------------|----------------|
| gateway-redis | 500m | 500Mi |
| gateway-postgres | 500m | 800Mi |

**Gateway subtotal (requests × replicas)**

| | Operator default | Sample CR | ARB floor (higher of the two) |
|--|------------------|-----------|-------------------------------|
| CPU | 350m | 350m | **350m** |
| Memory | **2112Mi (~2.1 Gi)** | 1518Mi (~1.5 Gi) | **2112Mi (~2.1 Gi)** |

---

## 2. Automation Controller

Web and task are **separate Deployments**. Default `replicas: 1` each (unless `web_replicas` / `task_replicas` override).

### 2.1 Controller web pod — `redis` + `web` + `rsyslog`

| Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|-----------|----------------------|---------------------|---------------------|
| redis | 50m / 64Mi | 50m / 64Mi | 100m / 200Mi |
| web | 100m / 128Mi | 100m / 200Mi | 200m / 1600Mi |
| rsyslog | 100m / 128Mi | 100m / 128Mi | 500m / 250Mi |
| **Pod total** | **250m / 320Mi** | **250m / 392Mi** | **800m / 2050Mi** |

### 2.2 Controller task pod — `redis` + `task` + `ee` + `rsyslog`

| Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|-----------|----------------------|---------------------|---------------------|
| redis | 50m / 64Mi | 50m / 64Mi | 100m / 200Mi |
| task | 100m / 128Mi | 100m / 150Mi | 1000m / 1200Mi |
| ee (control-plane EE) | 100m / 64Mi | 100m / 64Mi | 1000m / 500Mi |
| rsyslog | 100m / 128Mi | 100m / 128Mi | 500m / 250Mi |
| **Pod total** | **350m / 384Mi** | **350m / 406Mi** | **2600m / 2150Mi** |

### 2.3 Controller Postgres

| Pod | Default CPU / RAM req | Sample CR | Notes |
|-----|----------------------|-----------|-------|
| controller-postgres | 10m / 64Mi | *(not in sample)* | Prefer external PG or raise requests/limits for production |

### 2.4 Init containers (startup only)

| Spec field | Default requests |
|------------|------------------|
| `init_container_resource_requirements` | 100m / 128Mi (sample adds limits 500m / 200Mi) |

**Controller subtotal (steady-state requests, 1 web + 1 task + postgres)**

| | Operator default | Sample\* | ARB floor (higher) |
|--|------------------|----------|---------------------|
| CPU | 610m | 610m | **610m** |
| Memory | 768Mi | 862Mi | **862Mi** |

\* Sample for web/task containers; postgres kept at operator default.

---

## 3. Private Automation Hub

Each Hub Deployment/StatefulSet below is a **single app container** per pod (the CR `resource_requirements` applies once per pod). Postgres may include a conditional init container using the same postgres resource block.

| Pod | Default replicas | Default CPU / RAM **per pod** | Sample replicas | Sample CPU / RAM req | Sample CPU / RAM lim |
|-----|------------------|------------------------------|-----------------|---------------------|---------------------|
| hub-api | 1 | 200m / 512Mi | 1 | 150m / 256Mi ↓ | 800m / 500Mi |
| hub-content | **2** | 200m / 512Mi | **1** | 150m / 256Mi ↓ | 800m / 1200Mi |
| hub-worker | **2** | 200m / 512Mi | **1** | 150m / 256Mi ↓ | 800m / 400Mi |
| hub-web | 1 | 200m / 512Mi | 1 | 100m / 256Mi ↓ | 500m / 300Mi |
| hub-redis | 1 | 200m / 512Mi | 1 | 100m / 250Mi ↓ | 300m / 400Mi |
| hub-postgres | 1 | **none** (`{}`) | 1 | **set explicitly** | **set explicitly** |

↓ Sample often **lowers** per-pod requests and Hub replica counts vs operator defaults.

**Hub subtotal (requests × replicas; postgres excluded)**

| | Operator default (× default reps) | Sample (× sample reps) | ARB floor\* |
|--|-----------------------------------|------------------------|-------------|
| CPU | **1400m** | 650m | **1400m** |
| Memory | **3584Mi (~3.5 Gi)** | 1274Mi (~1.2 Gi) | **3584Mi (~3.5 Gi)** |

\* Floor assumes default Hub replica counts (2 content / 2 worker).

---

## 4. Event-Driven Ansible (2.7 layout)

> **2.7 removals:** no `eda-redis` pod and no `eda-scheduler` pod (dispatcherd / PostgreSQL `pg_notify`). Legacy Redis/scheduler objects are cleaned up on upgrade.  
> **Multi-container note:** Setting `spec.eda.api.resource_requirements` (etc.) configures **each** listed app container — not the pod as a whole. Init containers use the same CR block when present but are **startup-only**. `configure-bundle-ca-cert` init appears only when a bundle CA is configured.

### 4.1 `eda-api` pod (Deployment) — default replicas **1**

CR field: `api.resource_requirements` (default **50m / 350Mi** req; sample same req, **500m / 400Mi** lim).

| Role | Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|------|-----------|----------------------|---------------------|---------------------|
| init (startup) | `run-migrations` | 50m / 350Mi | 50m / 350Mi | 500m / 400Mi |
| init (startup) | `eda-initial-data` | 50m / 350Mi | 50m / 350Mi | 500m / 400Mi |
| init (startup, optional) | `configure-bundle-ca-cert` | 50m / 350Mi | 50m / 350Mi | 500m / 400Mi |
| app | `eda-api` (gunicorn) | 50m / 350Mi | 50m / 350Mi | 500m / 400Mi |
| app | `daphne` (WebSocket/ASGI) | 50m / 350Mi | 50m / 350Mi | 500m / 400Mi |
| app | `nginx` | 50m / 350Mi | 50m / 350Mi | 500m / 400Mi |
| **Steady-state pod total** | **3 app containers** | **150m / 1050Mi** | **150m / 1050Mi** | **1500m / 1200Mi** |

### 4.2 `eda-event-stream` pod — default replicas **1**

CR field: `event_stream.resource_requirements` (default **50m / 350Mi**; sample **25m / 150Mi** req, **100m / 300Mi** lim).

| Role | Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|------|-----------|----------------------|---------------------|---------------------|
| init (startup) | `wait-for-migrations` | 50m / 350Mi | 25m / 150Mi | 100m / 300Mi |
| init (startup, optional) | `configure-bundle-ca-cert` | 50m / 350Mi | 25m / 150Mi | 100m / 300Mi |
| app | `eda-event-stream` | 50m / 350Mi | 25m / 150Mi | 100m / 300Mi |
| app | `nginx` | 50m / 350Mi | 25m / 150Mi | 100m / 300Mi |
| **Steady-state pod total** | **2 app containers** | **100m / 700Mi** | **50m / 300Mi** | **200m / 600Mi** |

### 4.3 `eda-default-worker` pod — default replicas **2** (sample often **1**)

CR field: `default_worker.resource_requirements` (default **25m / 130Mi**; sample **25m / 200Mi** req, **500m / 400Mi** lim).

| Role | Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|------|-----------|----------------------|---------------------|---------------------|
| init (startup) | `wait-for-migrations` | 25m / 130Mi | 25m / 200Mi | 500m / 400Mi |
| init (startup, optional) | `configure-bundle-ca-cert` | 25m / 130Mi | 25m / 200Mi | 500m / 400Mi |
| app | `eda-default-worker` | 25m / 130Mi | 25m / 200Mi | 500m / 400Mi |
| **Steady-state pod total** | **1 app container** | **25m / 130Mi** | **25m / 200Mi** | **500m / 400Mi** |

### 4.4 `eda-activation-worker` pod — default replicas **2** (sample often **1**)

CR field: `activation_worker.resource_requirements` (default **25m / 150Mi**; sample **25m / 150Mi** req, **500m / 400Mi** lim).

| Role | Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|------|-----------|----------------------|---------------------|---------------------|
| init (startup) | `wait-for-migrations` | 25m / 150Mi | 25m / 150Mi | 500m / 400Mi |
| init (startup, optional) | `configure-bundle-ca-cert` | 25m / 150Mi | 25m / 150Mi | 500m / 400Mi |
| app | `eda-activation-worker` | 25m / 150Mi | 25m / 150Mi | 500m / 400Mi |
| **Steady-state pod total** | **1 app container** | **25m / 150Mi** | **25m / 150Mi** | **500m / 400Mi** |

### 4.5 `eda-postgres` pod — default replicas **1**

| Role | Container | Default CPU / RAM req | Sample | Notes |
|------|-----------|----------------------|--------|-------|
| init (startup, conditional) | `init` | 50m / 100Mi | *(omit from sample; use default)* | Volume-init path; not always present on OpenShift |
| app | `postgres` | 50m / 100Mi | *(omit from sample; use default)* | Shared with dispatcherd/`pg_notify` in 2.7 |

### 4.6 Removed in 2.7 (do not size)

| Former pod | Status |
|------------|--------|
| `eda-scheduler` | Removed — scheduling is inside dispatcherd workers |
| `eda-redis` | Removed — no Redis Deployment |

### 4.7 `eda-ui` pod — **not deployed** under platform CR (`ui_disabled: true`)

| Role | Container | Default CPU / RAM req | Sample CPU / RAM req | Sample CPU / RAM lim |
|------|-----------|----------------------|---------------------|---------------------|
| app | `eda-ui` | 25m / 64Mi | 25m / 64Mi | 500m / 150Mi |

### 4.8 EDA rollup (steady-state requests × replicas; no UI / no Redis / no scheduler)

| Pod | Def. reps | Containers (app) | Default pod req | Default × reps | Sample reps | Sample pod req | Sample × reps |
|-----|-----------|------------------|-----------------|----------------|-------------|----------------|---------------|
| eda-api | 1 | 3 | 150m / 1050Mi | 150m / 1050Mi | 1 | 150m / 1050Mi | 150m / 1050Mi |
| eda-event-stream | 1 | 2 | 100m / 700Mi | 100m / 700Mi | 1 | 50m / 300Mi | 50m / 300Mi |
| eda-default-worker | **2** | 1 | 25m / 130Mi | 50m / 260Mi | **1** | 25m / 200Mi | 25m / 200Mi |
| eda-activation-worker | **2** | 1 | 25m / 150Mi | 50m / 300Mi | **1** | 25m / 150Mi | 25m / 150Mi |
| eda-postgres | 1 | 1 | 50m / 100Mi | 50m / 100Mi | 1 | 50m / 100Mi | 50m / 100Mi |
| **EDA total** | | | | **400m / 2410Mi (~2.4 Gi)** | | | **300m / 1800Mi (~1.8 Gi)** |

| | Operator default (× default reps) | Sample (× sample reps) | ARB floor\* |
|--|-----------------------------------|------------------------|-------------|
| CPU | **400m** | 300m | **400m** |
| Memory | **2410Mi (~2.4 Gi)** | 1800Mi (~1.8 Gi) | **~2550Mi (~2.5 Gi)**† |

\* Floor keeps **default replica counts**.  
† Slightly above operator-default memory because sample raises default-worker memory to 200Mi/pod while default reps remain 2.

Operator docs state dispatcherd/`pg_notify` overhead on Postgres is typically negligible; keep normal DB headroom rather than adding a Redis-sized reservation.

---

## 5. Operator manager pods

These run in the Operator namespace (often `aap` or a dedicated operators project). One replica each typical. Metrics and Lightspeed managers are only present if those operators are installed from OperatorHub / the bundle; include them in capacity planning when the customer will enable those features.

| Operator Deployment | CPU req | RAM req | CPU lim | RAM lim | Notes |
|---------------------|---------|---------|---------|---------|-------|
| automation-gateway-operator | 10m | 256Mi | 2000m | 4000Mi | Always for platform CR |
| automation-controller-operator | 50m | 32Mi | 2000m | 4000Mi | Always for platform CR |
| automation-hub-operator | 10m | 256Mi | 2000m | 1800Mi | If Hub enabled |
| automation-eda-controller-operator | 10m | 256Mi | 2000m | 4000Mi | If EDA enabled |
| automation-metrics-operator | 100m | 128Mi | 500m | 1Gi | If Metrics operator installed |
| automation-lightspeed-operator | 10m | 256Mi | 500m | 768Mi | If Lightspeed operator installed (`lightpseed` package name in clone) |
| **Core four (GW+Ctrl+Hub+EDA) requests** | **80m** | **800Mi** | — | — | Typical platform install |
| **All six (incl. Metrics+Lightspeed) requests** | **190m** | **1184Mi (~1.2 Gi)** | — | — | When both optional operators are installed |

---

## 6. Totals — standard platform (Gateway + Controller + Hub + EDA)

Steady-state **requests** only. Excludes init containers, ephemeral `automation-job-*` / `activation-job-*` pods (see [§7](#7-ephemeral-execution-pods-automation-job--activation-job-)), mesh nodes, Lightspeed/MCP/Metrics, and Hub Postgres when unset.

### 6.1 Workload pods (operands)

| Scope | Operator default CPU / RAM | Sample CPU / RAM req | ARB floor CPU / RAM\* |
|-------|----------------------------|----------------------|------------------------|
| Gateway | 350m / 2112Mi | 350m / 1518Mi | 350m / **2112Mi** |
| Controller | 610m / 768Mi | 610m / 862Mi | 610m / **862Mi** |
| Hub (no postgres) | 1400m / 3584Mi | 650m / 1274Mi | **1400m / 3584Mi** |
| EDA (2.7, multi-container aware) | 400m / 2410Mi | 300m / 1800Mi | **400m / ~2550Mi** |
| **Workload total** | **2760m (~2.8 cores) / 8874Mi (~8.7 Gi)** | 1910m / 5454Mi | **~2.8 cores / ~8.9 Gi** |

\* ARB floor = higher of the two columns, keeping **default replica counts** for Hub/EDA. EDA pod totals multiply shared CR resource blocks across app containers (API ×3, event-stream ×2).

Add Hub Postgres when set (suggested +200m / +512Mi): ~**3.0 cores / ~9.4 Gi** ARB-floor footprint.

### 6.2 Including operator managers

| Scope | Operator default CPU / RAM |
|-------|----------------------------|
| Workload + core four operators | **2840m (~2.8 cores) / 9674Mi (~9.4 Gi)** |
| Workload + all six operators | **2950m (~3.0 cores) / 10058Mi (~9.8 Gi)** |

### 6.3 Sample-CR limits footprint (approximate)

Summing **limits** from the sample for deployed containers (Gateway `proxy` CPU 256 ignored as non-representative; unmanaged postgres omitted):

| Component area | Approx. CPU limits sum | Approx. RAM limits sum |
|----------------|------------------------|------------------------|
| Gateway api+redis+db | 1.5 cores | ~2.3 Gi |
| Controller web+task containers | 3.4 cores | ~4.1 Gi |
| Hub (sample replicas) | 3.2 cores | ~2.8 Gi |
| EDA (sample reps; API×3 + event-stream×2; no redis/scheduler) | ~2.7 cores | ~2.5 Gi |
| **Rough limits budget** | **~10.8 cores** | **~11.7 Gi** |

---

## 7. Ephemeral execution pods (`automation-job-*`, `activation-job-*`)

These are **not** part of the steady-state platform totals in §6. They are created while work is running and removed afterward. Size worker/node capacity for **peak concurrent** jobs or activations, not daily averages.

### 7.1 Controller Container Group — `automation-job-<job_id>`

When a Job Template runs on a **Container Group** instance group, Controller creates one OpenShift Pod per running job.

| Item | Value |
|------|-------|
| Pod name | `automation-job-<job_id>` |
| Containers | **1** — launch path sets the container name to `automation-job-<job_id>` (default pod-spec template uses `worker`) |
| Image | The job’s Execution Environment |
| Default CPU request | `250m` |
| Default RAM request | `100Mi` |
| Default limits | **none** |
| Override | Instance Group **Pod specification** (`pod_spec_override`) deep-merged over the default |

**Not this path:** jobs on automation mesh / hybrid execution nodes do **not** create these pods (receptor work-unit names may still look like `automation-job-<id>`). Size mesh nodes separately.

#### Per-container breakdown (default Container Group pod)

| Container | Role | CPU req | RAM req | CPU lim | RAM lim |
|-----------|------|---------|---------|---------|---------|
| `automation-job-<job_id>` | `ansible-runner worker` | 250m | 100Mi | — | — |
| **Pod total** | | **250m** | **100Mi** | — | — |

#### Concurrent Controller jobs — reserved capacity at **default** requests

| Peak concurrent jobs | CPU reserved | RAM reserved |
|---------------------:|-------------:|-------------:|
| 100 | 25 cores (`25000m`) | ~9.8 Gi (`10000Mi`) |
| 500 | 125 cores | ~48.8 Gi (`50000Mi`) |
| 1000 | 250 cores | ~97.7 Gi (`100000Mi`) |

Formula: `N × 250m` CPU and `N × 100Mi` RAM. If you raise per-pod requests (or set limits) via Instance Group pod spec for heavy playbooks, scale the table by your per-pod values.

Also plan Controller **task** capacity / forks — each running job consumes control-plane capacity in addition to the EE pod reservation.

### 7.2 EDA activations — `activation-job-<activation_id>-<rulebook_process_id>`

When an activation runs on OpenShift, EDA creates a Kubernetes **Job**; the Job controller creates the running Pod.

| Item | Value |
|------|-------|
| Job name | `activation-job-<activation_id>-<rulebook_process_id>` (`resource_prefix` = `activation`) |
| Pod template name | `activation-pod-<activation_id>-<rulebook_process_id>` |
| Running pod name | Typically `{job-name}-xxxxx` (Job controller suffix) |
| Containers | **1** — name `eda-<rulebook_process_id>-<uuid>` (`CONTAINER_NAME_PREFIX` default `eda`) |
| Workload | `ansible-rulebook` in the decision-environment image |
| Default CPU / RAM requests | **unset** (container has no `resources` block) |
| Default limits | **unset** → QoS **BestEffort** unless a namespace LimitRange / admission policy injects values |
| Related (Podman only) | `PODMAN_MEM_LIMIT` default `200m` — **not** applied on the Kubernetes engine path |

#### Per-container breakdown (as coded today)

| Container | Role | CPU req | RAM req | CPU lim | RAM lim |
|-----------|------|---------|---------|---------|---------|
| `eda-<process_id>-<uuid>` | `ansible-rulebook` | — (unset) | — (unset) | — | — |
| **Pod total** | | **0 reserved** | **0 reserved** | — | — |

For ResourceQuota / ARB planning you **must** pick an assumed floor (LimitRange, policy, or measured usage). The product does not reserve CPU/RAM for activation pods by default.

#### Concurrent activations — illustrative planning floors

These rows are **planning scenarios**, not product defaults. Choose a per-activation floor from measurement or policy, then scale:

| Peak concurrent activations | @ 250m / 256Mi each | @ 250m / 512Mi each | @ 500m / 1Gi each |
|----------------------------:|--------------------:|--------------------:|------------------:|
| 100 | 25 cores / 25 Gi | 25 cores / 50 Gi | 50 cores / 100 Gi |
| 500 | 125 cores / 125 Gi | 125 cores / 250 Gi | 250 cores / 500 Gi |
| 1000 | 250 cores / 250 Gi | 250 cores / 500 Gi | 500 cores / 1000 Gi |

Actual usage depends on rulebook complexity and event rate. Unlike short Controller jobs, long-lived activations hold their reservation for the entire runtime.

**Control plane:** starting/managing activations also needs EDA `activation_worker` (and related worker) capacity — scale those Deployments separately from the activation pods.

## 8. Optional components

### 8.1 Ansible Lightspeed / model serving (heavy)

| Pod | Replicas | CPU req | RAM req | CPU lim | RAM lim |
|-----|----------|---------|---------|---------|---------|
| chatbot-api | 1 | 500m | 5000Mi | 1500m | 8000Mi |
| model | 1 | 500m | 5000Mi | 1500m | 8000Mi |
| mcp-server api | 1 | 100m | 500Mi | 200m | 1000Mi |
| lightspeed-postgres | 1 | 50m | 100Mi | — | — |
| **Lightspeed subtotal (req)** | | **1150m** | **~10.4 Gi** | | |

### 8.2 Metrics service

| Pod | Replicas | CPU req | RAM req | CPU lim | RAM lim |
|-----|----------|---------|---------|---------|---------|
| automationmetricsservice | 1 | 50m | 256Mi | 1000m | 1Gi |

---

## 9. What to tell the Architecture Review Board

**Cluster reservation for control plane (default Operator install):**

- Use the **ARB floor** (~**2.8 CPU / ~8.9 Gi** workload requests; ~**9.4 Gi** with core four operators, ~**9.8 Gi** if Metrics + Lightspeed operators are also installed) — not the lower sample-CR request totals. Gateway/Hub defaults already request more memory than the customize snippet; EDA API/event-stream pods request **N ×** the CR field (3 and 2 containers).
- Still **not** sufficient for concurrent automation. Add:
  - **Container Group job pods** (`automation-job-*`): default **250m / 100Mi** each — e.g. **100 / 500 / 1000** concurrent ⇒ **25 / 125 / 250** cores and **~10 / ~49 / ~98 Gi** reserved (see [§7.1](#71-controller-container-group--automation-job-job_id)).
  - **EDA activation pods** (`activation-job-*`): **no default requests/limits** — assume a planning floor (e.g. 250m/512Mi) and scale; **100 / 500 / 1000** concurrent at that floor ⇒ **25 / 125 / 250** cores and **50 / 250 / 500 Gi** (see [§7.2](#72-eda-activations--activation-job-activation_id-rulebook_process_id)).
  - **Mesh execution/hop nodes** (if used): commonly on the order of **4 vCPU / 16 Gi per execution node** as a starting analogy.

**Production / ResourceQuota practice:**

1. Use the sample CR for **limits** (and fields you want to tune), but do **not** blindly lower Gateway/Hub memory requests below operator defaults unless you have measured headroom.
2. Always set **Controller `task_resource_requirements.limits`**.
3. Explicitly set **Hub `postgres_resource_requirements`** (prefer external Postgres for enterprise).
4. Override **`spec.proxy.resource_requirements`** if Envoy must comply with a ResourceQuota (do not treat limit `256` as a target).
5. For upgrades from 2.6: remove EDA Redis/scheduler from capacity models; reclaim that allocation; leave Postgres sizing as-is unless monitoring shows pressure.

**RHEL/VM product minimums** remain topology-level guidance (often ~16 Gi / 4 vCPU per major role). On OpenShift, use the per-pod tables for namespace quotas.

---

## 10. Source file map (lab clone `aap-27/`)

| Component | Defaults / reference |
|-----------|----------------------|
| Controller containers | `operator/automation-controller-operator/roles/installer/defaults/main.yml` |
| Hub deployments | `operator/automation-hub-operator/roles/common/defaults/main.yml` |
| Hub Postgres | `operator/automation-hub-operator/roles/postgres/defaults/main.yml` |
| EDA | `operator/automation-eda-controller-operator/roles/eda/defaults/main.yml` |
| EDA Postgres | `operator/automation-eda-controller-operator/roles/postgres/defaults/main.yml` |
| EDA Redis deprecation | `operator/automation-eda-controller-operator/docs/user-guide/redis-configuration.md` |
| Gateway API/proxy | `operator/automation-gateway-operator/roles/ansibleautomationplatform/defaults/main.yml` |
| Gateway Redis / Postgres | `.../roles/redis/defaults/main.yml`, `.../roles/postgres/defaults/main.yml` |
| Recommended sample CR | `operator/automation-gateway-operator/dev/aap-cr/aap-resource-requirements.yml` |
| Lightspeed | `operator/automation-lightpseed-operator/roles/*/defaults/main.yml` |
| Metrics | `operator/automation-metrics-operator/roles/automationmetricsservice/defaults/main.yml` |
| Controller Container Group default pod | `controller/automation-controller/awx/main/utils/execution_environments.py` (`get_default_pod_spec`) |
| Controller job pod naming / merge | `controller/automation-controller/awx/main/scheduler/kubernetes.py` |
| EDA activation Job/Pod (K8s) | `eda/automation-eda-controller/src/aap_eda/services/activation/engine/kubernetes.py` |
| EDA container name / Podman mem | `eda/automation-eda-controller/src/aap_eda/settings/defaults.py` (`CONTAINER_NAME_PREFIX`, `PODMAN_MEM_LIMIT`) |

---

## 11. Example CR snippet (recommended starting point for 2.7)

Adapted from the gateway-operator sample. EDA `scheduler` / `ui` / Redis omitted because they are not part of the 2.7 platform footprint.

```yaml
apiVersion: aap.ansible.com/v1alpha1
kind: AnsibleAutomationPlatform
metadata:
  name: aap
spec:
  api:
    replicas: 1
    resource_requirements:
      requests: {cpu: 100m, memory: 256Mi}
      limits: {cpu: 500m, memory: 1000Mi}
  # Optional: constrain Envoy for ResourceQuota
  # proxy:
  #   resource_requirements:
  #     requests: {cpu: 50m, memory: 750Mi}
  #     limits: {cpu: "2", memory: 2Gi}
  redis:
    replicas: 1
    resource_requirements:
      requests: {cpu: 100m, memory: 256Mi}
      limits: {cpu: 500m, memory: 500Mi}
  database:
    resource_requirements:
      requests: {cpu: 100m, memory: 256Mi}
      limits: {cpu: 500m, memory: 800Mi}

  controller:
    disabled: false
    task_resource_requirements:
      requests: {cpu: 100m, memory: 150Mi}
      limits: {cpu: 1000m, memory: 1200Mi}
    web_resource_requirements:
      requests: {cpu: 100m, memory: 200Mi}
      limits: {cpu: 200m, memory: 1600Mi}
    ee_resource_requirements:
      requests: {cpu: 100m, memory: 64Mi}
      limits: {cpu: 1000m, memory: 500Mi}
    redis_resource_requirements:
      requests: {cpu: 50m, memory: 64Mi}
      limits: {cpu: 100m, memory: 200Mi}
    rsyslog_resource_requirements:
      requests: {cpu: 100m, memory: 128Mi}
      limits: {cpu: 500m, memory: 250Mi}

  hub:
    disabled: false
    api:
      replicas: 1
      resource_requirements:
        requests: {cpu: 150m, memory: 256Mi}
        limits: {cpu: 800m, memory: 500Mi}
    content:
      replicas: 1
      resource_requirements:
        requests: {cpu: 150m, memory: 256Mi}
        limits: {cpu: 800m, memory: 1200Mi}
    worker:
      replicas: 1
      resource_requirements:
        requests: {cpu: 150m, memory: 256Mi}
        limits: {cpu: 800m, memory: 400Mi}
    web:
      replicas: 1
      resource_requirements:
        requests: {cpu: 100m, memory: 256Mi}
        limits: {cpu: 500m, memory: 300Mi}
    redis:
      replicas: 1
      resource_requirements:
        requests: {cpu: 100m, memory: 250Mi}
        limits: {cpu: 300m, memory: 400Mi}
    # postgres_resource_requirements:
    #   requests: {cpu: 200m, memory: 512Mi}
    #   limits: {cpu: 1000m, memory: 2Gi}

  eda:
    disabled: false
    # Do not size for redis or scheduler in 2.7 — not deployed
    api:
      replicas: 1
      resource_requirements:
        requests: {cpu: 50m, memory: 350Mi}
        limits: {cpu: 500m, memory: 400Mi}
    default_worker:
      replicas: 1
      resource_requirements:
        requests: {cpu: 25m, memory: 200Mi}
        limits: {cpu: 500m, memory: 400Mi}
    activation_worker:
      replicas: 1
      resource_requirements:
        requests: {cpu: 25m, memory: 150Mi}
        limits: {cpu: 500m, memory: 400Mi}
    event_stream:
      replicas: 1
      resource_requirements:
        requests: {cpu: 25m, memory: 150Mi}
        limits: {cpu: 100m, memory: 300Mi}
```

---

## Revision notes

- Values verified against AAP 2.7 operator defaults in the lab clone (`aap-27/.version.lock` → `2.7`).
- No local `product-docs/` tree was present for 2.7 in the clone; recommended column uses the in-repo gateway-operator sample CR.
- Added §7 for ephemeral Controller `automation-job-*` (default 250m/100Mi) and EDA `activation-job-*` (no K8s resources by default), with concurrent 100/500/1000 examples (same code paths as 2.6 for these pods).
- Re-validate after operator z-stream upgrades; defaults can change.
