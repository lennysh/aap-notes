# AAP Notes

Personal reference material for [Ansible Automation Platform (AAP)](https://www.redhat.com/en/technologies/management/ansible). This repo was formerly **aap-rbac-notes**; RBAC content now lives under `rbac/`, and additional topics are organized in their own folders as they are added.

## Contents

| Folder | Description |
|--------|-------------|
| [`rbac/`](rbac/) | RBAC concepts, role catalogs, hierarchy diagrams, organizational design guidance, and agent-oriented lookup material |
| [`config-examples/`](config-examples/) | Example deployment manifests and related notes (not production-ready templates). **AAP 2.4** uses component CRs directly; **AAP 2.5+** uses the `AnsibleAutomationPlatform` platform CR. |

## Quick links

- **RBAC overview and file index** — [`rbac/README.md`](rbac/README.md)
- **OpenShift operator examples** — [`AAP 2.4`](config-examples/AAP24/openshift/README.md) · [`AAP 2.5`](config-examples/AAP25/openshift/README.md) · [`AAP 2.6`](config-examples/AAP26/openshift/README.md) · [`AAP 2.7`](config-examples/AAP27/openshift/README.md)

## Using with Cursor / other agents

Add this repo to your workspace, then `@`-mention the doc that matches your question:

- RBAC goals and role lookup → `rbac/AAP-RBAC-AGENT-CONTEXT.md`
- Deployment secrets and CR wiring → `config-examples/AAP24/openshift/` (or the matching `AAP25` / `AAP26` / `AAP27` folder for your version)

Most material under `rbac/` was derived from local forks of upstream AAP component repos; see [`rbac/README.md`](rbac/README.md) for the source list.
