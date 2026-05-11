# Configuration Optimization Tool (COT) - Outline

## Table of Contents

1. [Purpose](#1-purpose)
2. [High-Level Concept](#2-high-level-concept)
3. [Role in the MAGICIAN Ecosystem](#3-role-in-the-magician-ecosystem)
4. [Inputs](#4-inputs)
5. [Outputs](#5-outputs)
6. [Scope & Phasing](#6-scope--phasing)
7. [User & Functional Requirements](#7-user--functional-requirements)
8. [Risks & Design Principles](#8-risks--design-principles)

---

## 1. Purpose

The Configuration Optimization Tool (COT) is a core enabling component of the MAGICIAN system designed to support partners and end users in configuring MAGICIAN modules for new use cases.

### What COT Is

- A **decision-support and orchestration layer** between use-case descriptions and MAGICIAN technical modules
- A tool to **reduce configuration effort and errors**
- A system that makes **implicit assumptions explicit**
- A mechanism to **improve consistency** across deployments
- A provider of **guidance and traceability** when adapting to new tasks, objects, materials, sensors, or environments

### What COT Is Not

- **Not a replacement** for human expertise
- **Not autonomous** reconfiguration without human validation
- **Not a guarantee** of performance under all conditions

---

## 2. High-Level Concept

### 2.1 Questionnaire-Based Configuration

Interactive configuration interface where users specify:

| Category | Examples |
|----------|----------|
| Robot Setup | Number of arms, coordination requirements |
| Sensors & Perception | Camera types, tactile sensing, lighting |
| Object & Material | Properties, surface characteristics, 3D mesh availability |
| Task Requirements | Defect types, precision, time constraints |
| Environment | Operational constraints, compute resources |

### 2.2 Output: Module Change Recommendations

Based on inputs, COT produces structured output indicating:

- **Which modules** are affected
- **What characteristics/parameters** need changes
- **Whether new data, calibration, or retraining** is required
- **Where human judgment** is explicitly required

> **Note:** In Phase 1, output does not directly change system behavior—it provides an inspectable recommendation layer.

### 2.3 Partner-Provided Module Knowledge Base

Built upon structured input from MAGICIAN partners:

- Module inputs and outputs
- Internal processes and configurable components
- Dependencies on data, hardware, and sensing modalities
- Use-case characteristics influencing module behavior

This knowledge is **descriptive rather than prescriptive**: captures behavior and dependencies without constraining partner implementations.

---

## 3. Role in the MAGICIAN Ecosystem

The COT functions as a **coordination, guidance, and progressively assistive configuration layer**.

### Core Functions

| Function | Description |
|----------|-------------|
| **Collect & Structure** | Gather information about new/modified use cases |
| **Interpret** | Relate information to MAGICIAN's modular architecture |
| **Identify** | Highlight modules, components, and dependencies requiring adaptation |
| **Support** | Assist preparation and validation of configurations |
| **Enable** | Facilitate communication and traceability between partners |

### 3.1 Separation of Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEPARATION OF CONCERNS                       │
├─────────────────┬───────────────────────────────────────────────┤
│ Use-Case        │ • Object characteristics & geometries         │
│ Characterization│ • Material properties                         │
│                 │ • Process constraints & performance targets   │
│                 │ • Available data, meshes, training inputs     │
│                 │ • Environmental/operational conditions        │
├─────────────────┼───────────────────────────────────────────────┤
│ System & Module │ • Identify impacted MAGICIAN modules          │
│ Awareness       │ • Determine adaptation types required         │
│                 │ • Track dependencies and constraints          │
│                 │ • Generate structured guidance                │
├─────────────────┼───────────────────────────────────────────────┤
│ Human Decision  │ • Safety-critical configurations              │
│ & Oversight     │ • Performance/cost/reliability trade-offs     │
│                 │ • Ambiguous or insufficiently covered cases   │
│                 │ • Validation of automated proposals           │
└─────────────────┴───────────────────────────────────────────────┘
```

### 3.2 Progressive Configuration Support

**Evolution Path:**

1. **Early Stage** → Identify modules, highlight tasks, aggregate guidance
2. **Intermediate** → Partner-contributed configuration functions
3. **Advanced** → Parameter suggestions, preliminary validation, prerequisite checks

### 3.3 Alignment with Partner Goals

Addresses partner requirements from mural exercise:

- ✓ Transparency and explainability
- ✓ Human validation and override capabilities
- ✓ Managing inconsistent configuration risks
- ✓ Avoiding complexity for end users
- ✓ Supporting extensibility

---

## 4. Inputs

### 4.1 System & Hardware

| Input | Description |
|-------|-------------|
| Robot Arms | Number of arms |
| Coordination | Robot coordination requirements |
| Compute | Available CPU/GPU resources |
| Cameras | Type(s) and setup |
| Tactile/Force | Sensing availability |

### 4.2 Perception & Sensing

| Input | Description |
|-------|-------------|
| Lighting | Environmental lighting conditions |
| Image Quality | Blur, exposure constraints |
| Sensor Modalities | Required sensor types |
| Multi-Camera | Setup configurations |

### 4.3 Object & Material Properties

| Input | Description |
|-------|-------------|
| Material(s) | Object material types |
| Surface | Surface characteristics |
| 3D Mesh | Availability of object mesh |
| Variability | Expected instance variation |

### 4.4 Task & Performance Requirements

| Input | Description |
|-------|-------------|
| Defect Types | Types to detect |
| Accuracy/Runtime | Constraint balance |
| Safety | Safety relevance level |
| Explainability | Traceability requirements |

---

## 5. Outputs

### Configuration Summary Structure

```
COT Output
├── Affected Modules List
│
├── Per Module Details
│   ├── Relevant configuration characteristics
│   ├── Reasoning ("why this matters")
│   └── Required actions (retrain, adjust camera, etc.)
│
├── Confidence/Completeness Indication
│   └── Based on answered questions
│
└── Explicit Flags
    ├── Data quality concerns
    ├── Assumption validity warnings
    └── Human validation requirements
```

### Design Principles for Output

- **Transparency** — Clear reasoning visible
- **Visualization** — Understandable presentation
- **No black-box behavior** — Decisions traceable
- **Human override capability** — Always available

---

## 6. Scope & Phasing

### Phase 1 — Decision Support (Current Focus)

| Aspect | Implementation |
|--------|----------------|
| Interface | Questionnaire-driven |
| Logic | Rule- and logic-based mapping |
| Output | Descriptive configuration recommendations |
| Human Role | In-the-loop by design |

### Phase 2 — Assisted Configuration

| Aspect | Implementation |
|--------|----------------|
| Functions | Partner-provided configuration logic |
| Automation | Partial where feasible |
| Integration | Meshes, datasets, calibration assets |

### Phase 3 — Advanced Optimization (Future)

| Aspect | Implementation |
|--------|----------------|
| Optimization | Cross-module |
| Trade-offs | Runtime-performance reasoning |
| Learning | Data-driven refinement |
| Scaling | Multi-robot and multi-node |

### Explicit Non-Goals (Initial Phases)

- ❌ Fully autonomous reconfiguration without human validation
- ❌ Guaranteeing performance/accuracy under all conditions
- ❌ Solving factory-level constraints outside model assumptions
- ❌ Replacing expert judgment in ambiguous/safety-critical cases

---

## 7. User & Functional Requirements

### 7.1 User Requirements

#### Configuration & Control

- Module selection by users
- Override capability (human-in-the-loop)
- Role-based access & authorization
- Consistent interface across use cases

#### Guidance & Usability

- Step-by-step configuration guidance
- Progressive learning path (basic → advanced)
- Understandable reasoning (avoid opacity)
- Clear documentation

#### Visualization & Transparency

- Visualization tools with modular-level logging
- Data logging, reporting, statistics
- Decision traceability

#### Scalability & Flexibility

- Multiple cameras, robots, compute nodes
- Multiple OP solvers by problem type
- Supervisor/task planner configuration

### 7.2 Functional Requirements

#### Core Modules & Components

| Domain | Components |
|--------|------------|
| **Classification** | Vision classifier, Tactile classifier, Physical camera config |
| **Data Pipeline** | Dataset capture, annotation, training |
| **Runtime** | Model configuration, accuracy/latency trade-offs |
| **Motion & Control** | Orientation solver, DMP, Ergonomic controller |
| **Validation** | 3D mesh mapping, misclassification detection |

#### Implementation Priorities

**High Priority (First):**
- Dataset capture & annotation
- Classifier training & runtime configuration
- Camera & sensor configuration
- Core solvers (orientation, DMP)

**Human-Guided:**
- Risk vs performance trade-offs
- Edge cases with poor data coverage
- Physical reality deviations
- Strategic reconfiguration decisions

**Lower Priority (Later):**
- OS/version compatibility checks

---

## 8. Risks & Design Principles

### Risk Categories

#### Configuration & System Risks

| Risk | COT Response |
|------|--------------|
| Inconsistent configurations → safety risks | Emphasize traceability and visibility |
| Low sensing accuracy | Highlight configuration mismatches |
| Configuration vs physical setup visibility | Make assumptions explicit |

#### Data & Model Risks

| Risk | COT Response |
|------|--------------|
| Limited/poor-quality datasets | Highlight data gaps (don't hide them) |
| Under/overfitting | Flag training data concerns |
| Incorrect annotations | Surface annotation quality issues |
| Model size vs compute constraints | Show trade-off implications |

#### Performance & Scalability Risks

| Risk | COT Response |
|------|--------------|
| Accuracy vs speed conflicts | Present explicit trade-offs |
| Hardware incompatibilities | List hardware dependencies clearly |
| Factory constraints outside model | Acknowledge model limitations |

#### Software & Integration Risks

| Risk | COT Response |
|------|--------------|
| OS/driver/ROS/framework compatibility | Check and surface conflicts |
| Unstable ROS interfaces | Track interface versions |
| COT complexity overwhelming users | Prioritize explainability over automation |

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Transparency** | All reasoning visible and traceable |
| **Human-in-the-loop** | Override always available |
| **Explainability** | Prioritized over automation |
| **Consistency** | Structured knowledge base |
| **Progressiveness** | Gradual automation increase |

---

