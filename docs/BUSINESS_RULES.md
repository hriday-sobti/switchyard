# SWITCHYARD: Business Rules Specification

## 1. Scope & Objective
This document formalizes the deterministic business rules governing SLA status classification, multi-factor exception prioritization, state transitions, and quarantine thresholds across the SWITCHYARD system.

---

## 2. Rule Definitions

### BRULE-001: SLA Classification & Target Calculation
- **Rule Name:** SLA Target Duration Assignment
- **Inputs:** `service_tier` (Tier 1, Tier 2, Tier 3), `customer_tier` (Enterprise, Commercial, Retail), `severity` (Critical, High, Medium, Low).
- **Logic:** Base SLA minutes are determined by service and customer tier matrix:
  - Enterprise Customer + Critical Severity $\rightarrow$ 60 minutes.
  - Enterprise Customer + High Severity $\rightarrow$ 120 minutes.
  - Commercial Customer + Critical Severity $\rightarrow$ 180 minutes.
  - Commercial / Retail Standard $\rightarrow$ 480 to 1440 minutes.
- **Output:** `target_sla_minutes` (integer > 0).

---

### BRULE-002: SLA Warning & Breach State Logic
- **Rule Name:** SLA State Engine
- **Inputs:** `start_time` (UTC), `current_time` (UTC), `target_sla_minutes`.
- **Formulas:**
  $$\text{elapsed\_minutes} = \max(0, \frac{\text{current\_time} - \text{start\_time}}{60})$$
  $$\text{remaining\_minutes} = \text{target\_sla\_minutes} - \text{elapsed\_minutes}$$
  $$\text{consumption\_ratio} = \frac{\text{elapsed\_minutes}}{\text{target\_sla\_minutes}}$$
- **State Evaluation:**
  1. If $\text{consumption\_ratio} \ge 1.0 \implies \mathbf{BREACHED}$
  2. Else if $\text{consumption\_ratio} \ge 0.80 \implies \mathbf{AT\_RISK}$
  3. Else $\implies \mathbf{ON\_TRACK}$
- **Edge Cases:** If `start_time` > `current_time` (clock skew defect), flag data-quality violation. If target minutes $\le 0$, reject as invalid SLA configuration.

---

### BRULE-003: Multi-Factor Priority Scoring Engine
- **Rule Name:** Explainable Priority Score Calculation
- **Objective:** Map heterogeneous operational dimensions into a normalized 0–100 scale.
- **Weights Configuration:**
  - $w_{SLA} = 0.35$ (SLA Urgency)
  - $w_{Cust} = 0.25$ (Customer Impact & Tier)
  - $w_{Fin} = 0.20$ (Financial Exposure)
  - $w_{Age} = 0.10$ (Case Waiting Age)
  - $w_{Crit} = 0.10$ (Operational Severity)
  - $\sum w = 1.00$

- **Normalized Dimension Scores ($0.0 \le S_i \le 100.0$):**
  1. **SLA Score ($S_{SLA}$):**
     - If $\text{Breached} \implies 100.0$
     - If $\text{consumption\_ratio} \ge 0.80 \implies 80.0 + (\text{consumption\_ratio} - 0.80) \times 100.0$
     - Else $\implies \text{consumption\_ratio} \times 70.0$
  2. **Customer Tier Score ($S_{Cust}$):**
     - Enterprise $\implies 100.0$
     - Commercial $\implies 60.0$
     - Retail $\implies 30.0$
  3. **Financial Impact Score ($S_{Fin}$):**
     - Logarithmic scaling: $\min(100.0, \frac{\log_{10}(\max(1, \text{exposure\_usd}))}{5.0} \times 100.0)$ (e.g., \$100k exposure $\rightarrow$ 100.0).
  4. **Aging Score ($S_{Age}$):**
     - Linear cap at 24 hours: $\min(100.0, \frac{\text{unassigned\_hours}}{24.0} \times 100.0)$.
  5. **Criticality Score ($S_{Crit}$):**
     - Critical $\implies 100.0$, High $\implies 75.0$, Medium $\implies 40.0$, Low $\implies 10.0$.

- **Priority Band Thresholds:**
  - $\text{Score} \ge 85.0 \implies \mathbf{P1}$ (Critical Triage)
  - $70.0 \le \text{Score} < 85.0 \implies \mathbf{P2}$ (High Priority)
  - $45.0 \le \text{Score} < 70.0 \implies \mathbf{P3}$ (Standard Operational)
  - $\text{Score} < 45.0 \implies \mathbf{P4}$ (Low / Maintenance)

- **Driver Generation Logic:**
  - If $S_{SLA} \ge 80.0 \rightarrow$ `"SLA breach imminent or already breached"`
  - If $S_{Cust} == 100.0 \rightarrow$ `"Tier 1 Enterprise customer account"`
  - If exposure $\ge \$25,000 \rightarrow$ `"Significant financial exposure (\$X)"`
  - If unassigned hours $\ge 6 \rightarrow$ `"Case aging exceeds triage SLA threshold"`

---

### BRULE-004: Exception Lifecycle State Transitions
- **Allowed States:** `DETECTED`, `TRIAGED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`.
- **Valid Transition Matrix:**
  - `DETECTED` $\rightarrow$ `TRIAGED`, `CLOSED` (false positive)
  - `TRIAGED` $\rightarrow$ `ASSIGNED`
  - `ASSIGNED` $\rightarrow$ `IN_PROGRESS`, `TRIAGED` (re-routed)
  - `IN_PROGRESS` $\rightarrow$ `RESOLVED`, `ASSIGNED` (re-assigned)
  - `RESOLVED` $\rightarrow$ `CLOSED`, `IN_PROGRESS` (reopened defect)
- **Illegal Transitions:** Jumping from `DETECTED` directly to `RESOLVED`, or mutating any field once `CLOSED`.
