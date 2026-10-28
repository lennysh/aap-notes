# AAP 2.7 Resource Operator — Custom Resources (expanded)

Support / GitOps reference for the **Ansible Automation Platform Resource Operator** (`tower.ansible.com/v1alpha1`). Expands the thin published field tables with connection-secret setup, CRD-complete `spec` fields, deprecations, and known docs gaps.

| Item | Value |
|------|--------|
| **Product version** | Ansible Automation Platform **2.7** |
| **API group / version** | `tower.ansible.com/v1alpha1` |
| **Published reference** | [Resource Operator custom resources](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/reference-resource_operator_custom_resources) |
| **Published install / connect guide** | [Ansible Automation Platform Resource Operator](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/installing_and_upgrading_red_hat_ansible_automation_platform/install-assembly_controller_resource_operator) (token + `aap-access` procedure) |
| **CRD source of truth** | `aap-notes/.crd-dumps/2.7/tower.ansible.com_*.yaml` (cluster dump) |
| **Role behavior source** | Upstream [`ansible/awx-resource-operator`](https://github.com/ansible/awx-resource-operator) (downstream: platform-resource-operator) |
| **Last updated** | 2026-10-28 |

---

## What this operator does

Resource Operator does nothing until you create a CR. Controllers then call the **platform gateway** API using credentials from a Kubernetes Secret referenced by `spec.connection_secret`, and create / update / launch automation controller resources (projects, inventories, credentials, job templates, workflows, schedules, instance groups, and one-shot jobs).

Typical GitOps order:

1. Platform is up (`AnsibleAutomationPlatform` CR / gateway Route).
2. Create an OAuth2 token for a user that has enough RBAC to manage the target objects.
3. Create the connection Secret (commonly named `aap-access`).
4. Apply Resource Operator CRs that set `connection_secret: aap-access` (same namespace as the Secret unless you use a cluster-wide secret pattern your operator install supports).

---

## Connection secret (`aap-access`)

The published **custom resources** page shows a minimal Secret example but does not explain how to mint the token or which scopes to pick. The **install** guide covers that; this section merges both.

### Required Secret keys

| Key | Required | Description |
|-----|----------|-------------|
| `token` | Yes | OAuth2 access token string (shown **once** at creation time). |
| `host` | Yes | Base URL the operator can reach. Docs show the external gateway Route. No `ssl_verify` / `verify_ssl` key -- TLS verification is **hardcoded off** in the operator (`TOWER_VERIFY_SSL` / `CONTROLLER_VERIFY_SSL` = `False`). |

There is **no** documented way to enable TLS verify via this Secret.

### What can go in `host`?

Any URL the Resource Operator pods can resolve and reach. Verified patterns:

| Style | Example (AAP CR named `aap` in ns `aap`) | When to use |
|-------|------------------------------------------|-------------|
| External Route FQDN | `https://aap-aap.apps.example.com` | Default / safest; works across namespaces if the Route is reachable |
| In-cluster HTTP Service | `http://aap` or `http://aap.aap.svc.cluster.local` | Same ns (short name) or FQDN; day-2 tests use `http://aap`. Service port **80** |
| In-cluster HTTP API Service | `http://aap-api.aap.svc.cluster.local` | Gateway operator uses this for management API |
| In-cluster HTTPS (TLS on) | `https://aap-gateway-internal.aap.svc.cluster.local:8446` | Private envoy Service; verify already disabled |

Prefer matching scheme to the Service (do not put `https://` on a plain port-80 ClusterIP unless TLS is actually terminated there).

Example (name is conventional, not hard-coded -- every CR's `connection_secret` must match this `metadata.name`):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aap-access
  namespace: aap   # same namespace as your Resource Operator CRs
type: Opaque
stringData:
  token: "<paste-oauth2-token-once>"
  host: "https://aap-aap.apps.example.com"
```

Apply:

```shell
oc apply -f aap-access-secret.yml -n aap
```

### Create the OAuth2 token (UI)

You can only create OAuth2 tokens for **your own** user (API or UI).

1. Log in to the **platform UI** (gateway).
2. **Access Management → Users** → select your user.
3. **Tokens → Automation Execution → Create Token**.
4. Leave **Application** empty for a personal access token (PAT).
5. Add a description; set **Scope** to **Write** if CRs will create/update/launch resources (Read is insufficient for most Resource Operator CRs).
6. Copy the token immediately; later GETs return a redacted / encrypted placeholder.

Scopes implemented in gateway/DAB OAuth2: `read`, `write`, `openid`, `roles` (`aap-27/common/django-ansible-base/ansible_base/oauth2_provider/models/access_token.py`).

### Create the OAuth2 token (API)

Gateway mounts DAB OAuth2 under `/api/gateway/v1/` (`tokens` ViewSet). Example PAT create (session or existing auth; adjust host/credentials):

```shell
# After authenticating to the gateway (session cookie or existing bearer token):
curl -sk -X POST "https://my-aap-gateway.example.com/api/gateway/v1/tokens/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <existing-or-session>" \
  -d '{"description":"resource-operator","scope":"write"}'
```

On `POST`, the response includes the plaintext `token` **once**. Store it in the Secret; do not commit it.

### Deprecated auth field on some CRs

Several CRs still accept `spec.tower_auth_secret` with the same meaning as `connection_secret`. CRD descriptions mark it **DEPRECATED**. Prefer `connection_secret`.

### Operational notes

- Prefer gateway (platform) URL, not a raw controller-only Service, on AAP 2.5+ platform installs.
- Token user RBAC must allow the operations the CRs perform (org admin / appropriate roles).
- Put the Secret in the **same namespace** as the CRs unless your operator docs say otherwise.
- Rotate by creating a new token, updating the Secret, and deleting old tokens in the UI.

---

## Practically required fields (CRD vs role)

OpenAPI `required:` on the CRD is **not** the full story. Ansible Operator only injects fields present on the CR. Role code that templates `{{ description }}` (no `default(omit)`) fails with `'description' is undefined` if you omit the field -- even when the CRD marks it optional and published docs treat it as optional.

| Kind | CRD `required` | Also required in practice (role / runner) | Notes |
|------|----------------|-------------------------------------------|--------|
| `AnsibleInventory` | `name`, `organization` | **`description`**, `connection_secret` | Omit `description` → create task fails (`'description' is undefined`); status then often shows a misleading `inventory.changed` error |
| `AnsibleProject` | `connection_secret`, `name`, `organization`, `scm_type` | -- | `description` is optional in the Job env template (`{% if description is defined %}`) |
| `AnsibleCredential` | `connection_secret`, `name`, `organization`, `type` | credential material for the chosen type | `description` optional in Job env; SSH needs `ssh_secret` (+ `ssh_username`); generic path needs `inputs` |
| `AnsibleSchedule` | `connection_secret`, `name`, `rrule`, `unified_job_template` | -- | Matches CRD |
| `WorkflowTemplate` | `connection_secret`, `name`, `organization`, `inventory`, `workflow_nodes` | `name`, `organization`, `workflow_nodes` in role | Role uses `inventory \| default(omit)` and `description \| default(omit)`; still set `inventory` if CRD validation enforces it |
| `JobTemplate` | _(none)_ | `name` **or** `job_template_name`; `inventory`/`project`/`playbook` (or deprecated `job_template_*`) | Role uses `name \| default(job_template_name)` etc.; omitting both sides of a pair fails |
| `AnsibleJob` | _(none)_ | `connection_secret`; **`job_template_name` or `workflow_template_name`** | Role asserts at least one template name is set |
| `AnsibleWorkflow` | `connection_secret` | `workflow_template_name` in practice | Needed to launch |
| `AnsibleInstanceGroup` | `connection_secret`, `name` | -- | Extra fields gated with `default(omit, true)` in runner |

### Misleading Failure status (inventory)

When a module task fails during **argument templating** (e.g. undefined `description`) with `ignore_errors: true`, the register often lacks `changed`. The next task then fails evaluating `when: inventory.changed`, and that secondary message is what lands in `status.conditions[Failure].message`.

**Always check operator logs** for the real first error:

```shell
oc logs -n aap deploy/resource-operator-controller-manager --tail=200 \
  | grep -E "undefined|FAILED|AnsibleInventory"
```

Example: first error was `'description' is undefined`; CR status only showed the `inventory.changed` conditional failure. Adding `spec.description` made reconcile succeed (`message: Inventory Created`).

---

## CR inventory (`tower.ansible.com/v1alpha1`)

| Kind | Purpose | CRD required `spec` fields (2.7 dump) |
|------|---------|----------------------------------------|
| `AnsibleJob` | Launch a job or workflow template | _(none marked required)_ |
| `JobTemplate` | Create a job template | _(none marked required)_ |
| `AnsibleProject` | Create a project | `connection_secret`, `name`, `organization`, `scm_type` |
| `AnsibleInventory` | Create / manage an inventory | `name`, `organization` (+ **`description` in practice**) |
| `AnsibleCredential` | Create a credential | `connection_secret`, `name`, `organization`, `type` |
| `AnsibleSchedule` | Create a schedule | `connection_secret`, `name`, `rrule`, `unified_job_template` |
| `AnsibleWorkflow` | Launch / manage a workflow run | `connection_secret` |
| `WorkflowTemplate` | Create a workflow job template | `connection_secret`, `name`, `organization`, `inventory`, `workflow_nodes` |
| `AnsibleInstanceGroup` | Create an instance / container group | `connection_secret`, `name` |

Status on these CRDs is unstructured (`x-kubernetes-preserve-unknown-fields: true`). Inspect with `oc describe` / `oc get <kind> -o yaml`.

---

## Shared runner fields

Many CRs accept optional runner overrides used by the operator’s reconcile pods:

| Field | Type | Notes |
|-------|------|--------|
| `runner_image` | string | Image for the runner pod |
| `runner_version` | string | Image tag / version |
| `runner_pull_policy` | string | e.g. `Always`, `Never`, `IfNotPresent` (docs often default `IfNotPresent`) |

---

## AnsibleJob

Launches a job template or workflow job template.

| Field | Type | In published table? | Notes |
|-------|------|---------------------|--------|
| `connection_secret` | string | Yes | Preferred auth Secret name |
| `tower_auth_secret` | string | **No** | Deprecated alias of `connection_secret` |
| `job_template_name` | string | Yes | **Practically required** unless `workflow_template_name` is set (role asserts one of them) |
| `workflow_template_name` | string | Yes | Mutual with `job_template_name` |
| `inventory` | string | Yes | Template must allow prompt-on-launch for inventory when overriding |
| `extra_vars` | object | Yes | Same for variables |
| `job_tags` | string | Yes | Comma-separated |
| `skip_tags` | string | Yes | Comma-separated |
| `runner_image` / `runner_version` / `runner_pull_policy` | string | Partial | `runner_pull_policy` omitted from published table |
| `job_ttl` | integer | Yes | TTL (seconds) for the K8s Job after completion |
| `request_timeout` | integer | **No** | Seconds to wait when polling job status via API |

**Example:**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleJob
metadata:
  generateName: demo-job-
spec:
  connection_secret: aap-access
  job_template_name: Demo Job Template
  inventory: Demo Inventory
  extra_vars:
    test_var: test
  job_tags: "provision,install"
  request_timeout: 120
```

---

## JobTemplate

Creates a job template. Published docs use **deprecated** field names; the CRD prefers the short names. CRD lists **no** required fields, but the role needs a name + inventory + project + playbook via either naming style.

| Field | Type | Prefer | Notes |
|-------|------|--------|--------|
| `connection_secret` | string | -- | Auth |
| `tower_auth_secret` | string | avoid | Deprecated |
| `name` | string | **yes** | Display name (**or** `job_template_name`) |
| `project` | string | **yes** | Associated project (**or** `job_template_project`) |
| `playbook` | string | **yes** | Playbook path (**or** `job_template_playbook`) |
| `inventory` | string | **yes** | Associated inventory (**or** `job_template_inventory`) |
| `ask_inventory_on_launch` | boolean | **yes** | Prompt inventory |
| `ask_variables_on_launch` | boolean | **yes** | Prompt extra vars |
| `job_template_name` | string | deprecated | Use `name` |
| `job_template_project` | string | deprecated | Use `project` |
| `job_template_playbook` | string | deprecated | Use `playbook` |
| `job_template_inventory` | string | deprecated | Use `inventory` |
| `job_template_ask_inventory` | boolean | deprecated | Use `ask_inventory_on_launch` |
| `job_template_ask_vars` | boolean | deprecated | Use `ask_variables_on_launch` |

**Example (preferred field names):**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: JobTemplate
metadata:
  name: jobtemplate-demo
spec:
  connection_secret: aap-access
  name: ExampleJobTemplate
  project: Demo Project
  playbook: hello_world.yml
  inventory: Demo Inventory
  ask_variables_on_launch: true
```

Published docs still show the deprecated `job_template_*` form; both work until removed.

---

## AnsibleProject

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `connection_secret` | string | Yes | |
| `name` | string | Yes | Display name in controller |
| `organization` | string | Yes | |
| `scm_type` | string | Yes | e.g. `git` |
| `repo` | string | | SCM URL |
| `branch` | string | | SCM branch |
| `description` | string | | |
| `scm_credential` | string | **Missing from published table** | Credential name for private SCM |
| `runner_image` / `runner_version` / `runner_pull_policy` | string | | Optional |

**Example:**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleProject
metadata:
  name: project-demo-git
spec:
  connection_secret: aap-access
  name: ProjectDemo-git
  organization: Default
  scm_type: git
  repo: https://github.com/ansible/ansible-tower-samples
  branch: main
  # scm_credential: my-scm-cred   # when repo is private
```

---

## AnsibleInventory

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `name` | string | Yes | Display name in controller |
| `organization` | string | Yes | Name, ID, or named URL |
| `description` | string | **Yes in practice** | Role uses `description: "{{ description }}"` with **no** `default(omit)`. Omitting it fails create (`'description' is undefined`). CRD/docs mark it optional -- set it anyway (empty string is fine) |
| `connection_secret` | string | Yes in practice | Auth Secret name |
| `state` | string | | `present` (default), `absent`, or `exists` (CRD enum; published docs omit `exists`) |
| `instance_groups` | string[] | | Instance group names/IDs/named URLs |
| `variables` | object | | Inventory vars (nested objects allowed) |
| `copy_from` | string | **Missing from published table** | Copy existing inventory by name/id, then apply overrides; new name is `name` |

**Example:**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleInventory
metadata:
  name: inventory-new
spec:
  connection_secret: aap-access
  name: newinventory
  organization: Default
  description: "my inventory"   # required by role even if CRD says optional
  state: present
  variables:
    env: production
    region: us-east-1
```

---

## AnsibleCredential

**Docs vs CRD mismatch:** the published reference lists `username_secret` / `password_secret`. Those fields are **not** in the 2.7 CRD dump. Use the fields below.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `connection_secret` | string | Yes | |
| `name` | string | Yes | |
| `organization` | string | Yes | |
| `type` | string | Yes | Credential type label, e.g. `Machine`, `Amazon Web Services`, `OpenShift or Kubernetes API Bearer Token` |
| `description` | string | | |
| `ssh_username` | string | | Machine / SSH |
| `ssh_secret` | string | | Name of a K8s Secret holding the SSH private key material (exact key names: verify against operator samples -- not typed in CRD) |
| `inputs` | string | **Missing from published table** | Credential inputs payload (string; often JSON for cloud / generic types) |
| `kubernetes_api` | string | **Missing** | API URL for OpenShift/K8s bearer credentials |
| `kubernetes_bearer_token_secret` | string | **Missing** | K8s Secret name with the bearer token |
| `runner_*` | string | | Optional |

**Example (Machine / SSH):**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleCredential
metadata:
  name: ssh-cred
spec:
  connection_secret: aap-access
  name: ssh-cred
  organization: Default
  type: "Machine"
  ssh_username: "ansible"
  ssh_secret: my-ssh-secret
```

---

## AnsibleSchedule

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `connection_secret` | string | Yes | |
| `name` | string | Yes | |
| `rrule` | string | Yes | iCal RRULE, e.g. `DTSTART:20210101T000000Z RRULE:FREQ=DAILY;INTERVAL=1;COUNT=1` |
| `unified_job_template` | string | Yes | Job or workflow template name |
| `runner_*` | string | | Optional (`runner_image` / `runner_version` omitted from published table) |

**Example:**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleSchedule
metadata:
  name: schedule-demo
spec:
  connection_secret: aap-access
  name: "Demo Schedule"
  rrule: "DTSTART:20210101T000000Z RRULE:FREQ=DAILY;INTERVAL=1;COUNT=1"
  unified_job_template: "Demo Job Template"
```

---

## AnsibleWorkflow

Launches / drives a workflow (distinct from defining a `WorkflowTemplate`).

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `connection_secret` | string | Yes | |
| `workflow_template_name` | string | | |
| `inventory` | string | | |
| `extra_vars` | object | **Missing from published table** | |
| `request_timeout` | integer | **Missing** | API poll timeout (seconds) |
| `runner_*` | string | | Optional |

**Example:**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleWorkflow
metadata:
  name: workflow-run
spec:
  connection_secret: aap-access
  workflow_template_name: ExampleTowerWorkflow
  inventory: Demo Inventory
```

---

## WorkflowTemplate

Defines a workflow job template graph.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `connection_secret` | string | Yes | CRD description text still says “username and password”; actual Secret is `token` + `host` |
| `name` | string | Yes | |
| `organization` | string | Yes | |
| `inventory` | string | Yes | |
| `workflow_nodes` | array | Yes | Required in CRD; **not listed in OpenAPI properties** -- `spec` has `x-kubernetes-preserve-unknown-fields: true`, so the field is accepted but untyped in the dump |
| `description` | string | | |
| `extra_vars` | object | **Missing from published table** | |
| `job_tags` / `skip_tags` / `limit` / `labels` | string | **Missing** | |
| `allow_simultaneous` | boolean | **Missing** | |
| `ask_*_on_launch` | boolean | **Missing** | `ask_inventory_on_launch`, `ask_variables_on_launch`, `ask_tags_on_launch`, `ask_skip_tags_on_launch`, `ask_limit_on_launch`, `ask_labels_on_launch`, `ask_scm_branch_on_launch` |
| `survey_enabled` | boolean | **Missing** | |
| `survey_spec` | object | **Missing** | Unstructured |
| `state` | string | **Missing** | |

**Example (from published docs; still valid):**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: WorkflowTemplate
metadata:
  name: workflowtemplate-sample
spec:
  connection_secret: aap-access
  name: ExampleWorkflow
  organization: Default
  inventory: Demo Inventory
  workflow_nodes:
  - identifier: node101
    unified_job_template:
      name: Demo Job Template
      type: job_template
  - identifier: node102
    unified_job_template:
      name: Demo Job Template
      type: job_template
```

Node shape (from published docs; not OpenAPI-validated in the CRD dump): each entry has `identifier` plus `unified_job_template` with `name`, `type`, and optionally `inventory`.

---

## AnsibleInstanceGroup

Published docs only list `name` + `runner_pull_policy`. CRD supports full instance-group and container-group options.

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `connection_secret` | string | Yes | |
| `name` | string | Yes | |
| `is_container_group` | boolean | | Default `false` -- InstanceGroup; `true` -- ContainerGroup |
| `credential_name` | string | | OpenShift/K8s API Bearer Token credential; **ContainerGroup only** |
| `pod_spec_override` | string | | Custom Pod spec YAML/JSON string; **ContainerGroup only** |
| `instance_list` | string[] | | Instance names/IDs; **InstanceGroup only** |
| `policy_instance_minimum` | integer | | **InstanceGroup only** |
| `policy_instance_percentage` | integer | | **InstanceGroup only** |
| `max_concurrent_jobs` | integer | | `0` = unlimited |
| `max_forks` | integer | | `0` = unlimited |
| `policy_spec_override` | string | | **DEPRECATED** |
| `runner_*` | string | | Optional |

**Example (plain instance group):**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleInstanceGroup
metadata:
  name: my-instance-group
spec:
  connection_secret: aap-access
  name: production-instances
  is_container_group: false
  max_concurrent_jobs: 10
```

**Example sketch (container group -- credential + pod override):**

```yaml
apiVersion: tower.ansible.com/v1alpha1
kind: AnsibleInstanceGroup
metadata:
  name: my-container-group
spec:
  connection_secret: aap-access
  name: ocp-ee-group
  is_container_group: true
  credential_name: "My OpenShift Cred"
  # pod_spec_override: |
  #   apiVersion: v1
  #   kind: Pod
  #   ...
```

---

## Gaps vs published reference (checklist)

| Topic | Published CR page | This note / CRD / roles |
|-------|-------------------|-------------------------|
| How to create OAuth token | Almost absent (Secret YAML only) | UI + API + scopes |
| Secret key contract (`token`, `host`) | Shown in example | Documented + ops notes |
| TLS verify / `ssl_verify` on Secret | Absent | **Not configurable** -- operator hardcodes verify off |
| Internal vs Route `host` URLs | External HTTPS example only | Route, ClusterIP HTTP, gateway-internal HTTPS |
| `tower_auth_secret` deprecation | Absent | Documented |
| `JobTemplate` preferred field names | Only deprecated names | Both |
| Practically required fields vs CRD | Incomplete | Table above; **`AnsibleInventory.description` required by role** |
| Misleading `inventory.changed` Failure | Absent | Documented (secondary error after undefined vars) |
| `AnsibleProject.scm_credential` | Absent | Documented |
| `AnsibleInventory.copy_from`, `state=exists` | Absent / incomplete | Documented |
| `AnsibleCredential.inputs` / K8s fields | Wrong (`username_secret` / `password_secret`) | CRD fields; runner also supports username/password/token secret env paths |
| `AnsibleJob` / `AnsibleWorkflow` `request_timeout`, `extra_vars` | Partial | Complete |
| `WorkflowTemplate` ask/survey/limit fields | Absent | From CRD |
| `AnsibleInstanceGroup` container group | Absent | From CRD |
| Status schema | Absent | Unstructured -- use `oc` |

---

## Quick validation

```shell
# CRDs present
oc get crd | grep tower.ansible.com

# Secret keys
oc get secret aap-access -n aap -o jsonpath='{.data}' | jq 'keys'

# After applying a CR
oc get ansibleprojects,jobtemplates,ansibleinventories -n aap
oc describe ansibleproject <name> -n aap
```

If reconcile fails with 401/403, re-check token scope (`write`), token user RBAC, and that `host` points at the gateway Route.

---

## Related local notes

- Platform install examples: [README.md](README.md), [secrets-aap.yml](secrets-aap.yml), [aap.yml](aap.yml)
- CRD dumps: `../../.crd-dumps/2.7/tower.ansible.com_*.yaml`
- Same content for 2.6 (schemas match): [../AAP26/resource-operator-custom-resources.md](../AAP26/resource-operator-custom-resources.md)
