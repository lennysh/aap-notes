#!/usr/bin/env python3
"""Extract install playbook tasks recursively into markdown reference docs."""

from __future__ import annotations

import argparse
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RESERVED = frozenset(
    {
        "name",
        "when",
        "register",
        "loop",
        "with_items",
        "with_dict",
        "with_nested",
        "with_fileglob",
        "with_together",
        "with_subelements",
        "with_sequence",
        "with_indexed_items",
        "with_flattened",
        "until",
        "retries",
        "delay",
        "changed_when",
        "failed_when",
        "ignore_errors",
        "delegate_to",
        "run_once",
        "become",
        "become_user",
        "become_method",
        "become_flags",
        "become_exe",
        "vars",
        "args",
        "apply",
        "tags",
        "notify",
        "listen",
        "block",
        "rescue",
        "always",
        "loop_control",
        "environment",
        "no_log",
        "async",
        "poll",
        "throttle",
        "any_errors_fatal",
        "max_fail_percentage",
        "check_mode",
        "diff",
        "local_action",
        "connection",
        "remote_user",
        "gather_facts",
        "hosts",
        "roles",
        "tasks",
        "pre_tasks",
        "post_tasks",
        "handlers",
        "serial",
        "strategy",
        "order",
        "ignore_unreachable",
        "vars_files",
        "vars_prompt",
        "module_defaults",
        "collections",
    }
)

MODULE_HINTS = {
    "include_role": "Include and run tasks from an Ansible role",
    "import_role": "Import and run tasks from an Ansible role (static)",
    "include_tasks": "Include a task file from the current role or playbook",
    "import_tasks": "Import a task file (static include)",
    "include": "Legacy include — runs nested tasks or role",
    "meta": "Ansible meta task (flush handlers, clear facts, etc.)",
    "set_fact": "Set a host fact used by later tasks",
    "assert": "Validate a condition and fail if it is not met",
    "fail": "Fail the play with an error message",
    "pause": "Pause execution and optionally prompt the operator",
    "debug": "Print debug information",
    "stat": "Check whether a file or path exists and gather metadata",
    "slurp": "Read a file from the remote host into a variable",
    "template": "Render a Jinja2 template to a file on the host",
    "copy": "Copy a file to the host",
    "file": "Manage files, directories, or symlinks",
    "lineinfile": "Ensure a specific line exists in a file",
    "blockinfile": "Insert or remove a block of text in a file",
    "replace": "Replace text in a file using regular expressions",
    "command": "Run a command on the host",
    "shell": "Run a shell command on the host",
    "raw": "Run a raw command without the Ansible module subsystem",
    "script": "Copy and execute a local script on the host",
    "systemd": "Manage systemd units (start/stop/enable services)",
    "service": "Manage a traditional service",
    "dnf": "Install or remove RPM packages with dnf",
    "yum": "Install or remove RPM packages with yum",
    "package": "Install or remove packages using the platform package manager",
    "pip": "Manage Python packages with pip",
    "user": "Manage local user accounts",
    "group": "Manage local group accounts",
    "getent": "Look up user/group/database entries",
    "firewalld": "Manage firewalld rules and zones",
    "iptables": "Manage iptables firewall rules",
    "uri": "Interact with HTTP/HTTPS APIs",
    "get_url": "Download a file from a URL",
    "unarchive": "Unpack an archive on the host",
    "archive": "Create an archive from files on the host",
    "cron": "Manage cron jobs",
    "mount": "Manage filesystem mounts",
    "seboolean": "Manage SELinux booleans",
    "selinux": "Manage SELinux mode or policy",
    "authorized_key": "Manage SSH authorized keys",
    "openssh_keypair": "Generate OpenSSH key pairs",
    "openssl_privatekey": "Generate or manage OpenSSL private keys",
    "openssl_csr": "Generate a certificate signing request",
    "openssl_certificate": "Manage TLS certificates",
    "group_by": "Create dynamic inventory groups at runtime",
    "include_vars": "Load variables from a file",
    "set_stats": "Set aggregate statistics for the run",
    "wait_for": "Wait for a port or path to become available",
    "wait_for_connection": "Wait for the host to become reachable",
    "setup": "Gather Ansible facts from the host",
    "calculate_mesh": "Validate and optionally render the Receptor mesh topology",
    "containers.podman.podman_container": "Manage a Podman container",
    "containers.podman.podman_image": "Pull or manage a Podman image",
    "containers.podman.podman_volume": "Manage a Podman volume",
    "containers.podman.podman_network": "Manage a Podman network",
    "containers.podman.podman_secret": "Manage a Podman secret",
    "containers.podman.podman_quadlet": "Manage a Podman Quadlet unit file",
    "ansible.builtin.setup": "Gather Ansible facts from the host",
    "ansible.builtin.include_role": "Include and run tasks from an Ansible role",
    "ansible.builtin.import_role": "Import and run tasks from an Ansible role (static)",
    "ansible.builtin.include_tasks": "Include a task file from the current role",
    "ansible.builtin.import_tasks": "Import a task file (static include)",
    "ansible.legacy.group_by": "Create dynamic inventory groups at runtime",
}


@dataclass
class TaskRow:
    order: int
    path: str
    name: str
    description: str
    when: str = ""


@dataclass
class Extractor:
    collections_root: Path
    primary_roles_dir: Path
    collection_name: str
    rows: list[TaskRow] = field(default_factory=list)
    _counter: int = 0
    _stack: list[tuple[str, str]] = field(default_factory=list)
    role_tasks_dirs: dict[str, Path] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.role_tasks_dirs:
            self.role_tasks_dirs = self._build_role_index()

    def _build_role_index(self) -> dict[str, Path]:
        index: dict[str, Path] = {}
        for tasks_dir in self.collections_root.rglob("roles/*/tasks"):
            if tasks_dir.is_dir():
                index.setdefault(tasks_dir.parent.name, tasks_dir)
        return index

    def add_row(self, path: str, name: str, description: str, when: str = "") -> None:
        self._counter += 1
        self.rows.append(
            TaskRow(
                order=self._counter,
                path=path,
                name=name,
                description=description,
                when=when,
            )
        )

    def normalize_role(self, role_name: str) -> str:
        role_name = role_name.strip()
        prefix = f"ansible.{self.collection_name}."
        if role_name.startswith(prefix):
            return role_name[len(prefix) :]
        if role_name.startswith(f"{self.collection_name}."):
            return role_name.split(".", 1)[1]
        return role_name.split(".")[-1]

    def role_tasks_path(self, role_name: str, tasks_from: str | None) -> Path | None:
        short = self.normalize_role(role_name)
        tasks_dir = self.role_tasks_dirs.get(short)
        if tasks_dir is None:
            return None
        tasks_file = "main.yml" if not tasks_from else tasks_from
        if not tasks_file.endswith((".yml", ".yaml")):
            tasks_file = f"{tasks_file}.yml"
        candidate = tasks_dir / tasks_file
        if candidate.exists():
            return candidate
        candidate_yaml = candidate.with_suffix(".yaml")
        if candidate_yaml.exists():
            return candidate_yaml
        return None

    def load_yaml_list(self, path: Path) -> list[Any]:
        text = path.read_text()
        lines = text.splitlines()
        while lines and lines[-1].strip() in ("...", "---"):
            lines.pop()
        data = yaml.safe_load("\n".join(lines))
        if data is None:
            return []
        if isinstance(data, dict):
            return [data]
        return data

    def module_name(self, task: dict[str, Any]) -> str:
        for key in task:
            if key not in RESERVED and not key.startswith("_"):
                return key
        return "unknown"

    def format_when(self, when: Any) -> str:
        if when is None:
            return ""
        if isinstance(when, list):
            return "; ".join(str(item) for item in when)
        return str(when).strip()

    def describe_task(self, task: dict[str, Any], module: str) -> str:
        if task.get("name"):
            return str(task["name"]).strip()
        hint = MODULE_HINTS.get(module, "")
        if hint:
            return hint
        if module.startswith("ansible.builtin."):
            return MODULE_HINTS.get(module[16:], f"Run the {module} module")
        return f"Run the {module} module"

    def task_summary(self, task: dict[str, Any]) -> str:
        module = self.module_name(task)
        name = task.get("name")
        if name:
            base = str(name).strip()
        else:
            base = MODULE_HINTS.get(module, f"Run `{module}`")

        extras: list[str] = []
        if module in {"include_role", "import_role", "ansible.builtin.include_role", "ansible.builtin.import_role"}:
            role = task.get("name") or task.get(module, {}).get("name") if isinstance(task.get(module), dict) else task.get("name")
            payload = task.get(module, task)
            if isinstance(payload, str):
                extras.append(f"role `{self.normalize_role(payload)}`")
            elif isinstance(payload, dict):
                if payload.get("name"):
                    extras.append(f"role `{self.normalize_role(str(payload['name']))}`")
                if payload.get("tasks_from"):
                    extras.append(f"tasks `{payload['tasks_from']}`")
        elif module in {"include_tasks", "import_tasks", "ansible.builtin.include_tasks", "ansible.builtin.import_tasks"}:
            payload = task.get(module, "")
            if isinstance(payload, str):
                extras.append(f"file `{payload}`")
        elif module == "meta":
            payload = task.get("meta", "")
            extras.append(str(payload))
        elif module in {"template", "copy", "file"}:
            payload = task.get(module, {})
            if isinstance(payload, dict) and payload.get("dest"):
                extras.append(f"dest `{payload['dest']}`")
        elif module in {"service", "systemd"}:
            payload = task.get(module, {})
            if isinstance(payload, dict) and payload.get("name"):
                extras.append(f"service `{payload['name']}`")

        if extras:
            return f"{base} ({', '.join(extras)})"
        return base

    def resolve_task_file(self, task_file: str, current_tasks_dir: Path | None) -> Path | None:
        name = task_file
        candidates: list[Path] = []
        if current_tasks_dir is not None:
            candidates.extend(
                [
                    current_tasks_dir / name,
                    current_tasks_dir / f"{name}.yml",
                    current_tasks_dir / f"{name}.yaml",
                ]
            )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def expand_role(
        self,
        role_name: str,
        tasks_from: str | None,
        path_prefix: str,
        when: str = "",
    ) -> None:
        short = self.normalize_role(role_name)
        tasks_path = self.role_tasks_path(role_name, tasks_from)

        label = f"role `{short}`"
        if tasks_from:
            label += f" (`{tasks_from}`)"
        self.add_row(path_prefix, label, "Enter role task list", when)

        if tasks_path is None:
            self.add_row(
                f"{path_prefix} → {short}",
                "missing role tasks",
                f"Could not locate tasks file for role `{short}`",
                when,
            )
            return

        self.expand_tasks_file(
            tasks_path,
            f"{path_prefix} → {short}",
            inherited_when=when,
        )

    def expand_tasks_file(
        self,
        tasks_path: Path,
        path_prefix: str,
        inherited_when: str = "",
    ) -> None:
        rel = tasks_path.relative_to(self.collections_root)
        stack_key = (tasks_path.parent.parent.name, tasks_path.name)
        if stack_key in self._stack:
            self.add_row(path_prefix, tasks_path.name, "Skipped — recursive cycle detected", inherited_when)
            return

        self.add_row(path_prefix, f"file `{tasks_path.name}`", f"Task file `{rel}`", inherited_when)
        self._stack.append(stack_key)
        try:
            for task in self.load_yaml_list(tasks_path):
                if isinstance(task, dict):
                    self.expand_task(task, path_prefix, inherited_when, tasks_path.parent)
        finally:
            self._stack.pop()

    def expand_task(
        self,
        task: dict[str, Any],
        path_prefix: str,
        inherited_when: str = "",
        current_tasks_dir: Path | None = None,
    ) -> None:
        when = self.format_when(task.get("when"))
        if inherited_when and when:
            when = f"{inherited_when}; {when}"
        elif inherited_when:
            when = inherited_when

        if "block" in task:
            block_name = task.get("name") or "block"
            self.add_row(path_prefix, block_name, "Begin conditional or grouped task block", when)
            for sub in task.get("block", []):
                if isinstance(sub, dict):
                    self.expand_task(sub, f"{path_prefix} → {block_name}", when, current_tasks_dir)
            for section in ("rescue", "always"):
                subs = task.get(section)
                if subs:
                    self.add_row(path_prefix, f"{block_name} ({section})", f"Run {section} tasks for block", when)
                    for sub in subs:
                        if isinstance(sub, dict):
                            self.expand_task(
                                sub,
                                f"{path_prefix} → {block_name} ({section})",
                                when,
                                current_tasks_dir,
                            )
            return

        module = self.module_name(task)
        task_name = task.get("name") or module
        summary = self.task_summary(task)

        if module in {"include_role", "import_role", "ansible.builtin.include_role", "ansible.builtin.import_role"}:
            payload = task.get(module, {})
            if isinstance(payload, str):
                role_name = payload
                tasks_from = None
            else:
                role_name = payload.get("name", "")
                tasks_from = payload.get("tasks_from")
            self.add_row(path_prefix, str(task_name), summary, when)
            if "{{" in str(role_name):
                self.add_row(
                    f"{path_prefix} → dynamic role",
                    str(role_name),
                    "Dynamic role name — expansion skipped; see dispatcher variable definitions in the collection",
                    when,
                )
                return
            self.expand_role(role_name, tasks_from, f"{path_prefix} → {self.normalize_role(role_name)}", when)
            return

        if module in {"include_tasks", "import_tasks", "ansible.builtin.include_tasks", "ansible.builtin.import_tasks"}:
            payload = task.get(module, "")
            task_file = payload if isinstance(payload, str) else str(payload)
            self.add_row(path_prefix, str(task_name), summary, when)
            candidate = self.resolve_task_file(task_file, current_tasks_dir)
            if candidate is not None:
                self.expand_tasks_file(candidate, f"{path_prefix} → {task_file}", when)
            else:
                self.add_row(
                    f"{path_prefix} → {task_file}",
                    task_file,
                    f"Include task file `{task_file}` (relative to current role task directory)",
                    when,
                )
            return

        if module == "include":
            payload = task.get("include")
            if isinstance(payload, str) and payload.endswith((".yml", ".yaml")):
                self.add_row(path_prefix, str(task_name), summary, when)
                return
            if isinstance(payload, dict) and payload.get("file"):
                self.add_row(path_prefix, str(task_name), summary, when)
                return

        self.add_row(path_prefix, str(task_name), summary, when)

    def expand_playbook(self, playbook_path: Path) -> None:
        plays = self.load_yaml_list(playbook_path)
        for play in plays:
            if not isinstance(play, dict):
                continue
            play_name = play.get("name") or "unnamed play"
            hosts = play.get("hosts", "")
            play_path = f"install.yml → {play_name}"
            self.add_row(
                "install.yml",
                play_name,
                f"Play targeting `{hosts}`",
            )

            for section in ("pre_tasks", "tasks", "post_tasks"):
                for task in play.get(section, []) or []:
                    if isinstance(task, dict):
                        self.expand_task(task, play_path, current_tasks_dir=None)

            for role in play.get("roles", []) or []:
                if isinstance(role, str):
                    self.expand_role(role, None, play_path)
                elif isinstance(role, dict):
                    role_name = role.get("role") or role.get("name", "unknown")
                    tasks_from = role.get("tasks_from")
                    self.expand_role(role_name, tasks_from, play_path)


def strip_md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def progress_pct(order: int, total: int) -> str:
    """Linear install progress: first task 0%, last task 100%."""
    if total <= 1:
        return "100%"
    pct = (order - 1) / (total - 1) * 100
    return f"{pct:.1f}%"


def render_markdown(
    title: str,
    playbook_cmd: str,
    installer_dump: str,
    playbook_rel: str,
    rows: list[TaskRow],
) -> str:
    lines = [
        f"# {title}",
        "",
        "Task execution order for the AAP install playbook, expanded recursively through "
        "included roles and task files. Conditional tasks include a `When` column; "
        "tasks inside blocks inherit the block condition. **Progress** runs from 0% "
        "(first row) to 100% (last row) based on position in the expanded task list.",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Playbook command | `{playbook_cmd}` |",
        f"| Source playbook | `{playbook_rel}` |",
        f"| Installer dump | `{installer_dump}` |",
        f"| Total tasks (expanded) | {len(rows)} |",
        "",
        "## Task table",
        "",
        "<!-- prettier-ignore-start -->",
        "<!-- Do not format this table — editors pad columns to the widest cell. Regenerate instead. -->",
        "| # | Progress | Location | Task | Description | When |",
        "|---:|---:|---|---|---|---|",
    ]
    total = len(rows)
    for row in rows:
        lines.append(
            "| {order} | {progress} | {path} | {name} | {desc} | {when} |".format(
                order=row.order,
                progress=progress_pct(row.order, total),
                path=strip_md_cell(row.path),
                name=strip_md_cell(row.name),
                desc=strip_md_cell(row.description),
                when=strip_md_cell(row.when) or "—",
            )
        )
    lines.extend(
        [
            "<!-- prettier-ignore-end -->",
            "",
        ]
    )
    lines.append(
        "## Notes\n\n"
        "- **Location** shows the play and role/task-file breadcrumb path from `install.yml`.\n"
        "- The same role or task file may appear multiple times when invoked from different plays or blocks.\n"
        "- Recursive cycles (A includes B includes A) are detected and marked as skipped.\n"
        "- Handler tasks (`notify`) are not executed inline; they run when notified and flushed.\n"
        "- **Progress** runs from 0% (first row) to 100% (last row).\n"
        "- **Do not Format Document** on this file — Markdown table formatters pad every column "
        "to the widest cell (~400+ char lines). Regenerate with "
        "`python3 installer/scripts/extract_install_playbook_tasks.py` instead.\n"
        "- Inventories in this folder are co-located with this reference — `@`-mention `installer/AAP{XY}/{method}/` for both.\n"
        "- OpenShift operator examples are in the sibling [`openshift/`](../../../openshift/) folder (no install playbook).\n"
    )
    return "\n".join(lines)


VERSIONS = [
    {
        "version": "2.4",
        "method": "rpm",
        "out": "AAP24/rpm/install-playbook-tasks.md",
        "dump": ".installer-dumps/2.4/ansible-automation-platform-setup-2.4-16",
        "collection": "automation_platform_installer",
        "playbook_cmd": "./setup.sh -i inventory",
        "playbook_rel": "collections/ansible_collections/ansible/automation_platform_installer/playbooks/install.yml",
    },
    {
        "version": "2.5",
        "method": "rpm",
        "out": "AAP25/rpm/install-playbook-tasks.md",
        "dump": ".installer-dumps/2.5/ansible-automation-platform-setup-2.5-23",
        "collection": "automation_platform_installer",
        "playbook_cmd": "./setup.sh -i inventory",
        "playbook_rel": "collections/ansible_collections/ansible/automation_platform_installer/playbooks/install.yml",
    },
    {
        "version": "2.5",
        "method": "containerized",
        "out": "AAP25/containerized/install-playbook-tasks.md",
        "dump": ".installer-dumps/2.5/ansible-automation-platform-containerized-setup-2.5-25",
        "collection": "containerized_installer",
        "playbook_cmd": "ansible-playbook -i inventory ansible.containerized_installer.install",
        "playbook_rel": "collections/ansible_collections/ansible/containerized_installer/playbooks/install.yml",
    },
    {
        "version": "2.6",
        "method": "rpm",
        "out": "AAP26/rpm/install-playbook-tasks.md",
        "dump": ".installer-dumps/2.6/ansible-automation-platform-setup-2.6-7",
        "collection": "automation_platform_installer",
        "playbook_cmd": "./setup.sh -i inventory",
        "playbook_rel": "collections/ansible_collections/ansible/automation_platform_installer/playbooks/install.yml",
    },
    {
        "version": "2.6",
        "method": "containerized",
        "out": "AAP26/containerized/install-playbook-tasks.md",
        "dump": ".installer-dumps/2.6/ansible-automation-platform-containerized-setup-2.6-10",
        "collection": "containerized_installer",
        "playbook_cmd": "ansible-playbook -i inventory ansible.containerized_installer.install",
        "playbook_rel": "collections/ansible_collections/ansible/containerized_installer/playbooks/install.yml",
    },
    {
        "version": "2.7",
        "method": "containerized",
        "out": "AAP27/containerized/install-playbook-tasks.md",
        "dump": ".installer-dumps/2.7/ansible-automation-platform-containerized-setup-2.7-2",
        "collection": "containerized_installer",
        "playbook_cmd": "ansible-playbook -i inventory ansible.containerized_installer.install",
        "playbook_rel": "collections/ansible_collections/ansible/containerized_installer/playbooks/install.yml",
    },
]


def generate_one(installer_root: Path, repo_root: Path, cfg: dict[str, str]) -> tuple[Path, int]:
    dump = repo_root / cfg["dump"]
    playbook = dump / cfg["playbook_rel"]
    collections_root = dump / "collections/ansible_collections"
    primary_roles_dir = (
        dump / "collections/ansible_collections/ansible" / cfg["collection"] / "roles"
    )
    extractor = Extractor(
        collections_root=collections_root,
        primary_roles_dir=primary_roles_dir,
        collection_name=cfg["collection"],
    )
    extractor.expand_playbook(playbook)

    title = f"AAP {cfg['version']} — {cfg['method'].title()} Install Playbook Tasks"
    md = render_markdown(
        title=title,
        playbook_cmd=cfg["playbook_cmd"],
        installer_dump=cfg["dump"],
        playbook_rel=cfg["playbook_rel"],
        rows=extractor.rows,
    )
    out_path = installer_root / cfg["out"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    return out_path, len(extractor.rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="AAP version to generate (e.g. 2.6)")
    parser.add_argument("--method", choices=["rpm", "containerized"], help="Deployment method")
    args = parser.parse_args()

    installer_root = Path(__file__).resolve().parents[1]
    repo_root = installer_root.parent
    selected = VERSIONS
    if args.version:
        selected = [v for v in VERSIONS if v["version"] == args.version]
        if args.method:
            selected = [v for v in selected if v["method"] == args.method]

    for cfg in selected:
        out_path, count = generate_one(installer_root, repo_root, cfg)
        print(f"Wrote {out_path} ({count} rows)")


if __name__ == "__main__":
    main()
