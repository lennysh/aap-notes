# AAP Notes

Personal reference material for [Ansible Automation Platform (AAP)](https://www.redhat.com/en/technologies/management/ansible). This repo was formerly **aap-rbac-notes**; RBAC content now lives under `rbac/`, and additional topics are organized in their own folders as they are added.

## Contents

| Folder | Description |
|--------|-------------|
| [`rbac/`](rbac/) | RBAC concepts, role catalogs, hierarchy diagrams, organizational design guidance, and agent-oriented lookup material |
| [`config-examples/`](config-examples/) | Example deployment configuration (not production-ready templates). **OpenShift:** AAP 2.4 uses component CRs; 2.5+ uses the `AnsibleAutomationPlatform` platform CR. **Containerized:** annotated Ansible inventories for 2.5, 2.6, and 2.7. |

## Quick links

- **RBAC overview and file index** — [`rbac/README.md`](rbac/README.md)
- **Config examples index** — [`config-examples/README.md`](config-examples/README.md)
- **OpenShift operator examples** — [`AAP 2.4`](config-examples/AAP24/openshift/README.md) · [`AAP 2.5`](config-examples/AAP25/openshift/README.md) · [`AAP 2.6`](config-examples/AAP26/openshift/README.md) · [`AAP 2.7`](config-examples/AAP27/openshift/README.md)
- **Containerized installer examples** — [`AAP 2.5`](config-examples/AAP25/containerized/README.md) · [`AAP 2.6`](config-examples/AAP26/containerized/README.md) · [`AAP 2.7`](config-examples/AAP27/containerized/README.md)

## Using with Cursor / other agents

Add this repo to your workspace, then `@`-mention the doc that matches your question:

- RBAC goals and role lookup → `rbac/AAP-RBAC-AGENT-CONTEXT.md`
- OpenShift secrets and CR wiring → `config-examples/AAP24/openshift/` (or the matching `AAP25` / `AAP26` / `AAP27` folder for your version)
- Containerized installer inventory options → `config-examples/AAP25/containerized/`, `AAP26/containerized/`, or `AAP27/containerized/` (or `config-examples/CONTAINERIZED_INVENTORY_CONTEXT.md` when refreshing inventories)

Most material under `rbac/` was derived from local forks of upstream AAP component repos; see [`rbac/README.md`](rbac/README.md) for the source list.
