# AAP Config Examples

Example Kubernetes manifests for deploying [Ansible Automation Platform (AAP)](https://www.redhat.com/en/technologies/management/ansible) with the Red Hat AAP Operator on OpenShift. These are **reference material**, not production-ready templates — replace placeholder values, trim secrets you do not need, and validate against your environment before applying.

Secrets are kept in separate YAML files from Custom Resources so credentials stay out of CR specs.

## Layout

| Folder | AAP version | Deployment model | OpenShift docs |
|--------|-------------|------------------|----------------|
| [`AAP24/openshift/`](AAP24/openshift/) | 2.4 | Component CRs (`AutomationController`, `AutomationHub`, `EDA`) | [README](AAP24/openshift/README.md) |
| [`AAP25/openshift/`](AAP25/openshift/) | 2.5 | Platform CR (`AnsibleAutomationPlatform`) | [README](AAP25/openshift/README.md) |
| [`AAP26/openshift/`](AAP26/openshift/) | 2.6 | Platform CR | [README](AAP26/openshift/README.md) |
| [`AAP27/openshift/`](AAP27/openshift/) | 2.7 | Platform CR | [README](AAP27/openshift/README.md) |

All examples target the `aap` namespace. Create it (or change `namespace` everywhere) before deploying. Do **not** deploy AAP into the `default` namespace.

## AAP 2.4 vs 2.5+

**AAP 2.4** uses one Custom Resource per component. You apply separate secret manifests, then `controller.yml`, `hub.yml`, and `eda.yml`. See [AAP24/openshift/README.md](AAP24/openshift/README.md) for the full secret catalog and deployment order.

**AAP 2.5 and later** use a single **`AnsibleAutomationPlatform`** CR. The operator creates the platform gateway and manages child component CRs from nested `spec.controller`, `spec.hub`, and `spec.eda` blocks. You apply `secrets-aap.yml`, then `aap.yml`. The [AAP 2.5 README](AAP25/openshift/README.md) is the primary reference for this model; 2.6 and 2.7 READMEs call out version-specific deltas.

## Typical apply order (2.5+)

```shell
oc create namespace aap
oc apply -f secrets-aap.yml
oc apply -f aap.yml
```

For 2.4, apply component secret files first, then the component CRs — see the version README for the full sequence.

## Regenerating examples

CR example YAML is generated from operator CRD dumps using [generate-aap-cr-examples](https://github.com/lennysh/openshift-playground/tree/main/generate-aap-cr-examples) in **openshift-playground**. CRD dumps are stored under `.crd-dumps/<version>/` (local, not committed).

Each version README includes the exact `generate-aap-cr-examples.py` invocation and output path.

## Using with Cursor / other agents

`@`-mention the folder for your AAP version when asking about deployment wiring, secret field names, or CR spec options:

- **2.4** — `config-examples/AAP24/openshift/` (component CRs and per-component secret files)
- **2.5+** — `config-examples/AAP25/openshift/` (platform CR model; use AAP26/AAP27 folders for version-specific fields)

Pair with [`rbac/`](../rbac/) when questions span both deployment and access control.

## Constraints

- **Not production templates** — placeholder passwords, example hostnames, and commented optional blocks are intentional.
- **External Postgres** — Hub requires the `hstore` extension when using an external database (documented in the 2.4 and 2.5 READMEs).
- **Operator-generated secrets** — Omitting encryption keys or admin passwords lets the operator create them; pre-provision secrets for GitOps and migration.
- **Hub storage** — S3 or Azure, not both.
