# AAP 2.4 on OpenShift — Example Manifests

Example Kubernetes manifests for deploying Ansible Automation Platform 2.4 with the Red Hat AAP Operator on OpenShift. Secrets are split from Custom Resources so credentials stay out of CR specs.

These are reference examples — replace placeholder values, trim secrets you do not need, and validate against your environment before applying.

All manifests target the `aap` namespace. Create it (or change `namespace` everywhere) before deploying. Do **not** deploy AAP into the `default` namespace.

## Files

| File | Purpose |
|------|---------|
| [secrets-controller.yml](secrets-controller.yml) | Controller secrets — Postgres, secret key, EE pull creds, route TLS; optional LDAP/bundle CA commented out |
| [secrets-hub.yml](secrets-hub.yml) | Hub secrets — Postgres, encryption key, route TLS, S3 storage; optional SSO/Azure commented out |
| [controller.yml](controller.yml) | `AutomationController` CR referencing controller secrets |
| [hub.yml](hub.yml) | `AutomationHub` CR referencing hub secrets |

## Deployment order

1. Create the namespace (if it does not exist).
2. Enable the PostgreSQL `hstore` extension on the Hub database (required for external Postgres — see below).
3. Replace TLS placeholders or create TLS secrets with real certificates.
4. Apply secret manifests so every secret referenced in the CRs exists first.
5. Apply the Custom Resources.

```shell
oc create namespace aap

# Optional: create TLS secrets from real cert/key files instead of editing YAML placeholders
# oc create secret tls controller-route-tls-secret --cert=controller.crt --key=controller.key -n aap
# oc create secret tls hub-route-tls-secret --cert=hub.crt --key=hub.key -n aap

# Stage secrets before the operator reconciles CRs
oc apply -f secrets-controller.yml
oc apply -f secrets-hub.yml

# Deploy component CRs (secret names in spec must match the secrets above)
oc apply -f controller.yml
oc apply -f hub.yml
```

## How this fits together

The AAP 2.4 operator uses component-level Custom Resources (`AutomationController`, `AutomationHub`, and others) rather than a single monolithic deployment manifest. Each CR's `spec` references Kubernetes Secret names; the operator reads those secrets at reconcile time.

Both components use **OpenShift Routes** (`ingress_type: Route`) with separate TLS secrets. If you use one wildcard certificate for both hostnames, you can point both CRs at the same secret name or duplicate the PEM into `controller-route-tls-secret` and `hub-route-tls-secret`.

**Controller** ([controller.yml](controller.yml)) wires Postgres, the Django `secret_key`, execution-environment registry pull credentials, and route TLS. Optional LDAP and custom CA bundle secrets are commented out in both the secret file and CR — uncomment matching pairs when needed.

**Hub** ([hub.yml](hub.yml)) wires Postgres, `db_fields_encryption_secret` (database field encryption), S3 object storage, and route TLS. Optional SSO (Keycloak) and Azure storage are commented out — uncomment the matching secret block and CR field for your environment.

## External Postgres

When using an external database, the `postgres_configuration_secret` must use this key mapping: `host`, `port`, `database`, `username`, `password`, `sslmode`, `type`. Avoid single quotes (`'`), double quotes (`"`), and backslashes (`\`) in the password value to prevent restore failures.

### Hub requires `hstore`

For external Hub Postgres, enable the `hstore` extension **before** installing Hub (AAP 2.4 migration scripts depend on it):

```shell
psql -d automationhub -c "CREATE EXTENSION IF NOT EXISTS hstore;"
```

Installation fails during database migration if `hstore` is missing.

## Optional features

| Feature | Secret file | CR field | Notes |
|---------|-------------|----------|-------|
| Custom CA bundle | `secrets-controller.yml` §6 | `bundle_cacert_secret` | Outbound TLS trust |
| LDAP | `secrets-controller.yml` §7–8 | `ldap_cacert_secret`, `ldap_password_secret` | CA data key must be `ldap-ca.crt` |
| Hub SSO / Keycloak | `secrets-hub.yml` §5 | `sso_secret` | Private Hub + RH SSO only |
| Azure storage | `secrets-hub.yml` §6 | `object_storage_azure_secret` | Disable S3 secret/field when using Azure |

## Constraints and warnings

- **Admin password** — If `admin_password_secret` is omitted on `AutomationController`, the operator looks for `<resourcename>-admin-password` (e.g. `example-controller-admin-password`) or auto-generates one.
- **Secret keys** — Controller uses `secret_key_secret` → secret data key `secret_key`. Hub uses `db_fields_encryption_secret` → secret data key `database_fields.symmetric.key`. Use stable keys in production; the operator generates new ones if omitted, which breaks migration and credential decryption.
- **TLS secrets** — Replace PEM placeholders in the YAML or create secrets with `oc create secret tls` before applying CRs.
- **Hub storage** — Deploy S3 **or** Azure, not both. Comment out S3 in [secrets-hub.yml](secrets-hub.yml) and [hub.yml](hub.yml) when switching to Azure.
- **EE pull credentials** — `ee_pull_credentials_secret` supplies `username`, `password`, and `url` for authenticated registries (e.g. `registry.redhat.io`).
