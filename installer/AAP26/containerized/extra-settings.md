# AAP 2.6 — Containerized `*_extra_settings` reference

Personal TSE notes for every inventory “extra settings” pass-through in the **AAP 2.6 containerized installer**.

Verified against lab clone `aap-26/installer/containerized_installer` (aligned with dump `ansible-automation-platform-containerized-setup-2.6-10`).

These variables are **not closed enums**. Most accept arbitrary keys that the target component understands. Prefer dedicated inventory vars (DB, nginx, TLS, storage, Redis) when they exist; use `*_extra_settings` for app/Django/Pulp/PostgreSQL knobs the installer does not expose directly.

Related files in this folder: [README.md](README.md) · [vars-example.yml](vars-example.yml).  
Sibling for 2.7: [AAP27/containerized/extra-settings.md](../../AAP27/containerized/extra-settings.md).

### Notable vs 2.7

| Area | 2.6 | 2.7 |
|---|---|---|
| EDA extras surface | Includes **Redis/MQ** settings (`MQ_*`, `RQ_REDIS_PREFIX`, TTLs) | Event **persistence / stream DB** settings instead |
| MCP built-in env | `BASE_URL`, `IGNORE_CERTIFICATE_ERRORS`, `ALLOW_WRITE_OPERATIONS`, `INTERNAL_EMAIL_DOMAINS` | Same **plus** `MCP_SERVER_URL` |
| Metrics Service lab tree | `automation-dashboard/automation-reports/` | `automation-dashboard/metrics-service/` |
| Inventory var set | Same names / shapes as 2.7 for these extras | — |

---

## Index

| Inventory variable | Shape | Default | Written into | Component |
|---|---|---|---|---|
| [`controller_extra_settings`](#controller_extra_settings) | list of `{setting, value}` | `[]` | Controller `settings.py` (Python) | Controller |
| [`metrics_utility_extra_settings`](#metrics_utility_extra_settings) | list of `{setting, value}` | *(required when enabled)* | Controller metrics-utility `.env` (`KEY=value`) | Controller metrics-utility |
| [`hub_extra_settings`](#hub_extra_settings) | list of `{setting, value}` | `[]` | Hub `/etc/pulp/settings.py` (Python) | Automation Hub |
| [`hub_azure_extra_settings`](#hub_azure_extra_settings) | dict | `{}` | Hub `settings.py` Azure keys | Hub + Azure storage |
| [`hub_s3_extra_settings`](#hub_s3_extra_settings) | dict | `{}` | Hub `settings.py` AWS keys | Hub + S3 storage |
| [`eda_extra_settings`](#eda_extra_settings) | list of `{setting, value}` | `[]` | EDA `settings.yaml` | EDA |
| [`gateway_extra_settings`](#gateway_extra_settings) | list of `{setting, value}` | `[]` | Gateway `settings.py` (Python) | Gateway |
| [`automationmetrics_extra_settings`](#automationmetrics_extra_settings) | list of `{setting, value}` | `[]` | Metrics Service `settings.yaml` | Automation Metrics |
| [`lightspeed_extra_settings`](#lightspeed_extra_settings) | list of `{setting, value}` | `[]` | Lightspeed `settings.py` (Python) | Lightspeed (wisdom service) |
| [`lightspeed_chatbot_model_extra_settings`](#lightspeed_chatbot_model--agent_extra_settings) | dict | `{}` | Chatbot run YAML `providers.inference[].config` | Lightspeed chatbot |
| [`lightspeed_chatbot_agent_extra_settings`](#lightspeed_chatbot_model--agent_extra_settings) | dict | `{}` | Chatbot run YAML `providers.agents[].config` | Lightspeed chatbot |
| [`mcp_extra_settings`](#mcp_extra_settings) | list of `{setting, value}` | `[]` | MCP container env | Ansible MCP |
| [`postgresql_extra_settings`](#postgresql_extra_settings) | list of `{setting, value}` | `[]` | `postgresql.conf` | Managed PostgreSQL |

> `lightspeed_extra_settings` exists in the role defaults/template but is **not** listed in the installer README table. Still valid.

---

## Common list format

Used by Controller, Hub (app), EDA, Gateway, Metrics Service, Lightspeed app, MCP, PostgreSQL, metrics-utility:

```yaml
component_extra_settings:
  - setting: SOME_SETTING_NAME
    value: some_value          # string → quoted in Python/YAML templates; non-string → raw
  - setting: ANOTHER_SETTING
    value: True
  - setting: NESTED_OR_BRACKET['KEY']
    value: 600
```

Template rule (Python/`settings.py` style):

- string values → `SETTING = 'value'`
- non-strings → `SETTING = value` (booleans, ints, lists, dicts as YAML→Python)

YAML-style components (`eda`, `automationmetrics`) emit `SETTING: value` / `SETTING: 'value'` instead.

Dict-style variables (`hub_azure_*`, `hub_s3_*`, chatbot extras) are plain maps, not `{setting, value}` lists.

---

## `controller_extra_settings`

| | |
|---|---|
| **Role** | `roles/automationcontroller` |
| **Template** | `templates/settings.py.j2` (appended near end) |
| **README example** | `USE_X_FORWARDED_HOST: true` |

```yaml
controller_extra_settings:
  - setting: USE_X_FORWARDED_HOST
    value: true
```

### What can go here

Open-ended **Django / AWX settings.py** assignments. Not the same as settings persisted via the Controller UI/API (`/api/v2/settings/all/`), though many names overlap.

Installer comment in the template: custom values you want to survive upgrades must go through `controller_extra_settings` (the generated file is overwritten on upgrade).

Useful local references (lab tree):

- `aap-26/controller/automation-controller/awx/settings/production_defaults.py`
- `aap-26/controller/automation-controller/awx/settings/defaults.py` (large conf registry; mostly **DB-backed** UI settings — prefer API/UI for those)

Common inventory-side examples (not exhaustive):

| Setting | Notes |
|---|---|
| `USE_X_FORWARDED_HOST` | Installer README example |
| `REMOTE_HOST_HEADERS` | Proxy / X-Forwarded handling |
| `SESSION_COOKIE_AGE` | Session lifetime |
| `CSRF_TRUSTED_ORIGINS` | Prefer not to fight installer-managed gateway origins |
| `LOGGING[...]` / nested keys | Possible; easy to break — merge carefully |

**Avoid overriding** installer-managed blocks already written earlier in `settings.py.j2` (DB, Redis, JWT/gateway integration) unless you have a clear need — extras are appended last, so they *can* override.

---

## `metrics_utility_extra_settings`

| | |
|---|---|
| **Role** | `roles/automationcontroller` |
| **Template** | `templates/metrics.env.j2` → `SETTING=value` env lines |
| **When required** | `metrics_utility_enabled=true` (preflight asserts non-empty list) |

```yaml
metrics_utility_enabled: true
metrics_utility_extra_settings:
  - setting: METRICS_UTILITY_PRICE_PER_NODE
    value: 100
  - setting: METRICS_UTILITY_REPORT_COMPANY_NAME
    value: Example Corp
  - setting: METRICS_UTILITY_REPORT_EMAIL
    value: reports@example.com
  - setting: METRICS_UTILITY_REPORT_SKU
    value: EXAMPLE-SKU
  - setting: METRICS_UTILITY_REPORT_TYPE
    value: CCS
```

### Required keys (preflight)

When metrics-utility is enabled, preflight **requires** all of:

- `METRICS_UTILITY_PRICE_PER_NODE`
- `METRICS_UTILITY_REPORT_COMPANY_NAME`
- `METRICS_UTILITY_REPORT_EMAIL`
- `METRICS_UTILITY_REPORT_SKU`
- `METRICS_UTILITY_REPORT_TYPE`

Additional `METRICS_UTILITY_*` env vars may be accepted by the metrics-utility binary; this installer only hard-validates the five above. Values are written literally (`{{ item.setting }}={{ item.value }}`) — not Python-quoted.

---

## `hub_extra_settings`

| | |
|---|---|
| **Role** | `roles/automationhub` |
| **Template** | `templates/settings.py.j2` (appended after gateway/auth blocks) |
| **README example** | `REDIRECT_IS_HTTPS: True` |

```yaml
hub_extra_settings:
  - setting: REDIRECT_IS_HTTPS
    value: True
  - setting: GALAXY_REQUIRE_CONTENT_APPROVAL
    value: False
  - setting: GALAXY_FEATURE_FLAGS__execution_environments
    value: True
```

### Documented Galaxy options

From Hub docs `aap-26/hub/automation-hub/docs/config/options.md` (intended customization surface):

| Setting | Default / notes |
|---|---|
| `GALAXY_API_PATH_PREFIX` | `"/api/galaxy"` |
| `GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH` | `"published"` |
| `GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH` | `"staging"` |
| `GALAXY_API_REJECTED_DISTRIBUTION_BASE_PATH` | `"rejected"` |
| `GALAXY_REQUIRE_CONTENT_APPROVAL` | `True` |
| `GALAXY_FEATURE_FLAGS` | dict — see feature flags below |
| `GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS` | `False` |
| `GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD` | `False` |
| `GALAXY_ENABLE_API_ACCESS_LOG` | `False` |
| `CONNECTED_ANSIBLE_CONTROLLERS` | `[]` |
| `CONTENT_PATH_PREFIX` | content URL prefix |
| `GALAXY_AUTHENTICATION_CLASSES` | DRF auth classes |
| `GALAXY_PERMISSION_CLASSES` | `[]` |
| `GALAXY_AUTO_SIGN_COLLECTIONS` | `False` (also via `hub_collection_auto_sign`) |
| `GALAXY_COLLECTION_SIGNING_SERVICE` | also via `hub_collection_signing*` |
| `GALAXY_CONTAINER_SIGNING_SERVICE` | also via `hub_container_signing*` |
| `GALAXY_SIGNATURE_UPLOAD_ENABLED` | `False` |
| `GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL` | `False` |
| `GALAXY_MINIMUM_PASSWORD_LENGTH` | `9` |
| `GALAXY_DYNAMIC_SETTINGS` | `False` |
| `CONTENT_BIND` | Pulp content bind |
| `DEFAULT_FILE_STORAGE` | storage backend class |
| `ANSIBLE_API_HOSTNAME` | usually installer-managed via gateway URL |
| `SESSION_COOKIE_AGE` | default `1209600` |
| `ANSIBLE_COLLECT_DOWNLOAD_LOG` | enable collection download log |

### `GALAXY_FEATURE_FLAGS` keys

From `docs/config/featureflags.md`:

- `signatures_enabled`
- `require_upload_signatures`
- `can_create_signatures`
- `can_upload_signatures`
- `collection_auto_sign`
- `display_signatures`
- `execution_environments`
- `container_signing`
- `ai_deny_index`
- `display_repositories`

Nested form: `GALAXY_FEATURE_FLAGS__execution_environments = True`  
Or merge dict with `"dynaconf_merge": True`.

### Immutable (Galaxy forces final value)

- `REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES`
- `ANSIBLE_URL_NAMESPACE`
- `ANSIBLE_DEFAULT_DISTRIBUTION_PATH`

### Broader surface

Any Pulp/Django/`galaxy_ng` setting can be injected. Local sources:

- Defaults: `aap-26/hub/automation-hub/galaxy_ng/app/settings.py`
- Pulpcore settings notes: `aap-26/hub/pulp/pulpcore/staging_docs/admin/learn/settings.md` (and related staging_docs)

Prefer dedicated inventory vars for signing (`hub_collection_signing`, etc.), storage backend, DB, and nginx.

---

## `hub_azure_extra_settings`

| | |
|---|---|
| **When** | `hub_storage_backend=azure` |
| **Shape** | dict (keys uppercased in template) |
| **Upstream catalog** | [django-storages Azure settings](https://django-storages.readthedocs.io/en/latest/backends/azure.html#settings) |

```yaml
hub_storage_backend: azure
hub_azure_account_name: ...
hub_azure_account_key: ...
hub_azure_extra_settings:
  AZURE_LOCATION: foo
  AZURE_SSL: True
  AZURE_URL_EXPIRATION_SECS: 60
```

Required siblings: `hub_azure_account_name`, `hub_azure_account_key` (container defaults to `pulp`).

---

## `hub_s3_extra_settings`

| | |
|---|---|
| **When** | `hub_storage_backend=s3` |
| **Shape** | dict (keys uppercased in template) |
| **Upstream catalog** | [django-storages S3 settings](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings) |

```yaml
hub_storage_backend: s3
hub_s3_access_key: ...
hub_s3_secret_key: ...
hub_s3_extra_settings:
  AWS_S3_MAX_MEMORY_SIZE: 4096
  AWS_S3_REGION_NAME: eu-central-1
  AWS_S3_USE_SSL: True
```

---

## `eda_extra_settings`

| | |
|---|---|
| **Role** | `roles/automationeda` |
| **Template** | `templates/settings.yaml.j2` |
| **README example** | `RULEBOOK_READINESS_TIMEOUT_SECONDS: 120` |

```yaml
eda_extra_settings:
  - setting: RULEBOOK_READINESS_TIMEOUT_SECONDS
    value: 120
```

### Useful keys from EDA defaults (2.6)

Source: `aap-26/eda/automation-eda-controller/src/aap_eda/settings/defaults.py` (open-ended).

**Rulebook / activation (same family as 2.7):**

| Setting | Notes |
|---|---|
| `RULEBOOK_READINESS_TIMEOUT_SECONDS` | default `60` in code; README example `120` |
| `RULEBOOK_LIVENESS_CHECK_SECONDS` | — |
| `RULEBOOK_LIVENESS_TIMEOUT_SECONDS` | — |
| `ACTIVATION_RESTART_SECONDS_ON_COMPLETE` | — |
| `ACTIVATION_RESTART_SECONDS_ON_FAILURE` | — |
| `ACTIVATION_MAX_RESTARTS_ON_FAILURE` | — |
| `DEFAULT_QUEUE_TIMEOUT` | — |
| `DEFAULT_RULEBOOK_QUEUE_TIMEOUT` | — |
| `SESSION_COOKIE_AGE` | — |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | — |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | — |
| `PODMAN_MEM_LIMIT` / `PODMAN_ENV_VARS` / `PODMAN_EXTRA_ARGS` | — |
| `EVENT_STREAM_REQUIRE_TRUSTED_PROXY` | — |
| `MAX_PG_NOTIFY_MESSAGE_SIZE` | — |

**2.6-specific Redis / message-queue surface** (prefer dedicated `eda_redis_*` inventory vars when present):

| Setting | Notes |
|---|---|
| `MQ_HOST` / `MQ_PORT` / `MQ_DB` | Redis connection |
| `MQ_USER` / `MQ_USER_PASSWORD` | Redis auth |
| `MQ_TLS` | TLS enable |
| `MQ_CLIENT_CACERT_PATH` / `MQ_CLIENT_CERT_PATH` / `MQ_CLIENT_KEY_PATH` | TLS material |
| `MQ_UNIX_SOCKET_PATH` | Unix socket |
| `MQ_REDIS_HA_CLUSTER_HOSTS` | HA cluster hosts |
| `MQ_SOCKET_TIMEOUT` / `MQ_SOCKET_CONNECT_TIMEOUT` / `MQ_SOCKET_KEEP_ALIVE` | Socket tuning |
| `MQ_CLUSTER_ERROR_RETRY_ATTEMPTS` | Cluster retry |
| `RQ_REDIS_PREFIX` | RQ key prefix |
| `DEFAULT_RESULT_TTL` / `DEFAULT_FAILURE_TTL` | Result retention |

Prefer dedicated inventory vars for EDA DB, Redis (`eda_redis_*` in 2.6), and nginx.

---

## `gateway_extra_settings`

| | |
|---|---|
| **Role** | `roles/automationgateway` |
| **Template** | `templates/settings.py.j2` |
| **README example** | `OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS']: 600` |

```yaml
gateway_extra_settings:
  - setting: OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS']
    value: 600
```

### Useful keys from Gateway defaults

Source: `aap-26/gateway/automation-gateway/aap_gateway_api/defaults.py` (subset; open-ended Django/DAB surface):

| Setting | Notes |
|---|---|
| `OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS']` | README example (bracket syntax in Python) |
| `GATEWAY_ACCESS_TOKEN_EXIPIRATION` | Gateway-specific token expiry (note spelling `EXIPIRATION` in code) |
| `SESSION_COOKIE_AGE` | Session cookie lifetime |
| `CSRF_TRUSTED_ORIGINS` | Usually installer-managed |
| `ENVOY_VERIFY_HTTPS_CERTIFICATES` | Envoy TLS verify |
| `ENVOY_PER_CONNECTION_BUFFER_LIMIT_BYTES` | Envoy buffer |
| `XDS_XFF_NUM_TRUSTED_HOPS` | X-Forwarded-For hops |
| `PING_PAGE_CHECK_TIMEOUT` | Ping page |
| `GRPC_SERVER_*` | gRPC server tuning |
| `RUNTIME_FEATURE_FLAGS` | Feature flags dict |
| `SECURE_PROXY_SSL_HEADER` | Proxy SSL header |

---

## `automationmetrics_extra_settings`

| | |
|---|---|
| **Role** | `roles/automationmetrics` |
| **Template** | `templates/settings.yaml.j2` |
| **README example** | placeholder `SOME_SETTING` |

```yaml
automationmetrics_extra_settings:
  - setting: LOG_LEVEL
    value: DEBUG
```

Installer already sets (do not casually override): `ALLOWED_HOSTS`, `URL_PREFIX` (`/api/metrics`), `DATABASES__*`, `CSRF_TRUSTED_ORIGINS`, `RESOURCE_SERVER__*`, `ANSIBLE_BASE_JWT_*`.

### Local reference in 2.6 lab tree

The 2.6 clone under `aap-26/automation-dashboard/` is **`automation-reports`** (not the later `metrics-service` layout used in 2.7). Useful starting point:

- `aap-26/automation-dashboard/automation-reports/src/backend/django_config/settings.py`

Treat extras as open-ended Dynaconf/Django keys for the metrics image; validate against the running container’s settings if a key is uncertain.

---

## `lightspeed_extra_settings`

| | |
|---|---|
| **Role** | `roles/ansiblelightspeed` |
| **Template** | `templates/lightspeed_settings.py.j2` |
| **README** | *not listed* (role default still `[]`) |

```yaml
lightspeed_extra_settings:
  - setting: CHAT_RATE_THROTTLE
    value: '20/minute'
  - setting: ENABLE_ADDITIONAL_CONTEXT
    value: True
```

Open-ended Django settings for the wisdom/Lightspeed service. Prefer dedicated inventory vars (`lightspeed_wca_*`, `lightspeed_chatbot_*`, etc.) first.

---

## Lightspeed chatbot model / agent `extra_settings`

| Variable | Injected into |
|---|---|
| `lightspeed_chatbot_model_extra_settings` | `ansible-chatbot-run.yaml` → inference provider `config:` |
| `lightspeed_chatbot_agent_extra_settings` | same file → agent provider `config:` |

Shape: **dict** (not list).

```yaml
lightspeed_chatbot_model_extra_settings:
  api_version: "1.0.1"
  api_type: ""

lightspeed_chatbot_agent_extra_settings:
  chatbot_temperature_override: 1.0
```

Model extras are most relevant when `lightspeed_chatbot_default_provider` is `azure` (README). Keys are provider-config fields for the chatbot stack, not Django settings. No installer-side allowlist — valid keys depend on the selected provider type (`rhoai` / `openai` / `azure`).

---

## `mcp_extra_settings`

| | |
|---|---|
| **Role** | `roles/ansiblemcp` |
| **Applied in** | `tasks/containers.yml` → merged into container `env` |
| **Shape** | list of `{setting, value}` → env var name/value |

```yaml
mcp_extra_settings:
  - setting: SOME_ENV_VAR
    value: some_value
```

Built-in env in **2.6** (already set by the role — override only if intentional):

| Env | Source |
|---|---|
| `BASE_URL` | `mcp_public_base_url` or gateway proxy URL |
| `IGNORE_CERTIFICATE_ERRORS` | `mcp_ignore_certificate_errors` |
| `ALLOW_WRITE_OPERATIONS` | `mcp_allow_write_operations` |
| `INTERNAL_EMAIL_DOMAINS` | `mcp_internal_email_domains` |

Extras are `combine()`’d on top of that map. Prefer dedicated MCP inventory vars when present.

> Note: some `vars-example.yml` placeholders may show Gateway-style OAuth under `mcp_extra_settings`; that is **not** meaningful for MCP env injection.

---

## `postgresql_extra_settings`

| | |
|---|---|
| **Role** | `roles/postgresql` |
| **Template** | `templates/postgresql.conf.j2` |
| **README example** | `ssl_ciphers` |

```yaml
postgresql_extra_settings:
  - setting: ssl_ciphers
    value: 'HIGH:!aNULL:!MD5'
```

Open-ended **`postgresql.conf`** parameters. Strings are single-quoted in the conf file.

Prefer dedicated inventory vars when they exist:

- `postgresql_max_connections`
- `postgresql_shared_buffers`
- `postgresql_password_encryption`
- `postgresql_log_destination`
- TLS cert/key vars

Any other valid PostgreSQL GUC can be passed here — validate against the PostgreSQL major version shipped with the 2.6 containerized installer.

---

## Practical guidance

1. **List vs dict** — App extras (Controller/Hub/EDA/Gateway/Metrics/Lightspeed/MCP/PG) are lists of `{setting, value}`. Storage + chatbot model/agent extras are plain dicts.
2. **Last-write wins** — List-style extras are usually appended at the end of the generated settings file, so they can override installer defaults.
3. **Do not use extras for secrets the installer already wires** — DB passwords, secret keys, TLS paths, registry creds, Redis passwords belong in their dedicated vars.
4. **metrics-utility is special** — env file format + hard required report fields when enabled.
5. **Hub storage extras are separate** — `hub_azure_extra_settings` / `hub_s3_extra_settings` are not substitutes for `hub_extra_settings`.
6. **EDA Redis in 2.6** — prefer `eda_redis_*` inventory vars; only fall back to `eda_extra_settings` `MQ_*` when needed.
7. **When stuck** — search the component defaults/docs under `aap-26/` rather than inventing key names from general product knowledge.

---

## Source map (lab)

| Topic | Path under `aap-26/` |
|---|---|
| Installer README tables/examples | `installer/containerized_installer/README.md` |
| Controller settings template | `installer/containerized_installer/roles/automationcontroller/templates/settings.py.j2` |
| Hub settings template | `installer/containerized_installer/roles/automationhub/templates/settings.py.j2` |
| Hub config options | `hub/automation-hub/docs/config/options.md` |
| Hub feature flags | `hub/automation-hub/docs/config/featureflags.md` |
| EDA defaults | `eda/automation-eda-controller/src/aap_eda/settings/defaults.py` |
| Gateway defaults | `gateway/automation-gateway/aap_gateway_api/defaults.py` |
| Metrics / dashboard (2.6 layout) | `automation-dashboard/automation-reports/src/backend/django_config/settings.py` |
| Pulpcore settings notes | `hub/pulp/pulpcore/staging_docs/admin/learn/settings.md` |
