# Organization Delete — Gateway + Controller PostgreSQL Behavior (AAP 2.6)

Support / engineering reference for accidental org deletes. The platform UI Delete button hits **Gateway**, which deletes in the **Gateway DB first**, then fans out a resource-registry delete to **Controller / Hub / EDA**. No component ships a hand-written “delete organization” SQL script; each DB uses Django’s deletion collector (FK `on_delete`) plus signals/tasks.

| Item | Value |
|------|--------|
| **Product version** | Ansible Automation Platform **2.6** |
| **UI / API entry** | Platform UI → `DELETE /api/gateway/v1/organizations/:id/` |
| **Code trees** | `aap-26/gateway/automation-gateway`, `aap-26/controller/automation-controller`, DAB under `aap-26/common/django-ansible-base` (also Hub/EDA resource APIs) |
| **Last updated** | 2026-10-22 |

---

## Short answer

1. **Gateway DB** deletes the org row, **CASCADE-deletes Gateway teams** (and org-scoped OAuth apps), cleans DAB RBAC / resource-registry rows for that org (and cascaded teams). Users are **not** deleted. Managed orgs (e.g. Default) cannot be deleted via API.
2. Gateway then **async** `DELETE …/resources/{ansible_id}/` to each registered service (Controller, Hub, EDA). Failures are best-effort; periodic reverse sync (~15 min) is the safety net.
3. **Controller DB** (when it receives that resource delete) cascade-deletes some attached objects (teams, org credentials, org EEs, labels, notification templates, …) but **does not** wipe projects, job templates, workflow templates, or job history -- those get `organization_id = NULL`. Inventories are scheduled for **async** deletion.

---

## End-to-end sequence (UI Delete)

```text
Platform UI "Delete" on Organization
  │
  ▼
DELETE /api/gateway/v1/organizations/:id/
  OrganizationViewSet.destroy
    │  reject if organization.managed == True  (HTTP 400)
    │
    ▼
  ResourceAPIUpdateMixin.perform_destroy  [@transaction.atomic]
    │
    ├─ 1) Local Gateway ORM delete (Gateway Postgres)
    │      Team CASCADE, OAuth apps CASCADE,
    │      DAB ObjectRole / Role*Assignment / evaluations,
    │      dab_resource_registry_resource for org (+ teams),
    │      activitystream Entry for delete
    │
    └─ 2) AllServicesClient.delete_resource(ansible_id)
           wait_for_response=False  (fire-and-forget threads)
           │
           ├─ Controller  DELETE …/resources/{ansible_id}/
           │     → Resource.delete_resource()
           │     → Organization.content_object.delete()
           │     → Controller collector / signals (see § Controller)
           │
           ├─ Hub         same resource DELETE → Hub Organization.delete()
           │                (Hub ALSO deletes its teams in BEFORE_DELETE)
           │
           └─ EDA         same resource DELETE → EDA Organization.delete()
```

Sources:

- `aap_gateway_api/views/api/v1/organization.py` -- managed-org guard
- `aap_gateway_api/views/api/v1/common.py` -- `ResourceAPIUpdateMixin.perform_destroy`
- `aap_gateway_api/utils/resources_client.py` -- `AllServicesClient` (`wait_for_response=False`; comment that 15-minute reverse sync catches delivery failures)
- DAB `resource_registry/models/resource.py` -- `Resource.delete_resource()` → `content_object.delete()` then registry row delete
- Controller `awx/resource_api.py` -- `Organization` is a shared resource (`is_provider=False`); Gateway is provider (`aap_gateway_api/resource_api.py`)

---

## Gateway database

Gateway is the **resource provider** for `shared.organization` / `shared.team`. Org delete from the UI is a Gateway write, not a proxied Controller `/api/v2/organizations/` call.

### Gates

| Check | Behavior |
|-------|----------|
| `organization.managed` | HTTP 400 `"Managed organizations cannot be deleted."` (Default org is created managed) |
| RBAC | `RoleModelViewSet` + DAB object permissions (`delete` on organization) |
| RBAC flush failure | Entire delete rolled back (org + teams + assignments remain) -- see `TestOrgDeleteRBACFlushRollback` |

### What Gateway Postgres deletes / keeps

| Object | Effect |
|--------|--------|
| `aap_gateway_api_organization` | `DELETE` org row |
| `aap_gateway_api_team` | `CASCADE` via `AbstractTeam.organization` (`on_delete=CASCADE`) |
| Team `parents` M2M through | Cleared with team delete |
| DAB OAuth2 applications with `organization_id` | `CASCADE` (`ansible_base.oauth2_provider` → org model) |
| `dab_rbac_objectrole` / `dab_rbac_roleuserassignment` / `dab_rbac_roleteamassignment` / evaluations | Removed for org **and** cascaded teams (`rbac_post_delete_remove_object_roles`; covered by `test_successful_delete_cleans_up_everything`) |
| `dab_resource_registry_resource` | Removed for org (and teams) via `remove_resource` / `AnsibleResourceField` |
| Users | **Not** deleted -- only role assignments tying them to that org/team |
| Activity stream `Entry` | Delete operation logged; history not fully purged as a wipe |
| Service clusters / routes / envoy config | Unrelated to org delete |

Confirmed by Gateway test `TestOrgDeleteCleansUpRBAC.test_successful_delete_cleans_up_everything`: after DELETE 204, org gone, team gone, org/team `RoleUserAssignment` gone, no orphaned empty `ObjectRole`s.

### Logical SQL shape (Gateway DB)

```sql
-- CASCADE children first (collector order varies)
DELETE FROM aap_gateway_api_team
 WHERE organization_id = :org_id;
-- (+ team parents M2M through, team resource/RBAC rows via signals)

DELETE FROM dab_oauth2provider_oauth2application   -- exact table name per app label
 WHERE organization_id = :org_id;
-- (+ tokens that CASCADE from those applications)

-- DAB RBAC for org (and for each cascaded team)
DELETE FROM dab_rbac_roleuserassignment  WHERE … object_role / object_id …
DELETE FROM dab_rbac_roleteamassignment  WHERE …
DELETE FROM dab_rbac_objectrole
 WHERE content_type_id = :org_ct AND object_id = :org_id;
-- RoleEvaluation* for those objects

-- Resource registry
DELETE FROM dab_resource_registry_resource
 WHERE content_type_id = :ct AND object_id = :pk;  -- org and each team

DELETE FROM aap_gateway_api_organization WHERE id = :org_id;

-- Activity stream: INSERT Entry(operation='delete', …)  (not a purge)
```

Table names follow Django defaults (`app_label` + model). Confirm with `\dt` on the Gateway database if labels differ in your build.

### Fan-out to service DBs (not Gateway SQL)

After the local delete commits inside `perform_destroy`:

```text
AllServicesClient.delete_resource(ansible_id)
  → HTTP DELETE {service}/…/resources/{ansible_id}/
```

- **Async** (`wait_for_response=False`): Gateway returns 204 even if a service is slow/down; worker threads log timeouts.
- Controller/Hub/EDA each run `Resource.delete_resource()` → local `Organization.delete()` in **that** service’s Postgres.
- Gateway does **not** explicitly loop `delete_resource` for every cascaded Gateway team in `perform_destroy`; services that CASCADE (or Hub’s `BEFORE_DELETE` team wipe) clean their own team rows when the **org** resource is deleted. Stale service-side rows are what periodic resource sync is meant to reconcile.

---

## Controller database

Triggered when Controller’s resource API receives `DELETE …/resources/{ansible_id}/` for the shared organization (or if someone hits Controller’s own `DELETE /api/v2/organizations/:id/` directly).

Controller does **not** use a custom SQL script. Same pattern: Django collector + signals + one async inventory task.

### Delete gate (Controller API path)

`RelatedJobsPreventDeleteMixin` blocks delete if:

1. Any related unified job is in an **active** state, or
2. A related job finished within the last minute but **event processing is not finished**.

Related jobs: `UnifiedJob` with `organization = <this org>` (`Organization._get_related_jobs`).

Source: `awx/api/views/mixin.py`, `awx/main/models/organization.py`.

> When delete arrives via **resource registry**, confirm in lab whether the same mixin runs (resource view calls `content_object.delete()` directly). Active-job protection is definite for `/api/v2/organizations/` destroys; resource-path behavior should be verified if a case hinges on it.

### Source map (FK policy → Postgres action)

| Model / relation | `on_delete` | Postgres effect on org delete |
|------------------|-------------|-------------------------------|
| `Team.organization` | `CASCADE` | `DELETE` teams |
| `Credential.organization` | `CASCADE` | `DELETE` org credentials (+ `CredentialInputSource` that CASCADE from those credentials) |
| `ExecutionEnvironment.organization` | `CASCADE` | `DELETE` org-scoped EEs |
| `Label.organization` | `CASCADE` | `DELETE` labels |
| `NotificationTemplate.organization` | `CASCADE` | `DELETE` templates → `Notification` CASCADE with them |
| `OAuth2Application.organization` | `CASCADE` | `DELETE` applications (tokens follow app FKs) |
| `OrganizationGalaxyCredentialMembership` | `CASCADE` | `DELETE` galaxy-cred membership rows |
| `OrganizationInstanceGroupMembership` | `CASCADE` | `DELETE` org↔IG link rows (**not** the `InstanceGroup` row) |
| Org notification-template M2Ms | M2M through | `DELETE` through-table rows |
| `Inventory.organization` | `SET_NULL` + **pre_delete signal** | Null org FK; inventories scheduled for **async** delete |
| `UnifiedJobTemplate.organization` | `SET_NULL` (polymorphic) | Projects / JTs / WFJTs **kept**, `organization_id` nulled |
| `UnifiedJob.organization` | `SET_NULL` (polymorphic) | Job history **kept**, `organization_id` nulled |
| `IndirectManagedNodeAudit.organization` | `DO_NOTHING` | No ORM UPDATE/DELETE; PG FK may **block** org delete if rows exist |
| Users | (membership via roles) | **Not** deleted |
| Shared `InstanceGroup` | M2M only | **Not** deleted |

Key model paths:

- `awx/main/models/organization.py` -- `Organization`, `Team`, galaxy membership
- `awx/main/models/unified_jobs.py` -- UJT / UJ `organization` SET_NULL
- `awx/main/models/inventory.py` -- inventory SET_NULL + `schedule_deletion`
- `awx/main/signals.py` -- `delete_inventory_for_org` (`pre_delete` on `Organization`)
- `awx/main/models/indirect_managed_node_audit.py` -- DO_NOTHING
- `awx/main/fields.py` -- `ImplicitRoleField._post_delete` (old RBAC role cleanup)
- `ansible_base/rbac/triggers.py` -- `rbac_post_delete_remove_object_roles` (DAB RBAC)
- `ansible_base/resource_registry/signals/handlers.py` -- `remove_resource`

### Controller sequence

```text
Organization.delete()   # via /api/v2/… or Resource.delete_resource()
  │
  ├─ pre_delete: delete_inventory_for_org
  │     └─ each Inventory.schedule_deletion()
  │           UPDATE pending_deletion=true
  │           clear JT↔inventory links
  │           enqueue delete_inventory.delay(pk, user_id)
  │
  ├─ Django Collector
  │     CASCADE children (teams, credentials, EEs, …)
  │     SET_NULL (UJT, UJ, inventory.organization_id)
  │     DO_NOTHING (indirect audits — no SQL)
  │
  ├─ ImplicitRoleField post_delete → DELETE main_rbac_roles (+ members/parents/ancestors)
  ├─ DAB post_delete → DELETE dab_rbac_objectrole / assignments / evaluations
  ├─ Resource registry post_delete → DELETE dab_resource_registry_resource
  │
  └─ DELETE FROM main_organization WHERE id = :org_id

(later, worker) delete_inventory → Inventory.delete()
      hosts / groups / sources / etc. cascade then
```

### Logical SQL export (Controller DB)

Django generates parameterized SQL; order can vary. Confirm with `log_statement` or `connection.queries` on a lab delete.

#### A. Inventory pre-delete (per inventory, sync portion)

```sql
UPDATE main_inventory
   SET pending_deletion = true
 WHERE id = :inv_id;

-- clear job-template associations for that inventory (through-table name may vary)
-- then Celery/dispatcher: delete_inventory.delay(:inv_id, :user_id)
```

#### B. CASCADE / M2M cleanup (org transaction)

```sql
DELETE FROM main_organizationgalaxycredentialmembership WHERE organization_id = :org_id;
DELETE FROM main_organizationinstancegroupmembership   WHERE organization_id = :org_id;

DELETE FROM main_organization_notification_templates_error    WHERE organization_id = :org_id;
DELETE FROM main_organization_notification_templates_success  WHERE organization_id = :org_id;
DELETE FROM main_organization_notification_templates_started  WHERE organization_id = :org_id;
DELETE FROM main_organization_notification_templates_approvals WHERE organization_id = :org_id;

DELETE FROM main_notification
 WHERE notification_template_id IN (
   SELECT id FROM main_notificationtemplate WHERE organization_id = :org_id
 );
DELETE FROM main_notificationtemplate WHERE organization_id = :org_id;

DELETE FROM main_label WHERE organization_id = :org_id;

-- CredentialInputSource rows for credentials owned by this org, then:
DELETE FROM main_credential WHERE organization_id = :org_id;

DELETE FROM main_executionenvironment WHERE organization_id = :org_id;
DELETE FROM main_oauth2application    WHERE organization_id = :org_id;
DELETE FROM main_team                 WHERE organization_id = :org_id;
```

Cascade of a Team/Credential also triggers that object’s own role/resource cleanup (same pattern as org).

#### C. SET_NULL (rows kept)

```sql
UPDATE main_unifiedjobtemplate
   SET organization_id = NULL
 WHERE organization_id = :org_id;
-- polymorphic parent for Project / JobTemplate / WorkflowJobTemplate / …

UPDATE main_unifiedjob
   SET organization_id = NULL
 WHERE organization_id = :org_id;
-- job / project_update / inventory_update / workflow_job / … history remains

UPDATE main_inventory
   SET organization_id = NULL
 WHERE organization_id = :org_id;
-- pending_deletion already true; full wipe is async
```

#### D. DO_NOTHING

```sql
-- main_indirectmanagednodeaudit: no ORM statement
-- If a real PG FK exists (migration 0196 does not set db_constraint=False),
-- leftover rows can IntegrityError the org DELETE.
```

#### E. RBAC / resource registry (signals)

```sql
-- Old AWX roles for the org (and cascade-deleted children with ImplicitRoleFields)
DELETE FROM main_rbac_roles_members  WHERE role_id IN (:org_role_ids);
DELETE FROM main_rbac_roles_parents  WHERE from_role_id IN (:org_role_ids)
                                    OR to_role_id IN (:org_role_ids);
DELETE FROM main_rbac_role_ancestors WHERE …;  -- via Role.delete / rebuild_role_ancestor_list
DELETE FROM main_rbac_roles WHERE id IN (:org_role_ids);

-- DAB RBAC
DELETE FROM dab_rbac_roleuserassignment  WHERE object_role_id IN (…);
DELETE FROM dab_rbac_roleteamassignment  WHERE object_role_id IN (…);
DELETE FROM dab_rbac_objectrole
 WHERE content_type_id = :org_ct AND object_id = :org_id;
-- RoleEvaluation / RoleEvaluationUUID for that object_id

-- Resource registry
DELETE FROM dab_resource_registry_resource
 WHERE content_type_id = :ct AND object_id = :pk;
-- repeated for Organization and each registered cascade-deleted child
```

#### F. Org row

```sql
DELETE FROM main_organization WHERE id = :org_id;
```

#### G. Later (async inventory task)

```sql
-- Inventory.objects.get(id=:inv_id).delete()
-- → DELETE hosts, groups, inventory sources, memberships, etc. for that inventory
```

### What Controller does *not* delete

| Still present after Controller org delete | Notes |
|-------------------------------------------|--------|
| Projects / job templates / workflow job templates | `organization_id` NULL |
| Unified job history | `organization_id` NULL |
| Users | Only membership/roles for that org are removed |
| Shared instance groups | Membership row gone; IG remains |
| Inventories (briefly / if async fails) | `pending_deletion=true`, then worker deletes |
| Indirect managed-node audit rows | DO_NOTHING; may block or dangle |
| Activity-stream history | Delete is logged; history is not fully purged |

Credential CASCADE can still **break** leftover templates/jobs that referenced deleted credentials (FK SET_NULL or M2M clear), even though the template/job rows themselves remain.

---

## Hub / EDA (brief)

Same fan-out: Gateway `delete_resource(ansible_id)` hits each service’s resource API.

| Service | Org model | Notable delete behavior |
|---------|-----------|-------------------------|
| **Hub** | `galaxy_ng` `Organization` | `BEFORE_DELETE` explicitly deletes all Hub teams for that org (then team→group CASCADE) |
| **EDA** | `aap_eda.core` `Organization` | Shared resource consumer; local org/team CASCADE per EDA models |

Hub/EDA do **not** hold Controller job/inventory data; orphaned Controller projects/JTs are a Controller-DB concern only.

---

## How to capture exact SQL on a lab

1. **Which DB?** Gateway delete → Gateway Postgres first; then Controller/Hub/EDA Postgres when resource DELETE lands.
2. Postgres: temporarily `log_statement = 'all'` (or log for the component DB role), reload, delete one org from the UI, restore setting.
3. Django: enable query logging around `Organization.objects.get(pk=…).delete()` in that component’s shell.
4. Or inspect collector membership without executing (Controller example):

```python
from django.db.models.deletion import Collector
from awx.main.models import Organization

org = Organization.objects.get(pk=ORG_ID)
c = Collector(using='default')
c.collect([org])
# c.data / c.fast_deletes / c.field_updates describe what would run
```

---

## Related code citations (aap-26)

| Topic | Path |
|-------|------|
| Gateway org view + managed guard | `gateway/automation-gateway/aap_gateway_api/views/api/v1/organization.py` |
| Gateway destroy + service fan-out | `aap_gateway_api/views/api/v1/common.py` (`ResourceAPIUpdateMixin`) |
| Async multi-service client | `aap_gateway_api/utils/resources_client.py` (`AllServicesClient`) |
| Gateway org/team models | `aap_gateway_api/models/organization.py`, `…/team.py`; DAB `lib/abstract_models/team.py` |
| Gateway as resource provider | `aap_gateway_api/resource_api.py` |
| Org delete RBAC cleanup test | `aap_gateway_api/tests/views/api/v1/organization/test_organization.py` |
| Resource.delete_resource | `common/django-ansible-base/ansible_base/resource_registry/models/resource.py` |
| Controller shared org consumer | `controller/…/awx/resource_api.py` |
| Controller org + related jobs | `awx/main/models/organization.py` |
| Controller prevent-delete mixin | `awx/api/views/mixin.py` |
| Inventory schedule + async delete | `awx/main/models/inventory.py`; `awx/main/tasks/system.py` `delete_inventory` |
| Org pre_delete inventories | `awx/main/signals.py` `delete_inventory_for_org` |
| UJT/UJ SET_NULL | `awx/main/models/unified_jobs.py` |
| Indirect audit DO_NOTHING | `awx/main/models/indirect_managed_node_audit.py` |
| Hub org BEFORE_DELETE teams | `hub/…/galaxy_ng/app/models/organization.py` |

---

## Considerations for support cases

- UI Delete is a **Gateway** operation first. Checking only the Controller DB understates what was removed (Gateway teams/RBAC/registry) and can miss a failed fan-out (Controller org still present while Gateway org is gone -- or the reverse after a partial sync).
- Customers often expect “delete org = delete everything under it” on Controller. Code intentionally **orphans** projects/JTs/jobs via SET_NULL.
- Inventory deletion on Controller is **best-effort async**; check worker logs / `pending_deletion` if inventories linger.
- Active jobs block Controller `/api/v2/` deletes; volume of attached resources alone does not.
- If Controller org delete fails with an FK error mentioning `main_indirectmanagednodeaudit`, that matches DO_NOTHING + a live PG constraint.
- Managed/Default org cannot be deleted from Gateway API.
- Restoring an accidentally deleted org is **not** a simple INSERT into one table -- Gateway + each service DB (and resource ansible_ids) must come from backups taken **before** the delete, or be rebuilt and re-synced carefully.
