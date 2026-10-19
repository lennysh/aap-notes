# Migrating AAP 2.4 External Databases (RPM or Containerized) to AAP 2.6 on OpenShift

Customer-facing guidance for Architecture Review Boards and migration planning when moving from AAP **2.4** on RHEL hosts—either **RPM** or **containerized** installer—to AAP **2.6** on OpenShift, while reusing the existing PostgreSQL databases.

| Item | Value |
|------|--------|
| **Source** | Ansible Automation Platform **2.4** (RPM **or** containerized on RHEL) |
| **Target** | Ansible Automation Platform **2.6** (AAP Operator on OpenShift) |
| **Scope** | Database schema upgrade behavior when pointing the Operator install at existing 2.4 databases |
| **Last updated** | 2026-10-19 |

---

## Short answer

You do **not** need to install AAP 2.4 on OpenShift first, point it at the old databases, and then upgrade that instance to 2.6 solely for schema upgrade purposes.

You can deploy **AAP 2.6** on OpenShift, configure the platform to use the **existing 2.4 databases**, and the product will detect pending schema changes and apply them.

This applies equally whether the source install was **RPM** or **containerized**. Schema migration is driven by what is already recorded in each database (Django / Pulp migration state). It does **not** require the Operator to “know” that the environment previously ran AAP 2.4 on OpenShift, and it does **not** depend on which RHEL installer (RPM vs containerized) produced those databases.

---

## What this document covers

| In scope | Out of scope |
|----------|--------------|
| Whether a direct 2.6 Operator install can upgrade a 2.4 DB schema | Full end-to-end migration runbooks (network, storage, mesh, cutover) |
| RPM **and** containerized sources that reuse existing PostgreSQL | Moving only an installer-managed local Postgres volume without a DBA/data plan |
| How schema upgrade decisions are made | PostgreSQL major-version upgrades |
| Differences between schema migrate and Gateway post-install data merge | Official Red Hat Support statements beyond what the product code/docs implement |

Always take a verified backup of databases and related secrets before cutover. Follow the current Red Hat product documentation for your exact topology and subscription channel.

---

## Source install types (same schema path)

| Source on RHEL | Typical database layout | Schema path to AAP 2.6 on OpenShift |
|----------------|-------------------------|-------------------------------------|
| **RPM** | Often dedicated / external PostgreSQL hosts (or co-located Postgres packages) | Point Operator `postgres_configuration_secret` at those DBs |
| **Containerized** | PostgreSQL usually on inventory hosts (Podman) or external DB hosts from inventory | Same: expose DB to the cluster and point Operator secrets at those DBs |

In both cases, once OpenShift can reach the PostgreSQL endpoints and the correct DB names/users/passwords and encryption secrets are supplied, Controller / Hub / EDA apply **pending** migrations from the 2.6 images. The Operator does not distinguish “this dump came from RPM” vs “this dump came from containerized.”

> **Prerequisite:** the databases must be reachable from the OpenShift cluster as **external** PostgreSQL for the Operator. If Postgres today lives only on a single RHEL host behind no routable service, plan network exposure, TLS, and firewall rules (or dump/restore into a new external Postgres) before cutover. That networking/DBA work is separate from schema migrate logic.

---

## Recommended approach (reuse existing databases)

1. **Back up** each component database and the critical secrets (`SECRET_KEY` for Controller, Hub encryption / DB field keys, and any other component secrets required for restore). On containerized installs, collect the same values from installer inventory / generated secrets used by the Podman stack.
2. Ensure PostgreSQL is reachable from OpenShift (hostname/IP, port, TLS, auth). Stop or fence the old RPM/containerized Controllers so they do not write during cutover.
3. Deploy the **AAP 2.6** Operator and create an `AnsibleAutomationPlatform` (or component) CR for 2.6.
4. Point each component at its existing database via the component’s **PostgreSQL configuration secret** (`postgres_configuration_secret` / equivalent nested platform fields).
5. Supply the **same Controller secret key** (and Hub encryption material) used by the 2.4 install so encrypted fields remain readable.
6. Allow the install to complete. Controller, Hub, and EDA will apply **pending** schema migrations against those databases as part of normal startup / install tasks.

Operator documentation for Controller describes this path explicitly: when the database is already external (or otherwise not managed by the Operator), configure `postgres_configuration_secret` (not the “old database dump/stream” migration secret used when copying between Operator-managed Postgres pods). The new deployment connects to the existing database and applies any pending migrations.

> **Strongly recommended:** keep the RPM or containerized environment offline or read-only during cutover so two Controllers never write to the same database concurrently.

---

## How schema upgrade decisions are made

### Schema migrations look at the database

On install/reconcile, Automation Controller checks for unapplied migrations (equivalent to `awx-manage showmigrations`) and, if any are pending, runs a migration Job (`awx-manage migrate`).

That decision is based on the migration history stored in the database (Django’s migration tables), compared to the migrations shipped in the **2.6** container image. The Operator does **not** need a prior 2.4 OpenShift Custom Resource or Deployment for this step.

Other components follow the same general pattern:

| Component | Typical migrate mechanism |
|-----------|---------------------------|
| Automation Controller | `awx-manage migrate` (Job when pending) |
| Private Automation Hub | `pulpcore-manager migrate` (init) |
| Event-Driven Ansible | `aap-eda-manage migrate` (init) |
| Platform Gateway | `aap-gateway-manage migrate` (init) on a **new** Gateway database |

Hub and EDA behave the same way when pointed at existing 2.4 databases: migrate against the DB they are given.

### Operator “previous version” awareness is a different layer

The Controller Operator can record `previous_version` / `upgradedFrom` when it finds an **existing OpenShift Deployment / CR** for that instance and reads a prior `status.version`. That mechanism is for **in-cluster** Operator upgrades (and related post-upgrade tasks). It is **not** what decides whether Controller schema migrations run.

| Mechanism | Looks at | Used for |
|-----------|----------|----------|
| Schema migrate (`showmigrations` / `migrate`) | Database migration state | Applying DDL / Django model changes |
| `upgradedFrom` / previous CR version | Existing OpenShift CR status | Selected post-upgrade Operator tasks (see below) |

**Implication:** a greenfield AAP 2.6 install that points at 2.4 databases (from RPM **or** containerized) still runs schema migrations. It does **not** need an intermediate “2.4 on OpenShift” install for that purpose.

---

## Platform Gateway notes (AAP 2.5 / 2.6)

AAP **2.4** does not include Platform Gateway. On 2.6:

- Gateway requires its **own** PostgreSQL database (new / empty for this purpose). Do not try to reuse a “2.4 Gateway DB”—it does not exist.
- After components are up, the platform post-install path merges service data into Gateway (`aap-gateway-manage migrate_service_data`: organizations, teams, users, and related resources from Controller / Hub / EDA).

### SSO / authenticator import caveat

When upgrading an **existing Controller on OpenShift** from a Controller version older than the Operator’s gating version, the Gateway Operator may automatically run `awx-manage import_auth_config_to_gateway` (imports LDAP/SAML/OIDC and related auth settings into Gateway). That path is gated on Controller CR `status.upgradedFrom`.

A **direct** 2.6 install (no prior Controller CR on the cluster)—whether the data came from RPM or containerized—will still:

- Upgrade Controller / Hub / EDA **schemas** from the databases, and
- Run Gateway `migrate_service_data`,

but it may **not** automatically run Controller → Gateway **authenticator** import.

**If the customer uses SSO (LDAP, SAML, OIDC, etc.) on Controller today:** plan to verify Gateway authenticators after cutover, and run `awx-manage import_auth_config_to_gateway` manually from a Controller web pod if SSO settings were not imported.

---

## Do you need “install 2.4 on OpenShift, then upgrade to 2.6”?

| Goal | Intermediate 2.4-on-OCP required? |
|------|-----------------------------------|
| Upgrade Controller / Hub / EDA **database schemas** from 2.4 → 2.6 | **No** — point 2.6 at the existing DBs (RPM or containerized source) |
| Stream/dump data from a **managed** (Operator-owned) Postgres into a new managed Postgres | Different path (`old_postgres_configuration_secret` / data migration) — not the usual VM/external-DB case |
| Automatic `import_auth_config_to_gateway` via `upgradedFrom` | Only applies when upgrading an **existing** OCP Controller instance; not required for schema upgrade |

For the common **RPM or containerized** + reusable PostgreSQL migration into OpenShift, the supported mental model is: **deploy 2.6, attach existing DBs + secrets, let migrate apply pending schema changes**, then complete Gateway onboarding (new DB + service data merge + SSO verification).

---

## Checklist (external / reused DB cutover)

- [ ] Source identified: RPM or containerized (same DB attach model either way)
- [ ] Verified backups of Controller, Hub, and EDA databases (and Gateway DB plan for new empty DB)
- [ ] Controller `SECRET_KEY` (and Hub encryption secrets) available as Kubernetes Secrets for the new install
- [ ] PostgreSQL reachable from the OpenShift cluster (network, TLS, auth, DB names/users)
- [ ] RPM or containerized Controllers stopped or prevented from writing during and after cutover
- [ ] AAP 2.6 Operator and `AnsibleAutomationPlatform` CR deployed with external DB secrets configured
- [ ] Migration Jobs / init containers completed successfully for each component
- [ ] Gateway `migrate_service_data` completed
- [ ] SSO / authenticator behavior verified in the platform UI (manual import if needed)
- [ ] Smoke tests: login, job launch, Hub content, EDA activations (as applicable)

---

## FAQ

**Q: Does this apply to containerized installs as well as RPM?**  
**A:** Yes. Schema upgrade depends on the database contents and the 2.6 images, not on whether the old stack was RPM or containerized.

**Q: Will installing 2.6 against a 2.4 Controller database automatically upgrade the schema?**  
**A:** Yes. Pending migrations are detected from the database and applied. Backup first.

**Q: Must we install 2.4 on OpenShift before 2.6?**  
**A:** Not for schema upgrade when reusing existing databases. You can install 2.6 and point it at those DBs.

**Q: Does the Operator only migrate if it sees a 2.4 → 2.6 upgrade?**  
**A:** No for schema. Schema migrate inspects the database. Some optional post-upgrade tasks (notably SSO import into Gateway) look at in-cluster CR upgrade status instead.

**Q: What about Gateway’s database?**  
**A:** Create/configure a new Gateway database for 2.6. Gateway was not part of AAP 2.4.

**Q: Our containerized Postgres is only on the installer host—can we “just point” OpenShift at it?**  
**A:** Only if the cluster can reach that PostgreSQL service securely. Otherwise plan network exposure or dump/restore to an external Postgres the cluster can use. That is a connectivity/DBA step, not a different schema-migrate rule.

**Q: What if PostgreSQL itself must be upgraded (for example major version)?**  
**A:** Treat that as a separate DBA project. Product schema migrate assumes a supported PostgreSQL that the new release can use; it does not replace a Postgres major-version migration plan.
