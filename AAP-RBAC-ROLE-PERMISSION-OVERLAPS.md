# AAP RBAC — Role & Permission Overlaps

Advanced diagrams showing **where managed roles share permissions**, **where one role’s permissions are a subset of another’s**, and **where the same role name merges permission sets across services**.

**Prerequisites:** [AAP-RBAC-MANAGED-ROLES-CATALOG.md](./AAP-RBAC-MANAGED-ROLES-CATALOG.md) (exact permission lists)

**Related:** [AAP-RBAC-ROLE-HIERARCHY.md](./AAP-RBAC-ROLE-HIERARCHY.md) · [AAP-RBAC-GUIDE.md](./AAP-RBAC-GUIDE.md)

---

## How to read these diagrams

AAP RBAC overlap is **not** role inheritance (assigning Org Admin does not auto-assign Team Admin). Overlap appears in three different ways:

| Overlap type | Meaning | Example |
|--------------|---------|---------|
| **Shared permission** | Same permission slug appears in multiple roles | `shared.member_team` in Team Member, Team Admin, and Organization Admin |
| **Permission subset** | Role A’s permissions are entirely contained in Role B’s (same or wider scope) | Team Member ⊆ Team Admin on a team |
| **Union / merge** | Same role **name** combines permission sets from multiple services | Organization Admin = Gateway `shared.*` + Controller `awx.*` + EDA `eda.*` |
| **View overlap** | Many roles include `view_*` on the same resource | `awx.view_jobtemplate` in Execute, Admin, Org Execute, Org Audit, Platform Auditor |

**Line styles in diagrams:**

- **Solid arrow** → role **includes** that permission
- **Dashed arrow** → role A’s permission set is a **subset of** role B (when scopes align)
- **Thick hub node** → permission shared by **3+** roles

---

## Diagram 1 — Gateway shared permissions (bipartite map)

Roles on the left, permissions on the right. Follow lines to see **who shares what**.

```mermaid
flowchart LR
    subgraph ROLES["Gateway roles"]
        direction TB
        PA[Platform Auditor]
        OA[Organization Admin]
        OM[Organization Member]
        TA[Team Admin]
        TM[Team Member]
    end

    subgraph PERMS["shared.* permissions"]
        direction TB
        P_VO["view_organization"]
        P_VT["view_team"]
        P_MO["member_organization"]
        P_MT["member_team"]
        P_CO["change_organization"]
        P_DO["delete_organization"]
        P_AT["add_team"]
        P_CT["change_team"]
        P_DT["delete_team"]
    end

    PA --> P_VO
    PA --> P_VT

    OM --> P_MO
    OM --> P_VO

    TM --> P_MT
    TM --> P_VT

    TA --> P_MT
    TA --> P_VT
    TA --> P_CT
    TA --> P_DT

    OA --> P_VO
    OA --> P_VT
    OA --> P_MO
    OA --> P_MT
    OA --> P_CO
    OA --> P_DO
    OA --> P_AT
    OA --> P_CT
    OA --> P_DT

    style P_MT fill:#f0ab00,stroke:#c79200,color:#000
    style P_VT fill:#06c,stroke:#004080,color:#fff
    style OM fill:#666,stroke:#444,color:#fff
```

**Highlights:**

- **`shared.member_team`** (gold) — shared by Team Member, Team Admin, Organization Admin; **not** in Organization Member alone for team ops at org scope the same way (Org Admin has it on all teams in org).
- **`shared.view_team`** (blue) — widest view overlap: Platform Auditor sees all teams; org/team roles see within assignment scope.
- **Organization Member** — only touches `member_organization` + `view_organization`; **no overlap** with operational team permissions.

---

## Diagram 2 — Gateway role subset relationships

When assigned on **compatible objects**, permission sets nest like this:

```mermaid
flowchart TB
    PA[Platform Auditor<br/>all view_* globally]

    OA[Organization Admin<br/>all shared.* + all service perms in org]

    TA[Team Admin<br/>on one team]
    TM[Team Member<br/>on one team]

    PA -.->|view_* superset of org/team views<br/>at system scope| OA
    OA -.->|shared team perms apply to<br/>ALL teams in org| TA
    TM -.->|permission subset| TA

    OM[Organization Member<br/>membership only]

    OM -.-x|no operational overlap| TA

    style OM fill:#666,stroke:#444,color:#fff
    style TM fill:#2d2d2d,stroke:#8a8,color:#fff
    style TA fill:#2d2d1f,stroke:#f0ab00,color:#fff
    style OA fill:#1f3d2d,stroke:#3e8635,color:#fff
    style PA fill:#1f2d3d,stroke:#06c,color:#fff
```

**Team Member ⊆ Team Admin** (same team object):

| Permission | Team Member | Team Admin |
|------------|:-----------:|:----------:|
| `shared.view_team` | ✓ | ✓ |
| `shared.member_team` | ✓ | ✓ |
| `shared.change_team` | | ✓ |
| `shared.delete_team` | | ✓ |

**Organization Admin ⊃ Team Admin** for shared team permissions — but on **different assignment scope** (org vs team). Org Admin’s team permissions apply to **every team in the org**, not one team.

---

## Diagram 3 — Organization Admin: merged permission unions

Same role **name**, three permission sources in unified Platform:

```mermaid
flowchart TB
    R["Organization Admin<br/>(one role name, assigned on org)"]

    R --> G
    R --> C
    R --> E

    subgraph G["Gateway shared.*"]
        G1[add/change/delete/view org]
        G2[add/change/delete/view/member team]
        G3[member_organization]
    end

    subgraph C["Controller awx.*"]
        C1[All org-child CRUD + actions]
        C2[Organization Audit/Execute/Approval<br/>bundles are separate roles]
    end

    subgraph E["EDA eda.*"]
        E1[activation CRUD + enable/disable/restart]
        E2[project · credential · DE · event stream …]
        E3[team CRUD + member]
    end

    style R fill:#3e8635,stroke:#1e4d1e,color:#fff
```

**Overlap consequence:** A user with **Organization Admin** already has permissions that **overlap** with:

- **Team Admin** (shared team permissions, org-wide)
- **Organization {Resource} Admin** for every Controller/EDA resource type
- **Organization Execute**, **Organization Audit** (as subsets — Org Admin is strictly broader)

You rarely need Org Admin **plus** Organization Project Admin — the latter is a **subset** of Org Admin’s Controller portion.

---

## Diagram 4 — Controller: Job Template permission overlap

One resource type; many roles reuse the same permission slugs on **different scopes**.

```mermaid
flowchart TB
    subgraph PERMS["awx job template permissions"]
        V["awx.view_jobtemplate"]
        E["awx.execute_jobtemplate"]
        C["awx.change_jobtemplate"]
        D["awx.delete_jobtemplate"]
        A["awx.add_jobtemplate"]
    end

    subgraph OBJ["Object scope · one job template"]
        JTE[Job Template Execute]
        JTA[Job Template Admin]
    end

    subgraph ORG["Organization scope"]
        OJE[Organization Execute]
        OJA[Organization Job Template Admin]
        OAD[Organization Admin]
        OAU[Organization Audit]
    end

    subgraph SYS["System scope"]
        PAV[Platform Auditor]
    end

    JTE --> V
    JTE --> E

    JTA --> V
    JTA --> E
    JTA --> C
    JTA --> D

    OJE --> V
    OJE --> E

    OJA --> V
    OJA --> E
    OJA --> C
    OJA --> D
    OJA --> A

    OAD --> V
    OAD --> E
    OAD --> C
    OAD --> D
    OAD --> A

    OAU --> V

    PAV --> V

    JTE -.->|subset| JTA
    OJE -.->|execute subset| OJA
    OJA -.->|subset of Controller<br/>portion of| OAD
    OAU -.->|view only subset| JTA

    style V fill:#06c,stroke:#004080,color:#fff
    style E fill:#f0ab00,stroke:#c79200,color:#000
```

**Patterns that repeat** for Inventory, Project, Credential, Workflow, etc.:

| Pattern | Subset relationship |
|---------|---------------------|
| `{Resource} {Action}` ⊆ `{Resource} Admin` | Execute ⊆ Admin on same object |
| `Organization Execute` ⊆ `Organization Admin` | Runnable subset only |
| `Organization Audit` ⊆ `Organization Admin` | View subset only |
| `Organization {Resource} Admin` ⊆ `Organization Admin` | Single-type admin ⊆ full org admin |
| `Platform Auditor` | View permissions only; overlaps **view** portions of all roles above |

---

## Diagram 5 — Cross-service “view” overlap on organizations

Three services define **view organization** separately — roles can overlap without sharing the same slug:

```mermaid
flowchart LR
    subgraph SLUGS["Organization view permissions"]
        SV["shared.view_organization"]
        AV["awx.view_organization"]
        EV["eda.view_organization"]
    end

    subgraph ROLES["Roles that include org view"]
        OM[Organization Member]
        OA[Organization Admin]
        OJA[Organization Job Template Admin]
        OAU[Organization Audit]
        PA[Platform Auditor]
        OEV[Organization Editor · EDA]
    end

    OM --> SV
    OA --> SV
    OA --> AV
    OA --> EV
    OJA --> AV
    OAU --> AV
    OAU --> SV
    PA --> SV
    OEV --> EV

    style SV fill:#6a6,stroke:#444,color:#fff
    style AV fill:#3e8635,stroke:#1e4d1e,color:#fff
    style EV fill:#06c,stroke:#004080,color:#fff
```

**Takeaway:** “Can view the organization” may require **multiple slugs** depending on which UI/API you hit. Organization Member only has `shared.*`; Organization Admin accumulates all three services’ org-view permissions.

---

## Diagram 6 — Membership permissions vs operational permissions

Membership slugs overlap roles but **do not** grant the same capabilities:

```mermaid
flowchart TB
    subgraph MEMBERSHIP["Membership permissions · inheritance hooks"]
        MO["shared.member_organization"]
        MT["shared.member_team"]
        EM["eda.member_team"]
    end

    subgraph OPERATIONAL["Operational examples · NOT implied by membership alone"]
        OP1["shared.change_team"]
        OP2["awx.execute_jobtemplate"]
        OP3["eda.enable_activation"]
    end

    OM[Organization Member] --> MO
    TM[Team Member] --> MT
    OA[Organization Admin] --> MO
    OA --> MT
    OA --> OP1
    TA[Team Admin] --> MT
    TA --> OP1

    EOM[EDA Organization Member] --> EM

    OM -.-x OP1
    OM -.-x OP2
    TM -.-x OP2
    TM -.-x OP3

    style MO fill:#666,stroke:#444,color:#fff
    style MT fill:#666,stroke:#444,color:#fff
    style EM fill:#666,stroke:#444,color:#fff
```

**Organization Member** and **Team Member** share **membership-class** permissions with admin roles but **lack** operational permissions (dashed X = no overlap with ops).

---

## Diagram 7 — Hub: global role permission overlap

Several `galaxy.*` roles share namespace and collection permissions:

```mermaid
flowchart TB
    subgraph PERMS["High-traffic Hub permissions"]
        UN["galaxy.add/change/delete_namespace"]
        UP["galaxy.upload_to_namespace"]
        CR["ansible.modify_ansible_repo_content"]
        EE["container.namespace_push_*"]
    end

    CA[galaxy.content_admin]
    CCA[galaxy.collection_admin]
    CP[galaxy.collection_publisher]
    CC[galaxy.collection_curator]
    CNO[galaxy.collection_namespace_owner]
    EEA[galaxy.execution_environment_admin]

    CA --> UN
    CA --> UP
    CA --> CR
    CA --> EE

    CCA --> UN
    CCA --> UP
    CCA --> CR

    CP --> UN
    CP --> UP

    CC --> CR

    CNO --> UP

    EEA --> EE

    CP -.->|subset| CCA
    CCA -.->|subset| CA
    CC -.->|partial overlap| CCA

    style CA fill:#3e8635,stroke:#1e4d1e,color:#fff
```

**galaxy.content_admin** is the **superset** for collection/namespace/EE permissions among global Hub roles.

---

## Overlap matrix — Gateway shared permissions

Which roles include each permission? ✓ = included.

| Permission | Platform Auditor | Org Admin | Org Member | Team Admin | Team Member |
|------------|:----------------:|:---------:|:----------:|:----------:|:-----------:|
| `shared.view_organization` | ✓ | ✓ | ✓ | | |
| `shared.view_team` | ✓ | ✓ | | ✓ | ✓ |
| `shared.member_organization` | | ✓ | ✓ | | |
| `shared.member_team` | | ✓ | | ✓ | ✓ |
| `shared.change_organization` | | ✓ | | | |
| `shared.delete_organization` | | ✓ | | | |
| `shared.add_team` | | ✓ | | | |
| `shared.change_team` | | ✓ | | ✓ | |
| `shared.delete_team` | | ✓ | | ✓ | |

---

## Overlap matrix — Controller job template (sample)

| Permission | JT Execute | JT Admin | Org Execute | Org JT Admin | Org Admin | Org Audit | Platform Auditor |
|------------|:----------:|:--------:|:-----------:|:------------:|:---------:|:---------:|:----------------:|
| `view_jobtemplate` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `execute_jobtemplate` | ✓ | ✓ | ✓ | ✓ | ✓ | | |
| `change_jobtemplate` | | ✓ | | ✓ | ✓ | | |
| `delete_jobtemplate` | | ✓ | | ✓ | ✓ | | |
| `add_jobtemplate` | | | | ✓ | ✓ | | |

---

## Practical implications

### Avoid redundant assignments

| Already has | Usually redundant to also assign |
|-------------|----------------------------------|
| Organization Admin | Organization {Resource} Admin, Team Admin (for team mgmt in that org), Organization Execute/Audit |
| Job Template Admin | Job Template Execute (on same template) |
| Team Admin | Team Member (on same team — Admin is strict superset) |
| galaxy.content_admin | galaxy.collection_admin, galaxy.collection_publisher |

### Overlap does not mean inheritance

Two users both needing `awx.execute_jobtemplate` on **different** job templates need **separate** assignments (or a team/org role that covers both). Shared permission slugs do not automatically flow between objects.

### Organization Member is an overlap outlier

It shares **`member_organization`** with Organization Admin but **nothing operational** — always show it separately in overlap analysis (see Diagram 6).

---

## Source & maintenance

Derived from [AAP-RBAC-MANAGED-ROLES-CATALOG.md](./AAP-RBAC-MANAGED-ROLES-CATALOG.md). Re-validate after AAP upgrades:

```http
GET /api/gateway/v1/role_definitions/?managed=true
```

Compare `permissions` arrays on roles that should nest as subsets.
