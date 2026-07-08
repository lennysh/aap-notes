# AAP 2.7 on OpenShift — Example Manifests

Same **platform-first** model as 2.5 — one `AnsibleAutomationPlatform` CR with all component options under `spec.controller`, `spec.hub`, and `spec.eda`. See [AAP 2.5 README](../AAP25/openshift/README.md) for the full explanation.

## Files

| File | Purpose |
|------|---------|
| [secrets-aap.yml](secrets-aap.yml) | Platform + optional component secrets |
| [aap.yml](aap.yml) | `AnsibleAutomationPlatform` CR |

Component CRD field reference: `config-examples/.crd-dumps/2.7/`

## Deployment order

```shell
oc create namespace aap
oc apply -f secrets-aap.yml
oc apply -f aap.yml
```

## Version notes (2.7 vs 2.6)

- **`aap.yml`** adds `gateway_timeouts`
- **EDA** options such as `event_stream.database_secret` and `event_persistence.database_secret` go under `spec.eda` in `aap.yml` (see EDA CRD dump)
- **`redis.eda_redis_secret`** on the platform CR is deprecated — EDA uses PostgreSQL/dispatcherd

## Regenerating

```shell
python3 generate-aap-cr-examples.py \
  --version 2.7 \
  --crd-dir /path/to/aap-notes/config-examples/.crd-dumps/2.7 \
  --output-dir /path/to/aap-notes/config-examples/AAP27/openshift \
  --kinds AnsibleAutomationPlatform
```
