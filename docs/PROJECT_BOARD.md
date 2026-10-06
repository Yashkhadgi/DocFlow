# DocFlow V1: GitHub Project Board Setup Guide

This guide walks through setting up and organizing the GitHub Project Board (Projects v2) to coordinate work across **Lead**, **Person A (Backend)**, **Person B (AI/Data)**, and **Person C (Frontend)** during the DocFlow V1 build.

---

## 1. Prerequisites

1. **GitHub CLI Authenticated**:
   Make sure you are logged into the GitHub CLI on your workstation:
   ```bash
   gh auth login
   ```
2. **Issues Created**:
   Run the issue creation script from the repository root:
   ```bash
   # Preview all 37 issues and labels
   ./scripts/create_issues.sh --dry-run

   # Create all labels and issues in the repository
   ./scripts/create_issues.sh
   ```

---

## 2. Creating the Project Board

### Via GitHub Web UI
1. Navigate to your repository or organization on GitHub:
   - For repository: `https://github.com/<owner>/<repo>/projects`
   - For user/org profile: `https://github.com/users/<owner>/projects`
2. Click **New project** (green button).
3. Select the **Board** template.
4. Set the project title to:
   ```text
   DocFlow V1 Sprint
   ```
5. Click **Create**.

---

## 3. Configuring Status Columns

GitHub Projects defaults to a single `Status` field. Configure the 4 required columns:

1. Click on the column header dropdowns or go to **Settings (top right) -> Fields -> Status**.
2. Ensure the following 4 options exist in this order:
   - **`To do`** (Color: Gray) — Backlog of ready tasks.
   - **`In progress`** (Color: Blue) — Task currently in active development on a feature branch.
   - **`In review`** (Color: Purple) — Pull Request opened and waiting for review / CI checks.
   - **`Done`** (Color: Green) — Pull Request merged and task verified against its "Done when" checklist.
3. Delete or rename any unwanted default options (e.g. rename "Backlog" to "To do").

---

## 4. Adding All Issues to the Project

### Method A: Bulk Add via Project UI (Recommended)
1. In your project board, press the shortcut `+` or click **+ Add item** at the bottom of any column.
2. Type `#` followed by the repository name or issue number.
3. To bulk-import all repository issues:
   - Click the search/filter bar in the project or click the **...** menu next to the view tabs.
   - Click **Add items from repository**.
   - Select your repository (`DocFlow`).
   - Check all 37 created task issues.
   - Click **Add selected items**.
4. All issues will land in the **`To do`** column.

### Method B: Automated Repository Integration (Auto-Add Workflow)
1. In the project board, click **... (top right) -> Workflows**.
2. Click **Auto-add to project**.
3. Set the trigger to:
   - Repository: `DocFlow`
   - Event: `Issues`
   - Filter (optional): leave empty to add all repository issues automatically.
4. Turn on the workflow. Any new issue created in the repository will immediately appear on the board.

---

## 5. Recommended Views & Tabs

To help each engineer focus on their owned track, configure customized views:

### View 1: Main Kanban (Board View)
- **Layout**: Board
- **Group by**: `Status` (`To do` | `In progress` | `In review` | `Done`)
- **Sort**: Title or manual priority
- **Purpose**: High-level overview of the entire team's flow.

### View 2: Person A — Backend (Board or Table)
- **Layout**: Board
- **Filter**: `label:backend`
- **Purpose**: Person A tracks tasks `A1` through `A8`.

### View 3: Person B — AI & Data (Board or Table)
- **Layout**: Board
- **Filter**: `label:ai`
- **Purpose**: Person B tracks tasks `B1` through `B8`.

### View 4: Person C — Frontend (Board or Table)
- **Layout**: Board
- **Filter**: `label:frontend`
- **Purpose**: Person C tracks tasks `C1` through `C8`.

### View 5: Integration & Hardening (Table or Board)
- **Layout**: Board
- **Filter**: `label:integration,hardening`
- **Purpose**: Phase 2 (`I1..I3`) and Phase 3 (`H1..H4`) tracking.

---

## 6. Automations & GitHub Workflow Setup

Enable built-in Project workflows so the board updates automatically without manual drag-and-drop:

1. Click **... -> Workflows** in your Project.
2. Enable these built-in automations:
   - **Item closed**: Set `Status` to **`Done`** when an issue is closed.
   - **Pull request merged**: Set `Status` to **`Done`** when a linked pull request merges.
   - **Pull request opened**: Set `Status` to **`In review`** when a pull request targeting `main` is opened.
   - **Branch / Draft PR created**: Set `Status` to **`In progress`**.

---

## 7. Working Rules for the Team

1. **One Task = One Branch = One PR**:
   - Branch naming convention:
     - `feat/a1-skeleton`
     - `feat/b2-extract`
     - `feat/c4-review-ui`
2. **Link Issues in PRs**:
   - In your PR description, use GitHub closing keywords:
     ```text
     Closes #7
     ```
     This automatically links the PR to the issue and transitions it across board columns.
3. **Definition of Done**:
   - Move an issue to **`Done`** only after every checklist item in its "Done when" section passes and the PR is approved and merged into `main`.
4. **Cadence**:
   - Target small PRs merged at least every 40 minutes of work to keep parallel tracks unblocked.
