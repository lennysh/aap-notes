# AAP 2.5 on OpenShift — Example Manifests

Example Kubernetes manifests for deploying Ansible Automation Platform **2.5** with the Red Hat AAP Operator on OpenShift.

For containerized deployment on Linux hosts, see [AAP 2.5 containerized inventories](../containerized/README.md). For RPM deployment, see [AAP 2.5 RPM inventories](../rpm/README.md).

## 2.5+ deployment model

From AAP 2.5, deploy the **`AnsibleAutomationPlatform`** CR (`aap.ansible.com/v1alpha1`). The operator:

- Creates the **platform gateway** (unified UI/API)
- Creates and manages **`AutomationController`**, **`AutomationHub`**, and **`EDA`** component CRs from nested `spec.controller`, `spec.hub`, and `spec.eda` blocks
- Auto-generates many component database secrets (see `status.controllerDatabaseSecret`, `status.hubDatabaseSecret`, `status.edaDatabaseSecret` on the platform CR)

You apply **one** platform CR. Every option that existed on the individual component CRs can be set under the matching nested block in `aap.yml` — the platform CRD uses `preserve-unknown-fields` and accepts the full `AutomationController`, `AutomationHub`, and `EDA` specs.

Red Hat docs: [Installing AAP 2.5 on OpenShift](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/installing_on_openshift_container_platform/operator-install-operator_operator-platform-doc)

## Files

| File | Purpose |
|------|---------|
| [secrets-aap.yml](secrets-aap.yml) | Platform + optional component secrets (referenced from `aap.yml`) |
| [aap.yml](aap.yml) | `AnsibleAutomationPlatform` CR — platform, gateway, and all component settings |

For an exhaustive list of every component field, see the generated nested blocks in [`aap.yml`](aap.yml) or the component CRD dumps under `config-examples/.crd-dumps/2.5/`.

## Deployment order

```shell
oc create namespace aap

oc apply -f secrets-aap.yml
oc apply -f aap.yml
```

Verify under **Operators → Installed Operators → Ansible Automation Platform → All instances**: you should see the **AnsibleAutomationPlatform** instance plus child **AutomationController**, **AutomationHub**, and **EDA** instances.

## Secret wiring

**Platform-level** secrets map to top-level `AnsibleAutomationPlatform` spec fields:

| CRD field | Secret name (example) | secrets-aap.yml |
|-----------|----------------------|-----------------|
| `admin_password_secret` | `example-aap-admin-password` | §3 |
| `db_fields_encryption_secret` | `example-aap-secret-key` | §2 |
| `database.database_secret` | `aap-gateway-postgres-configuration` | §1 |
| `route_tls_secret` | `aap-route-tls-secret` | §4 |
| `bundle_cacert_secret` | `aap-bundle-ca-secret` | §6 |
| `image_pull_secrets` | `aap-image-pull-secret` | §7 |
| `ingress_tls_secret` | `aap-ingress-tls-secret` | §8 |
| `redis.redis_secret` | `aap-redis-configuration` | §9 |

**Component-level** secrets are referenced from nested blocks in `aap.yml`, not from top-level platform fields:

| Nested path in `aap.yml` | Example secret | secrets-aap.yml |
|--------------------------|----------------|-----------------|
| `spec.hub.object_storage_s3_secret` | `hub-s3-storage-secret` | §5 |
| `spec.controller.postgres_configuration_secret` | `controller-postgres-configuration` | §10 (optional) |
| `spec.controller.secret_key_secret` | `example-controller-secret-key` | §11 (optional) |
| `spec.controller.ee_pull_credentials_secret` | `ee-pull-secret` | §12 (optional) |
| `spec.hub.postgres_configuration_secret` | `hub-postgres-configuration` | §13 (optional) |
| `spec.hub.db_fields_encryption_secret` | `example-hub-secret-key` | §14 (optional) |

The operator auto-generates component DB secrets when omitted. Pre-provision secrets for GitOps or migration.

## Nested component configuration

`spec.controller`, `spec.hub`, and `spec.eda` accept **any field** from the respective component CRD, plus:

| Field | Purpose |
|-------|---------|
| `disabled: true` | Skip deploying that component |
| `name: <existing-cr-name>` | Register an **existing** component CR instead of creating a new one (names must match exactly) |

Example — external controller Postgres and Hub S3 via nested blocks only:

```yaml
spec:
  controller:
    disabled: false
    postgres_configuration_secret: controller-postgres-configuration
    secret_key_secret: example-controller-secret-key
    ee_pull_credentials_secret: ee-pull-secret
  hub:
    disabled: false
    storage_type: S3
    object_storage_s3_secret: hub-s3-storage-secret
    postgres_configuration_secret: hub-postgres-configuration
  eda:
    disabled: false
```

## Regenerating `aap.yml`

```shell
cd /path/to/openshift-playground/generate-aap-cr-examples
python3 generate-aap-cr-examples.py \
  --version 2.5 \
  --crd-dir /path/to/aap-notes/config-examples/.crd-dumps/2.5 \
  --output-dir /path/to/aap-notes/config-examples/AAP25/openshift \
  --kinds AnsibleAutomationPlatform
```

The generator documents top-level platform fields exhaustively. Nested `spec.controller`, `spec.hub`, and `spec.eda` blocks include **every field** from the component CRDs (same coverage as the AAP 2.4 component examples), plus platform-only `disabled` and `name`.

## Migration notes

- Operator migration secrets (`old_postgres_configuration_secret`, etc.) are **deprecated** in 2.5+ (AAP-68844).
- Prefer customer-managed DB restore + `postgres_configuration_secret` / nested DB secret adoption with matching encryption keys.

## Hub `hstore` (external Postgres)

If using external Postgres for Hub (via `spec.hub.postgres_configuration_secret`):

```shell
psql -d automationhub -c "CREATE EXTENSION IF NOT EXISTS hstore;"
```
