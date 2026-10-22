# Organization Delete — What Controller Actually Does in PostgreSQL (AAP 2.6)

Support / engineering reference for accidental org deletes and cleanup expectations. Controller does **not** ship a hand-written “delete organization” SQL script. A UI/API delete runs Django’s deletion collector (FK `on_delete` policies) plus a few signals and one async task.

| Item | Value |
|------|--------|
| **Product version** | Ansible Automation Platform **2.6** (Controller / AWX) |
| **Code tree used** | `aap-26/controller/automation-controller` (+ DAB under `aap-26/common/django-ansible-base`) |
| **Entry point** | `DELETE /api/v2/organizations/:id/` → `OrganizationDetail` + `RelatedJobsPreventDeleteMixin` |
| **Last updated** | 2026-10-22 |

---

## Short answer

Deleting an organization **does cascade-delete some attached objects** (teams, org credentials, org EEs, labels, notification templates, OAuth apps, memberships, RBAC rows). It **does not** wipe projects, job templates, workflow templates, or job history -- those keep their rows and get `organization_id = NULL`. Inventories are marked for deletion and removed **asynchronously**, not fully inside the org DELETE transaction.

---

## Delete gate (may refuse the request)

Before any collector SQL runs, `RelatedJobsPreventDeleteMixin` blocks delete if:

1. Any related unified job is in an **active** state, or
2. A related job finished within the last minute but **event processing is not finished**.

Related jobs for an org are `UnifiedJob` rows with `organization = <this org>` (`Organization._get_related_jobs`).

Source: `awx/api/views/mixin.py` (`RelatedJobsPreventDeleteMixin`), `awx/main/models/organization.py`.

---

## Source map (FK policy → Postgres action)

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

---

## Sequence of what runs

```text
DELETE /api/v2/organizations/:id/
  │
  ├─ RelatedJobsPreventDeleteMixin  →  409/403 if active or unprocessed jobs
  │
  ├─ Organization.delete()
  │     │
  │     ├─ pre_delete: delete_inventory_for_org
  │     │     └─ each Inventory.schedule_deletion()
  │     │           UPDATE pending_deletion=true
  │     │           clear JT↔inventory links
  │     │           enqueue delete_inventory.delay(pk, user_id)
  │     │
  │     ├─ Django Collector
  │     │     CASCADE children (teams, credentials, EEs, …)
  │     │     SET_NULL (UJT, UJ, inventory.organization_id)
  │     │     DO_NOTHING (indirect audits — no SQL)
  │     │
  │     ├─ ImplicitRoleField post_delete → DELETE main_rbac_roles (+ members/parents/ancestors)
  │     ├─ DAB post_delete → DELETE dab_rbac_objectrole / assignments / evaluations
  │     ├─ Resource registry post_delete → DELETE dab_resource_registry_resource
  │     │
  │     └─ DELETE FROM main_organization WHERE id = :org_id
  │
  └─ (later, worker) delete_inventory → Inventory.delete()
        hosts / groups / sources / etc. cascade then
```

---

## Logical SQL export (shape, not a verbatim dump)

Django generates parameterized SQL; order can vary slightly. Table names below match Django defaults for the `main` / DAB apps. Use `log_statement` or `connection.queries` on a lab delete for exact wording.

### A. Inventory pre-delete (per inventory, sync portion)

```sql
UPDATE main_inventory
   SET pending_deletion = true
 WHERE id = :inv_id;

-- clear job-template associations for that inventory (through-table name may vary)
-- then Celery/dispatcher: delete_inventory.delay(:inv_id, :user_id)
```

### B. CASCADE / M2M cleanup (org transaction)

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

### C. SET_NULL (rows kept)

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

### D. DO_NOTHING

```sql
-- main_indirectmanagednodeaudit: no ORM statement
-- If a real PG FK exists (migration 0196 does not set db_constraint=False),
-- leftover rows can IntegrityError the org DELETE.
```

### E. RBAC / resource registry (signals)

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

### F. Org row

```sql
DELETE FROM main_organization WHERE id = :org_id;
```

### G. Later (async inventory task)

```sql
-- Inventory.objects.get(id=:inv_id).delete()
-- → DELETE hosts, groups, inventory sources, memberships, etc. for that inventory
```

---

## What is *not* deleted by org delete

| Still present after org DELETE returns 204 | Notes |
|--------------------------------------------|--------|
| Projects / job templates / workflow job templates | `organization_id` NULL |
| Unified job history | `organization_id` NULL |
| Users | Only membership/roles for that org are removed |
| Shared instance groups | Membership row gone; IG remains |
| Inventories (briefly / if async fails) | `pending_deletion=true`, then worker deletes |
| Indirect managed-node audit rows | DO_NOTHING; may block or dangle |
| Activity-stream history | Delete is logged; history is not fully purged as a “wipe org” |

Credential CASCADE can still **break** leftover templates/jobs that referenced deleted credentials (FK SET_NULL or M2M clear), even though the template/job rows themselves remain.

---

## How to capture exact SQL on a lab

1. Postgres: temporarily `ALTER SYSTEM SET log_statement = 'all';` (or log for the awx DB role only), reload, delete one org, restore setting.
2. Django: in `awx-manage shell`, enable query logging around `Organization.objects.get(pk=…).delete()`.
3. Or inspect collector membership without executing:

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
| Org model + related jobs | `controller/automation-controller/awx/main/models/organization.py` |
| Prevent delete mixin | `controller/automation-controller/awx/main/models` / `awx/api/views/mixin.py` |
| Inventory schedule + async delete | `awx/main/models/inventory.py` `schedule_deletion`; `awx/main/tasks/system.py` `delete_inventory` |
| Org pre_delete inventories | `awx/main/signals.py` `delete_inventory_for_org` |
| UJT/UJ SET_NULL | `awx/main/models/unified_jobs.py` |
| Indirect audit DO_NOTHING | `awx/main/models/indirect_managed_node_audit.py`; migration `0196_indirect_managed_node_audit.py` |
| Old role cleanup | `awx/main/fields.py` `ImplicitRoleField._post_delete` |
| DAB object-role cleanup | `common/django-ansible-base/ansible_base/rbac/triggers.py` |
| Resource registry cleanup | `common/django-ansible-base/ansible_base/resource_registry/signals/handlers.py` |

---

## Considerations for support cases

- Customers often expect “delete org = delete everything under it.” Code intentionally **orphans** projects/JTs/jobs via SET_NULL.
- Inventory deletion is **best-effort async**; check worker logs / `pending_deletion` if inventories linger.
- Active jobs block delete; volume of attached resources alone does not.
- If org delete fails with an FK error mentioning `main_indirectmanagednodeaudit`, that matches DO_NOTHING + a live PG constraint.
- Restoring an accidentally deleted org is **not** a simple INSERT of `main_organization` -- cascades (teams, credentials, roles, resources) are already gone; restore from DB backup taken **before** the delete.
