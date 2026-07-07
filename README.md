# AAP Notes

Personal reference material for [Ansible Automation Platform (AAP)](https://www.redhat.com/en/technologies/management/ansible). This repo was formerly **aap-rbac-notes**; RBAC content now lives under `rbac/`, and additional topics are organized in their own folders as they are added.

## Contents

| Folder | Description |
|--------|-------------|
| [`rbac/`](rbac/) | RBAC concepts, role catalogs, hierarchy diagrams, organizational design guidance, and agent-oriented lookup material |
| [`config-examples/`](config-examples/) | Example deployment manifests and related notes (not production-ready templates) |

## Quick links

- **RBAC overview and file index** — [`rbac/README.md`](rbac/README.md)
- **OpenShift AAP 2.4 operator examples** — [`config-examples/AAP24/openshift/README.md`](config-examples/AAP24/openshift/README.md)

## Using with Cursor / other agents

Add this repo to your workspace, then `@`-mention the doc that matches your question:

- RBAC goals and role lookup → `rbac/AAP-RBAC-AGENT-CONTEXT.md`
- Deployment secrets and CR wiring → `config-examples/AAP24/openshift/`

Most material under `rbac/` was derived from local forks of upstream AAP component repos; see [`rbac/README.md`](rbac/README.md) for the source list.
