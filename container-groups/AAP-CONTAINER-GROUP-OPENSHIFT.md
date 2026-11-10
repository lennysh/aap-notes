# Adding an OpenShift Container Group to AAP

This guide lets Ansible Automation Platform (AAP) run jobs as **temporary pods on an OpenShift cluster**. That setup is called a **Container Group**. It is written for teams doing this for the first time, where **different people own different parts**: OpenShift, network, and AAP.

It works with any AAP install type (RPM, containerized, or Operator) and AAP **2.4 through 2.7**. Where the UI differs by version, both versions are shown.

---

## Contents

- [How it works](#how-it-works)
- [Who does what](#who-does-what)
- [Step 0 — Kickoff (everyone)](#step-0--kickoff-everyone)
- [Part 1 — OpenShift team](#part-1--openshift-team)
- [Part 2 — Network / firewall team](#part-2--network--firewall-team)
- [Part 3 — AAP administrator](#part-3--aap-administrator)
- [Part 4 — Test together](#part-4--test-together)
- [Troubleshooting](#troubleshooting)
- [Ongoing maintenance](#ongoing-maintenance)
- [Appendix A — Version differences](#appendix-a--version-differences)
- [Appendix B — Configuration as code](#appendix-b--configuration-as-code)
- [Appendix C — Source references](#appendix-c--source-references)

---

## How it works

```
 ┌──────────────────────┐  HTTPS :6443 (bearer token)   ┌────────────────────────────────┐
 │ AAP control / hybrid │ ───────────────────────────▶ │ OpenShift API server           │
 │ node (or controller  │  create pod, stream output,   │                                │
 │ task pod)            │  delete pod                   │ namespace: aap-container-group │
 └──────────────────────┘                               │  └─ pod: automation-job-<id>   │
                                                        │       image = job's EE ────────┼──▶ container registry
                                                        │       runs playbook ───────────┼──▶ managed hosts
                                                        └────────────────────────────────┘
```

1. A user launches a job in AAP that is assigned to the container group.
2. AAP connects to the **OpenShift API** with a **service account token** and creates a pod in the chosen **namespace**. The pod's image is the job's **Execution Environment (EE)**.
3. The playbook runs inside the pod. Output streams back to AAP **through the OpenShift API**. The pod never connects back to AAP.
4. When the job finishes, AAP deletes the pod.

Things to know up front:

- **Only AAP control/hybrid nodes talk to OpenShift.** Execution and hop nodes are not involved.
- The **service account token is used only by AAP** to manage pods. The job pod itself runs as the namespace's `default` service account, with no token mounted.
- The service account's permissions are **limited to one namespace**. It has no cluster-wide access.
- **Project syncs still run in AAP.** Only jobs (and inventory syncs, if you assign them) run on OpenShift.

---

## Who does what

| Step | Owner | Needs from others | Hands off |
|------|-------|-------------------|-----------|
| [0. Kickoff](#step-0--kickoff-everyone) | Everyone | — | Filled-in [planning worksheet](#planning-worksheet) |
| [1. OpenShift prep](#part-1--openshift-team) | OpenShift / platform team | Planning worksheet | [OpenShift handoff](#14-hand-off-to-the-aap-administrator): API URL, token, CA cert, namespace |
| [2. Network prep](#part-2--network--firewall-team) | Network / firewall team | Addresses from the planning worksheet | Firewall rules open, tests pass |
| [3. AAP setup](#part-3--aap-administrator) | AAP administrator | OpenShift handoff; Part 2 done | Container group ready |
| [4. Test](#part-4--test-together) | AAP admin + OpenShift team | Parts 1–3 done | Working job |

Parts 1 and 2 can be done at the same time.

---

## Step 0 — Kickoff (everyone)

Fill in this worksheet together before anyone starts. Most failures in a first setup come from one team not knowing a value another team chose.

### Planning worksheet

| # | Question | Decided by | Answer |
|---|----------|------------|--------|
| 1 | AAP version (2.4, 2.5, 2.6, 2.7) | AAP admin | |
| 2 | OpenShift cluster API URL (`https://api.<cluster>.<domain>:6443`) | OpenShift team | |
| 3 | Namespace (project) for job pods — this guide uses `aap-container-group` | OpenShift team | |
| 4 | Service account name — this guide uses `aap-container-group-sa` | OpenShift team | |
| 5 | Name for the container group in AAP — e.g. `ocp-prod-east` | AAP admin | |
| 6 | Which EE images will jobs use, and which registry are they in (Private Automation Hub, `registry.redhat.io`, Quay, etc.)? | AAP admin | |
| 7 | Do those registries need a login? Who provides it? | AAP admin + registry owner | |
| 8 | Does the namespace need CPU/memory **limits**, a **node selector**, or **tolerations**? | OpenShift team | |
| 9 | Hostnames/IPs of AAP **control or hybrid** nodes (or the OpenShift cluster/egress IPs if AAP runs on the Operator) | AAP admin | |
| 10 | What do the playbooks connect to (managed host networks, ports, external APIs)? | AAP admin / automation owners | |
| 11 | How will the token be sent securely from the OpenShift team to the AAP admin (vault, password manager, etc.)? | Everyone | |

> **Different names?** If you use a different namespace or service account name, replace `aap-container-group` and `aap-container-group-sa` **everywhere** in this guide, including inside the YAML files.

---

## Part 1 — OpenShift team

**Goal:** Create a namespace and a service account that AAP can use to run pods there. Then hand over four pieces of information.

**You need:** `oc` CLI access with permission to create projects and RBAC in the target namespace. Cluster admin isn't required if you're a project admin there.

Set these at the start of your shell session (use the names from the worksheet):

```bash
export NS=aap-container-group
export SA=aap-container-group-sa
```

### 1.1 Create the namespace

```bash
oc new-project "$NS" --display-name="AAP Container Group"
```

### 1.2 Create the service account and its permissions

This creates three things:

- **ServiceAccount:** the identity AAP logs in as.
- **Role:** what that identity can do in this namespace only.
- **RoleBinding:** connects the two.

Save as `aap-container-group-rbac.yml`:

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: aap-container-group-sa
  namespace: aap-container-group
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: aap-container-group-role
  namespace: aap-container-group
rules:
  # Create, watch, and clean up job pods
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  # Read job output
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["pods/attach"]
    verbs: ["create"]
  # Let AAP create image pull secrets for EEs that have a registry credential
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "create", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: aap-container-group-rolebinding
  namespace: aap-container-group
subjects:
  - kind: ServiceAccount
    name: aap-container-group-sa
    namespace: aap-container-group
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: aap-container-group-role
```

Apply it:

```bash
oc apply -f aap-container-group-rbac.yml
```

These are the same permissions the AAP Operator gives its own built-in container group.

> **About the `secrets` rule:** If the AAP admin attaches a registry login to an EE, AAP creates an image pull secret in this namespace so OpenShift can pull the image. The secret is named `automation-<id>-image-pull-secret-<id>`. If your security policy doesn't allow this, remove the rule and use [option B in Part 3.3](#33-make-sure-openshift-can-pull-the-ee-images) instead.

**Check the permissions.** Every line should print `yes`:

```bash
for v in "create pods" "delete pods" "get pods/log" "create pods/attach" "create secrets"; do
  echo -n "$v: "; oc auth can-i $v -n "$NS" --as="system:serviceaccount:$NS:$SA"
done
```

### 1.3 Create a long-lived token and collect the connection details

On OpenShift 4.11 and later, you must create the token yourself. Save as `aap-container-group-sa-token.yml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aap-container-group-sa-token
  namespace: aap-container-group
  annotations:
    kubernetes.io/service-account.name: aap-container-group-sa
type: kubernetes.io/service-account-token
```

```bash
oc apply -f aap-container-group-sa-token.yml

# Wait a few seconds for OpenShift to fill in the token, then:

# 1) API URL
oc whoami --show-server

# 2) Token
oc get secret aap-container-group-sa-token -n "$NS" -o jsonpath='{.data.token}' | base64 -d > aap-cg.token

# 3) CA certificate
oc get secret aap-container-group-sa-token -n "$NS" -o jsonpath='{.data.ca\.crt}' | base64 -d > aap-cg-ca.crt
```

> **Don't use `oc create token`.** Those tokens **expire**, and the container group would stop working with no warning. A token created this way lasts until the secret is deleted.

> **Custom API certificate?** If your cluster's API uses a certificate from your company CA (check `oc get apiserver cluster -o yaml` → `spec.servingCerts.namedCertificates`), send **your company CA chain** instead of `aap-cg-ca.crt`. Either way, the test below tells you whether the CA is right.

**Test the token and CA.** Run this from any machine that can reach the API:

```bash
curl --cacert aap-cg-ca.crt \
     -H "Authorization: Bearer $(cat aap-cg.token)" \
     "$(oc whoami --show-server)/api/v1/namespaces/$NS/pods"
```

| Result | Meaning |
|--------|---------|
| JSON containing `"kind": "PodList"` (`"items": []` is fine) | ✅ Token, CA, and permissions all work |
| `401 Unauthorized` | Token is wrong. Check you copied the whole token. |
| `403 Forbidden` | RBAC or namespace mismatch. Re-run the 1.2 check. |
| `SSL certificate problem` / `x509` | Wrong CA. See the custom-certificate note above. |

### 1.4 Hand off to the AAP administrator

Send these through the secure channel agreed in the worksheet. **Never put the token in a ticket, email, or chat.**

| Item | Example |
|------|---------|
| API URL | `https://api.ocp.example.com:6443` |
| Token | contents of `aap-cg.token` — **secret** |
| CA certificate | contents of `aap-cg-ca.crt` (text starting `-----BEGIN CERTIFICATE-----`) |
| Namespace | `aap-container-group` |
| Required CPU/memory limits, node selector, tolerations | if any (worksheet #8) |
| Was the `secrets` rule included? | yes / no |

Then delete the local `aap-cg.token` file.

### 1.5 (Optional) Namespace policies to review

- **Quotas:** The default job pod **requests** `250m` CPU and `100Mi` memory and sets **no limits**. If the namespace has a ResourceQuota or LimitRange that requires limits, pods will be rejected. Give the AAP admin the limits to use.
- **Network policies / egress firewall:** Job pods need outbound access to managed hosts and anything playbooks call. See Part 2.
- **Security Context Constraints:** The default job pod works under the standard `restricted-v2` SCC. You don't need to change anything.

---

## Part 2 — Network / firewall team

**Goal:** Allow these connections. Nothing needs to connect **into** AAP from OpenShift.

| # | From | To | Port | Why |
|---|------|----|------|-----|
| 1 | **AAP control / hybrid nodes** (worksheet #9) | OpenShift API (`api.<cluster>.<domain>`) | TCP **6443** | AAP creates and watches pods and receives job output |
| 2 | OpenShift worker nodes | Registries holding EE images (worksheet #6) | TCP 443 | Pull EE images |
| 3 | OpenShift job pods (cluster egress) | Managed hosts | 22 (SSH), 5985/5986 (WinRM), others as needed | The automation itself |
| 4 | OpenShift job pods (cluster egress) | Anything playbooks call (worksheet #10) | As needed | Playbook dependencies |

> **Where AAP's traffic comes from:** On RPM installs, the control/hybrid hosts. On containerized installs, the hosts running the controller containers. If AAP is installed by the Operator on **another** cluster, traffic comes from that cluster's egress IPs.

**Test rule #1** from each AAP control/hybrid node:

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://api.ocp.example.com:6443/version
```

Any HTTP code (`200`, `401`, `403`) means the network path works. A timeout or "connection refused" means it's blocked.

---

## Part 3 — AAP administrator

**Goal:** Store the OpenShift connection details in AAP, create the container group, and point jobs at it.

**You need:** the [OpenShift handoff](#14-hand-off-to-the-aap-administrator), confirmation that Part 2 is done, and AAP admin access.

UI paths differ by version:

| | AAP 2.4 | AAP 2.5 and later |
|---|---------|-------------------|
| Credentials | **Resources → Credentials** | **Automation Execution → Infrastructure → Credentials** |
| Instance groups | **Administration → Instance Groups** | **Automation Execution → Infrastructure → Instance Groups** |
| Execution environments | **Administration → Execution Environments** | **Automation Execution → Infrastructure → Execution Environments** |

### 3.1 Create the OpenShift credential

Go to **Credentials → Add / Create credential**:

| Field | Value |
|-------|-------|
| Name | e.g. `OpenShift - ocp-prod-east container group` |
| Organization | **Leave blank** (recommended). This does *not* make it global: it makes the credential private to you and system administrators. That is fine here, because only system administrators can manage container groups, and jobs use the container group without users needing access to the credential. Blank also keeps the token visible to the fewest people. |
| Credential type | **OpenShift or Kubernetes API Bearer Token** |
| OpenShift or Kubernetes API Endpoint | **API URL** from the handoff (the `:6443` URL, *not* the web console URL) |
| API authentication bearer token | **Token** from the handoff |
| Verify SSL | ✅ leave **checked** |
| Certificate Authority data | **CA certificate** from the handoff. Paste the whole thing, including the `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----` lines. |

Save.

### 3.2 Create the container group

Go to **Instance Groups**, then:

- 2.4: **Add → Add container group**
- 2.5+: **Create group → Create container group**

1. **Name:** the name from worksheet #5.
2. **Credential:** choose the credential from 3.1.
3. **Max concurrent jobs** / **Max forks:** leave at `0` (no limit) for now. You can set caps later to protect the cluster.
4. Check the pod spec box:
   - 2.4: **Customize pod specification**
   - 2.5+: **Customize pod spec**

   A YAML editor appears.
5. **⚠️ Change the namespace. This is the step most often missed.** The editor is pre-filled with AAP's own default. Look for:

   ```yaml
   metadata:
     namespace: <something>
   ```

   That value is **AAP's** namespace: the namespace AAP itself runs in (Operator installs) or `default` (RPM/containerized). It is **not** the namespace the OpenShift team created. **Replace it** with the namespace from the handoff:

   ```yaml
   metadata:
     namespace: aap-container-group
   ```

   If you skip this, jobs fail with a "pods is forbidden … in the namespace "<AAP's namespace>"" error.
6. **Only if the OpenShift team gave you limits, node selector, or tolerations** (handoff), add them. Example:

   ```yaml
   spec:
     containers:
       - name: worker
         resources:
           requests:
             cpu: 250m
             memory: 100Mi
           limits:
             cpu: '1'
             memory: 1Gi
     nodeSelector:
       node-role.kubernetes.io/worker: ''
   ```
7. Leave everything else as it is, then **Save**.

What the pre-filled YAML does (so you know what's safe to change):

- **`image:`** is **ignored**. AAP always uses the job's EE image. Choose EEs on the Job Template instead.
- **`serviceAccountName: default`** and **`automountServiceAccountToken: false`**: the pod runs with no token. Leave these alone.
- You only need to keep the fields you want to change. Anything you delete falls back to AAP's built-in default.

### 3.3 Make sure OpenShift can pull the EE images

OpenShift, not AAP, pulls the EE image. Check every EE that jobs on this container group will use (worksheet #6):

| Where the EE image lives | What to do |
|--------------------------|------------|
| `registry.redhat.io` | Usually nothing. OpenShift's cluster-wide pull secret already includes Red Hat registry access. |
| Private Automation Hub, Quay, or another private registry | Use **option A** (recommended) or **option B** below |
| Public registry, no login | Nothing |

**Option A (recommended): attach a registry credential to the EE in AAP.**
1. **Credentials → Add / Create credential**, type **Container Registry**. Enter the registry host (e.g. `quay.io` or your Hub hostname) and a username/password or token with **read** access. Use a robot/service account where possible.
2. **Execution Environments → (your EE) → Edit → Registry credential** → choose that credential → Save.

AAP then creates the pull secret in the namespace automatically. This needs the `secrets` rule from Part 1.2.

**Option B: the OpenShift team creates the pull secret.** Use this if the `secrets` rule wasn't allowed:

```bash
oc create secret docker-registry aap-ee-pull \
   --docker-server=<registry> --docker-username=<user> --docker-password=<token> -n aap-container-group
oc secrets link default aap-ee-pull --for=pull -n aap-container-group
```

### 3.4 Send jobs to the container group

Add the container group under **Instance groups** on any of these:

- a **Job Template** (most specific — good for testing),
- an **Inventory**, or
- an **Organization**.

Jobs use the first instance group that has capacity. For testing, put the container group on **one** Job Template so you know where the job will run.

---

## Part 4 — Test together

Do this on a shared call with the OpenShift team and the AAP admin.

1. **AAP admin:** create or choose a simple Job Template:
   - A playbook that runs `ansible.builtin.ping` against `localhost`
   - An EE whose image is known to exist and be pullable (e.g. the default supported EE)
   - Instance group set to the new container group only
2. **OpenShift team:** watch the namespace:
   ```bash
   oc get pods -n aap-container-group -w
   ```
3. **AAP admin:** launch the job.
4. **Expected:**
   - A pod named `automation-job-<job id>-…` appears, goes `Pending → Running`, and is deleted when the job finishes.
   - The job shows **Successful** in AAP, and its details list the container group as the **Instance Group**.
5. Then try a real playbook against real managed hosts. This tests network rules #3 and #4.

---

## Troubleshooting

Find the error in the **AAP job output** (look for "Receptor detail") or in **OpenShift** (`oc get events -n aap-container-group`, `oc describe pod <pod>`).

| What you see | Where | Cause | Fix | Owner |
|--------------|-------|-------|-----|-------|
| `pods is forbidden: User "system:serviceaccount:aap-container-group:aap-container-group-sa" cannot create resource "pods" ... in the namespace "<AAP's namespace or default>"` | AAP job | The pod spec namespace wasn't changed | [3.2 step 5](#32-create-the-container-group): set `metadata.namespace` to the container group namespace | AAP admin |
| Same `forbidden` error but the namespace **is** the right one | AAP job | Role or RoleBinding missing or wrong | Re-run the [1.2 check](#12-create-the-service-account-and-its-permissions) | OpenShift |
| `401` / `Unauthorized` | AAP job | Token wrong, truncated, or the token secret was deleted | Re-run the [1.3 test](#13-create-a-long-lived-token-and-collect-the-connection-details); update the credential | OpenShift → AAP admin |
| `x509: certificate signed by unknown authority` / SSL errors | AAP job | Wrong or missing CA data | [1.3 custom-certificate note](#13-create-a-long-lived-token-and-collect-the-connection-details) | OpenShift → AAP admin |
| Connection timed out / refused to `:6443` | AAP job | Firewall between AAP and the API | [Part 2 rule #1 test](#part-2--network--firewall-team) | Network |
| `ErrImagePull` / `ImagePullBackOff` with `unauthorized` | OpenShift | No registry login for that image, **or the image/tag doesn't exist** (registries such as Quay return `unauthorized` for missing images too) | First check the image and tag exist. Then [3.3](#33-make-sure-openshift-can-pull-the-ee-images). | AAP admin |
| `ErrImagePull` with timeout / no route | OpenShift | Worker nodes can't reach the registry | Part 2 rule #2 | Network |
| AAP warning about failing to create an image pull secret | AAP job | The `secrets` rule is missing | Add it (1.2) or use option B (3.3) | OpenShift |
| Pod stuck in `Pending` | OpenShift | Quota, missing limits, node selector/taint mismatch, or not enough capacity | `oc describe pod` → Events. AAP gives up after **2 hours** by default. | OpenShift |
| Pod rejected (`forbidden: exceeded quota` / `must specify limits`) | OpenShift / AAP job | Namespace requires limits | Add `resources.limits` ([3.2 step 6](#32-create-the-container-group)) | AAP admin |
| Job runs but can't reach managed hosts | AAP job output | Cluster egress, NetworkPolicy, or EgressFirewall | Part 2 rules #3–4 | Network / OpenShift |

**Check what AAP actually saved** (useful for the namespace problem):

```bash
# Pick the API path for your version:
API=https://<aap>/api/v2               # AAP 2.4 (controller URL)
# API=https://<aap>/api/controller/v2  # AAP 2.5+ (platform gateway URL)

curl -s -u <admin>:<password> "$API/instance_groups/?is_container_group=true" \
  | jq '.results[] | {id, name, credential, pod_spec_override}'
```

---

## Ongoing maintenance

| Task | How | Owner |
|------|-----|-------|
| **Rotate the token** | Delete and recreate the `aap-container-group-sa-token` secret (1.3), then paste the new token into the AAP credential. Jobs fail between those two steps, so do it in a quiet period. | OpenShift → AAP admin |
| **OpenShift API certificate changes** | If the API certificate's CA changes, update **Certificate Authority data** in the credential | OpenShift → AAP admin |
| **New EE from a new registry** | Repeat 3.3 for it; tell the network team if it's a new registry host | AAP admin |
| **Limit load on the cluster** | Set **Max concurrent jobs** / **Max forks** on the container group | AAP admin |
| **Leftover pods** | Normally AAP deletes pods. If any `automation-job-*` pods remain after their jobs finished, they can be deleted. | OpenShift |

---

## Appendix A — Version differences

| | AAP 2.4 | AAP 2.5 – 2.7 |
|---|---------|---------------|
| Navigation | Resources / Administration menus | Automation Execution → Infrastructure |
| Create button | Add → Add container group | Create group → Create container group |
| Pod spec checkbox | **Customize pod specification** | **Customize pod spec** |
| Default pod spec shown | Namespace, service account, EE `image`, worker args, CPU/memory requests | Same, plus an `ansible_job` label and anti-affinity that spreads job pods across nodes |
| API base path | `/api/v2/` | `/api/controller/v2/` (through the platform gateway) |
| Credential type and fields | Same in all versions: **OpenShift or Kubernetes API Bearer Token** with endpoint, token, Verify SSL, CA data | |
| Namespace behavior | Same in all versions: you **must** set `metadata.namespace` | |

---

## Appendix B — Configuration as code

Using the `ansible.controller` collection, after Part 1 and Part 2 are done:

The same tasks work on 2.4 and 2.5+. Only the connection target changes: point `controller_host` at the **controller** URL on 2.4, or the **platform gateway** URL on 2.5+.

```yaml
- name: OpenShift credential for the container group
  ansible.controller.credential:
    name: OpenShift - ocp-prod-east container group
    credential_type: OpenShift or Kubernetes API Bearer Token
    inputs:
      host: https://api.ocp.example.com:6443
      bearer_token: "{{ ocp_cg_token }}"        # from a vault, never plain text
      verify_ssl: true
      ssl_ca_cert: "{{ ocp_cg_ca_pem }}"

- name: Container group
  ansible.controller.instance_group:
    name: ocp-prod-east
    is_container_group: true
    credential: OpenShift - ocp-prod-east container group
    pod_spec_override: |
      apiVersion: v1
      kind: Pod
      metadata:
        namespace: aap-container-group
```

---

## Appendix C — Source references

Checked against the AAP 2.4 and 2.7 source trees.

- Credential type `kubernetes_bearer_token` (`host`, `bearer_token`, `verify_ssl`, `ssl_ca_cert`): 2.7 `controller/awx-plugins/src/awx_plugins/credentials/plugins.py`; 2.4 `controller/automation-controller/awx/main/models/credential/__init__.py`
- Default pod spec: `controller/automation-controller/awx/main/utils/execution_environments.py` → `get_default_pod_spec()`
- Default namespace = AAP's own namespace (`MY_POD_NAMESPACE`) or `default`: `controller/automation-controller/awx/settings/defaults.py` → `AWX_CONTAINER_GROUP_DEFAULT_NAMESPACE`; pending timeout `AWX_CONTAINER_GROUP_POD_PENDING_TIMEOUT = "2h"`
- Merge rules, `image`/`args` always replaced, pull policy, pull secret injection: `controller/automation-controller/awx/main/tasks/receptor.py` → `pod_definition`
- Credential present → `kubernetes-runtime-auth` (external API), absent → in-cluster auth: `receptor.py` → `work_type`
- Pull secret create/replace and permission warnings: `controller/automation-controller/awx/main/scheduler/kubernetes.py` → `PodManager.create_secret`
- Operator's equivalent Role: 2.7 `operator/automation-controller-operator/roles/installer/templates/rbac/service_account.yaml.j2`
- UI forms: 2.4 `awx/ui/src/screens/InstanceGroup/shared/ContainerGroupForm.js`; 2.7 `ui/aap-ui/frontend/awx/administration/instance-groups/ContainerGroupForm.tsx`
