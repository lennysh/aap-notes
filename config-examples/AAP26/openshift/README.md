# AAP 2.6 on OpenShift — Example Manifests

Same **platform-first** model as 2.5 — one `AnsibleAutomationPlatform` CR with all component options under `spec.controller`, `spec.hub`, and `spec.eda`. See [AAP 2.5 README](../AAP25/openshift/README.md) for the full explanation.

## Files

| File | Purpose |
|------|---------|
| [secrets-aap.yml](secrets-aap.yml) | Platform + optional component secrets |
| [aap.yml](aap.yml) | `AnsibleAutomationPlatform` CR |

Component CRD field reference: `config-examples/.crd-dumps/2.6/`

## Deployment order

```shell
oc create namespace aap
oc apply -f secrets-aap.yml
oc apply -f aap.yml
```

## Version notes (2.6 vs 2.5)

- **`aap.yml`** adds optional `mcp` and `metrics` platform blocks
- Component CRDs add `postgres_extra_settings` and related fields — set them under the nested component blocks in `aap.yml`

## Regenerating

```shell
python3 generate-aap-cr-examples.py \
  --version 2.6 \
  --crd-dir /path/to/aap-notes/config-examples/.crd-dumps/2.6 \
  --output-dir /path/to/aap-notes/config-examples/AAP26/openshift \
  --kinds AnsibleAutomationPlatform
```
