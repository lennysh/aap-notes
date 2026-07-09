# AAP 2.4 on OpenShift — Example Manifests

Example Kubernetes manifests for deploying Ansible Automation Platform 2.4 with the Red Hat AAP Operator on OpenShift. Secrets are split from Custom Resources so credentials stay out of CR specs.

For RPM deployment on RHEL hosts, see [AAP 2.4 RPM inventory](../rpm/README.md).

These are reference examples — replace placeholder values, trim secrets you do not need, and validate against your environment before applying.

All manifests target the `aap` namespace. Create it (or change `namespace` everywhere) before deploying. Do **not** deploy AAP into the `default` namespace.

The `controller.yml`, `hub.yml`, and `eda.yml` CR files are exhaustive spec references (every CRD field documented). Regenerate them from operator CRD dumps with [generate-aap-cr-examples](https://github.com/lennysh/openshift-playground/tree/main/generate-aap-cr-examples) in openshift-playground.

## Files

| File | Purpose |
|------|---------|
| [secrets-controller.yml](secrets-controller.yml) | All Controller secret examples (active + optional commented) |
| [secrets-hub.yml](secrets-hub.yml) | All Hub secret examples (active + optional commented) |
| [secrets-eda.yml](secrets-eda.yml) | All EDA secret examples (active + optional commented) |
| [configmaps-hub.yml](configmaps-hub.yml) | Optional Hub signing scripts ConfigMap (pairs with Hub signing secret) |
| [controller.yml](controller.yml) | `AutomationController` CR — full spec reference |
| [hub.yml](hub.yml) | `AutomationHub` CR — full spec reference |
| [eda.yml](eda.yml) | `EDA` CR — full spec reference |

## Deployment order

1. Create the namespace (if it does not exist).
2. Enable the PostgreSQL `hstore` extension on the Hub database (required for external Postgres — see below).
3. Replace TLS placeholders or create TLS secrets with real certificates.
4. Apply secret manifests (and optional ConfigMaps) so every secret referenced in the CRs exists first.
5. Apply the Custom Resources.

```shell
oc create namespace aap

# Optional: create TLS secrets from real cert/key files instead of editing YAML placeholders
# oc create secret tls controller-route-tls-secret --cert=controller.crt --key=controller.key -n aap
# oc create secret tls hub-route-tls-secret --cert=hub.crt --key=hub.key -n aap
# oc create secret tls eda-route-tls-secret --cert=eda.crt --key=eda.key -n aap

# Stage secrets before the operator reconciles CRs
oc apply -f secrets-controller.yml
oc apply -f secrets-hub.yml
oc apply -f secrets-eda.yml
# oc apply -f configmaps-hub.yml   # when enabling Hub content signing

# Deploy component CRs (secret names in spec must match the secrets above)
oc apply -f controller.yml
oc apply -f hub.yml
oc apply -f eda.yml
```

## Secret catalog (AAP 2.4 CRDs)

Every `*_secret` field in the Controller, Hub, and EDA CRDs is listed below. **Active** secrets are applied by default; **optional** blocks are commented in the secret files and CRs.

### AutomationController

| CRD field | Secret name (example) | secrets-controller.yml | Status |
|-----------|----------------------|------------------------|--------|
| `secret_key_secret` | `example-controller-secret-key` | §3 | Active |
| `postgres_configuration_secret` | `controller-postgres-configuration` | §1 | Active |
| `ee_pull_credentials_secret` | `ee-pull-secret` | §2 | Active |
| `admin_password_secret` | `example-controller-admin-password` | §4 | Active |
| `route_tls_secret` | `controller-route-tls-secret` | §5 | Active |
| `bundle_cacert_secret` | `bundle-ca-secret` | §6 | Optional |
| `ldap_cacert_secret` | `ldap-ca-secret` | §7 | Optional |
| `ldap_password_secret` | `ldap-password-secret` | §8 | Optional |
| `broadcast_websocket_secret` | `example-controller-broadcast-websocket` | §9 | Optional (operator auto-generates) |
| `metrics_utility_secret` | `controller-metrics-utility-secret` | §10 | Optional (requires `metrics_utility_enabled: true`) |
| `image_pull_secrets` | `aap-image-pull-secret` | §11 | Optional |
| `ingress_tls_secret` | `controller-ingress-tls-secret` | §12 | Optional (use when `ingress_type: Ingress`) |
| `old_postgres_configuration_secret` | `example-controller-old-postgres-configuration` | §13 | Optional (migration only) |
| `image_pull_secret` | — | — | Deprecated; use `image_pull_secrets` |

**Related (not standalone secrets):** `extra_settings_files.secrets` (Controller 2.5+) references existing Secret names from the CR — no new secret shape.

### AutomationHub

| CRD field | Secret / ConfigMap name (example) | File | Status |
|-----------|-----------------------------------|------|--------|
| `db_fields_encryption_secret` | `example-hub-secret-key` | secrets-hub §2 | Active |
| `postgres_configuration_secret` | `hub-postgres-configuration` | secrets-hub §1 | Active |
| `object_storage_s3_secret` | `hub-s3-storage-secret` | secrets-hub §4 | Active |
| `route_tls_secret` | `hub-route-tls-secret` | secrets-hub §3 | Active |
| `admin_password_secret` | `example-hub-admin-password` | secrets-hub §5 | Optional |
| `sso_secret` | `automation-hub-sso` | secrets-hub §6 | Optional |
| `bundle_cacert_secret` | `hub-bundle-ca-secret` | secrets-hub §7 | Optional |
| `signing_secret` | `hub-signing-secret` | secrets-hub §8 | Optional |
| `signing_scripts_configmap` | `hub-signing-scripts` | configmaps-hub §1 | Optional (ConfigMap) |
| `container_token_secret` | `hub-container-token-secret` | secrets-hub §9 | Optional |
| `image_pull_secrets` | `hub-image-pull-secret` | secrets-hub §10 | Optional |
| `ingress_tls_secret` | `hub-ingress-tls-secret` | secrets-hub §11 | Optional |
| `object_storage_azure_secret` | `hub-azure-storage-secret` | secrets-hub §12 | Optional (disable S3) |
| `postgres_migrant_configuration_secret` | `example-hub-old-postgres-configuration` | secrets-hub §13 | Optional (migration) |
| `image_pull_secret` | — | — | Deprecated; use `image_pull_secrets` |

### EDA

| CRD field | Secret name (example) | secrets-eda.yml | Status |
|-----------|----------------------|-----------------|--------|
| `db_fields_encryption_secret` | `example-eda-secret-key` | §2 | Active |
| `database.database_secret` | `eda-postgres-configuration` | §1 | Active |
| `admin_password_secret` | `example-eda-admin-password` | §3 | Active |
| `route_tls_secret` | `eda-route-tls-secret` | §4 | Active |
| `bundle_cacert_secret` | `eda-bundle-ca-secret` | §5 | Optional |
| `image_pull_secrets` | `eda-image-pull-secret` | §6 | Optional |
| `ingress_tls_secret` | `eda-ingress-tls-secret` | §7 | Optional |
| `redis.redis_secret` | `eda-redis-configuration` | §8 | Optional (CRD: 2.5+ only; deprecated in later operators) |

## Secret data key reference

| Component | CRD field | Required secret data keys |
|-----------|-----------|---------------------------|
| Controller | `secret_key_secret` | `secret_key` |
| Controller | `postgres_configuration_secret` | `host`, `port`, `database`, `username`, `password`, `sslmode`, `type` |
| Controller | `ee_pull_credentials_secret` | `username`, `password`, `url` |
| Controller | `admin_password_secret` | `password` |
| Controller | `broadcast_websocket_secret` | `broadcast_websocket_secret` |
| Controller | `ldap_cacert_secret` | `ldap-ca.crt` |
| Controller | `ldap_password_secret` | `password` |
| Controller | `bundle_cacert_secret` | `bundle-ca.crt` |
| Controller | `route_tls_secret` / `ingress_tls_secret` | `tls.crt`, `tls.key` (`kubernetes.io/tls`) |
| Controller | `image_pull_secrets` | `.dockerconfigjson` (`kubernetes.io/dockerconfigjson`) |
| Hub | `db_fields_encryption_secret` | `database_fields.symmetric.key` |
| Hub | `postgres_configuration_secret` | same as Controller Postgres |
| Hub | `object_storage_s3_secret` | `s3-access-key-id`, `s3-secret-access-key`, `s3-bucket-name`, `s3-region` |
| Hub | `object_storage_azure_secret` | `azure-account-name`, `azure-account-key`, `azure-container`, etc. |
| Hub | `sso_secret` | Keycloak fields (`keycloak_host`, `social_auth_keycloak_secret`, …) |
| Hub | `signing_secret` | `signing_service.gpg` |
| Hub | `container_token_secret` | `container_auth_private_key.pem`, `container_auth_public_key.pem` |
| Hub | `admin_password_secret` | `password` |
| EDA | `db_fields_encryption_secret` | `secret_key` |
| EDA | `database.database_secret` | same as Controller Postgres |
| EDA | `admin_password_secret` | `password` |

## How this fits together

The AAP 2.4 operator uses component-level Custom Resources rather than a single monolithic deployment manifest. Each CR's `spec` references Kubernetes Secret names; the operator reads those secrets at reconcile time.

All three components default to **OpenShift Routes** (`ingress_type: Route`) with separate TLS secrets. Switch to `ingress_type: Ingress` and use the `ingress_tls_secret` examples in the secret files if deploying on vanilla Kubernetes.

## External Postgres

When using an external database, Postgres secrets must use: `host`, `port`, `database`, `username`, `password`, `sslmode`, `type`. Avoid single quotes (`'`), double quotes (`"`), and backslashes (`\`) in the password value.

### Hub requires `hstore`

```shell
psql -d automationhub -c "CREATE EXTENSION IF NOT EXISTS hstore;"
```

## Regenerating CR examples

```shell
cd /path/to/openshift-playground/dump-aap-crds
./dump-aap-crds.sh --versions 2.4

cd ../generate-aap-cr-examples
./generate-aap-cr-examples.sh \
  --crd-dir /path/to/aap-notes/config-examples/.crd-dumps/2.4 \
  --output-dir /path/to/aap-notes/config-examples/AAP24/openshift
```

Review `OVERRIDES` and `COMMENT_PATHS` in the generator when secret naming changes.

## Other 2.4 CR kinds (not covered here)

Your CRD dump also includes **AnsibleLightspeed** and **Tower resource CRs** (`JobTemplate`, `AnsibleJob`, etc.) with their own secret fields. Those are out of scope for this folder; see the 2.4 CRD dumps under `config-examples/.crd-dumps/2.4/` for schema reference.

## Constraints and warnings

- **Operator-generated secrets** — If encryption keys, admin passwords, or websocket secrets are omitted, the operator creates them. Pre-provision secrets for GitOps and migration.
- **Hub storage** — S3 **or** Azure, not both.
- **Hub signing** — Requires both `signing_secret` and `signing_scripts_configmap`.
- **EDA Redis** — Present in the 2.4 CRD but marked effective for 2.5+; later EDA operators use dispatcherd (PostgreSQL) instead of Redis.
- **EE pull credentials** — `ee_pull_credentials_secret` supplies registry auth for execution environments.
- **EDA → Controller** — Set `automation_server_url` to a URL reachable from EDA pods.
