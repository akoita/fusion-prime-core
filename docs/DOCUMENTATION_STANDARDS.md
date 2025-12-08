# 📚 Fusion Prime - Documentation Governance

**Purpose**: Maintain concise, organized, and consistent documentation across the project.

**Golden Rule**: Before creating new documentation, check if existing docs can be updated instead.

---

## 🎯 Documentation Philosophy

### Principles

1. **DRY (Don't Repeat Yourself)**: One source of truth per topic
2. **Merge over Multiply**: Consolidate related docs rather than creating new ones
3. **User-Centric**: Organize by user needs, not internal structure
4. **Maintainable**: Fewer files = easier to keep updated
5. **Discoverable**: Clear naming and cross-references

### Anti-Patterns to Avoid

❌ **Don't create**:
- Multiple quick start guides
- Separate "philosophy" documents (merge philosophy into practice)
- Per-environment duplicate docs (use universal docs with environment variables)
- README files that duplicate existing documentation

✅ **Do create**:
- Comprehensive guides that serve multiple purposes
- Clear cross-references between related docs
- Inline examples and quick references

---

## 📁 Documentation Structure

### Root-Level Documentation (User-Facing)

| File | Purpose | When to Update |
|------|---------|----------------|
| **README.md** | Project overview, quick navigation | When adding major features |
| **QUICKSTART.md** | Local development guide (30-min) | When setup process changes |
| **TESTING.md** | Universal testing guide | When test process changes |
| **ENVIRONMENTS.md** | Three-tier architecture explained | When adding new environments |
| **DEPLOYMENT_STATUS.md** | Current deployment state | After each deployment |
| **FUNCTIONAL_TESTS.md** | Detailed test specifications | When adding new tests |

### `docs/` Directory (Technical Details)

```
docs/
├── README.md                          # Navigation hub for docs/
├── specification.md                   # Product specification (single source of truth)
├── architecture/
│   └── risk-analytics-pipeline.md     # Specific architecture patterns
├── integrations/
│   └── escrow-to-backend.md           # Integration flows
├── sprints/
│   ├── README.md                      # Sprint planning overview
│   ├── sprint-01.md                   # Historical sprint records
│   ├── sprint-02.md
│   └── ...
└── standards/
    └── coding-guidelines.md           # Code style and patterns
```

**Rules for `docs/`**:
- Technical deep dives and design decisions
- Sprint planning and retrospectives
- Architecture decision records (ADRs)
- Integration specifications
- NOT for user-facing guides (those go in root)

---

## 🔄 When to Create vs Update vs Merge

### Create New Document When:

✅ **Introducing a new major subsystem**
   - Example: `docs/architecture/cross-chain-bridge.md`
   - Must be distinct from existing architecture

✅ **Starting a new sprint**
   - Example: `docs/sprints/sprint-06.md`
   - Follow sprint template

✅ **Documenting a new integration**
   - Example: `docs/integrations/kyc-provider.md`
   - Specific external system integration

### Update Existing Document When:

✅ **Adding features to existing subsystems**
   - Update `QUICKSTART.md` with new setup steps
   - Update `TESTING.md` with new test types
   - Update `ENVIRONMENTS.md` with new environment variables

✅ **Fixing bugs or clarifying**
   - Fix incorrect commands
   - Add troubleshooting sections
   - Improve examples

✅ **Documenting enhancements**
   - Add new workflows to `QUICKSTART.md`
   - Add new test patterns to `TESTING.md`

### Merge Documents When:

✅ **Overlap exceeds 30%**
   - Example: `TESTING.md` + `TESTING_PHILOSOPHY.md` → merged
   - Example: `QUICKSTART.md` + `LOCAL_DEVELOPMENT.md` → merged

✅ **Serving the same user need**
   - If users don't know which doc to read, merge them
   - If docs reference each other frequently, consider merging

✅ **Duplicate information**
   - Remove redundancy
   - Consolidate into single source of truth

---

## 📝 Documentation Checklist

### Before Creating New Documentation

- [ ] Does this information already exist elsewhere?
- [ ] Can I update an existing document instead?
- [ ] Will this serve a distinct user need?
- [ ] Can I merge this with a related document?
- [ ] Have I checked all existing docs?

### When Updating Documentation

- [ ] Is this information consistent with other docs?
- [ ] Have I updated cross-references?
- [ ] Have I checked for duplicate information?
- [ ] Is the change reflected in all relevant places?
- [ ] Have I updated the last modified date?

### When Merging Documentation

- [ ] Have I preserved all useful information?
- [ ] Is the new structure more user-friendly?
- [ ] Have I updated all cross-references?
- [ ] Have I removed the old files from git?
- [ ] Have I updated navigation (README, TOC)?

---

## 🗂️ Document Ownership

### Root-Level Documents

| Document | Owner | Review Frequency |
|----------|-------|------------------|
| README.md | Product | When features change |
| QUICKSTART.md | DevOps | When setup changes |
| TESTING.md | QA/DevOps | When test process changes |
| ENVIRONMENTS.md | DevOps | When infrastructure changes |
| DEPLOYMENT_STATUS.md | DevOps | After each deployment |

### `docs/` Directory

| Subdirectory | Owner | Review Frequency |
|--------------|-------|------------------|
| architecture/ | Architect | When architecture changes |
| integrations/ | Integration Team | When adding/updating integrations |
| sprints/ | Product | Each sprint (2 weeks) |
| standards/ | All Teams | Quarterly |

---

## 🔍 Documentation Audit Process

### Monthly Review

1. **Check for staleness**:
   ```bash
   # Find docs not updated in 90 days
   find . -name "*.md" -type f -mtime +90
   ```

2. **Review for accuracy**:
   - Test all commands in guides
   - Verify all links work
   - Check screenshots are current

3. **Look for duplication**:
   - Search for repeated content
   - Consider merging candidates
   - Update cross-references

### Quarterly Cleanup

1. **Archive completed sprints**:
   - Keep last 3 sprints in main `sprints/`
   - Move older to `sprints/archive/`

2. **Update architecture docs**:
   - Reflect current state
   - Remove deprecated patterns
   - Add new patterns

3. **Review root-level docs**:
   - Ensure consistency
   - Update examples
   - Refresh quickstart with latest practices

---

## 📊 Current Documentation Inventory

### Root Level (6 files)
- ✅ README.md
- ✅ QUICKSTART.md (comprehensive local dev guide)
- ✅ TESTING.md (universal testing guide)
- ✅ ENVIRONMENTS.md (three-tier architecture)
- ✅ DEPLOYMENT_STATUS.md (current state)
- ✅ FUNCTIONAL_TESTS.md (test specifications)

### `docs/` Directory (11 files)
- ✅ docs/README.md (navigation)
- ✅ docs/specification.md (product spec)
- ✅ docs/architecture/risk-analytics-pipeline.md
- ✅ docs/integrations/escrow-to-backend.md
- ✅ docs/standards/coding-guidelines.md
- ✅ docs/sprints/README.md
- ✅ docs/sprints/sprint-01.md through sprint-05.md (5 files)

**Total: 17 documentation files** ← Keep this lean!

---

## 🎓 Best Practices

### Writing Style

**DO**:
- Use clear, concise language
- Include examples for every concept
- Provide both quick start and deep dive
- Use consistent formatting (headers, code blocks, lists)
- Cross-reference related docs

**DON'T**:
- Use jargon without explanation
- Create walls of text (use headings, lists, tables)
- Duplicate information from other docs
- Write without testing the commands
- Create docs that become stale quickly

### Naming Conventions

**Root-level files**:
- `UPPERCASE.md` for important user-facing docs
- Clear, single-word names when possible
- Example: `QUICKSTART.md`, `TESTING.md`, `ENVIRONMENTS.md`

**`docs/` subdirectories**:
- `lowercase-with-hyphens.md`
- Descriptive names
- Example: `risk-analytics-pipeline.md`, `escrow-to-backend.md`

### Cross-Referencing

Always use relative links:
```markdown
See [QUICKSTART.md](./QUICKSTART.md) for setup instructions.
See [Testing Guide](./TESTING.md) for test procedures.
See [Architecture](./docs/architecture/risk-analytics-pipeline.md) for details.
```

---

## 🚀 Quick Actions

### I want to add documentation about...

**Local development**:
→ Update `QUICKSTART.md`

**Testing procedures**:
→ Update `TESTING.md`

**Environment configuration**:
→ Update `ENVIRONMENTS.md`

**A new architecture pattern**:
→ Create `docs/architecture/[pattern-name].md`

**A new integration**:
→ Create `docs/integrations/[system-name].md`

**Sprint planning**:
→ Create `docs/sprints/sprint-XX.md`

**Code standards**:
→ Update `docs/standards/coding-guidelines.md`

**Deployment info**:
→ Update `DEPLOYMENT_STATUS.md`

---

## 📋 Documentation Templates

### New Architecture Document

```markdown
# [Pattern Name]

**Purpose**: One-line description

**Owner**: Team name

**Last Updated**: YYYY-MM-DD

---

## Problem Statement

[What problem does this solve?]

## Solution Overview

[High-level approach]

## Architecture

[Diagrams, flows, components]

## Implementation

[Key details]

## Related Documentation

- [Link to related docs]
```

### New Integration Document

```markdown
# [System] Integration

**Purpose**: Integration with [external system]

**Status**: [Draft|Active|Deprecated]

**Last Updated**: YYYY-MM-DD

---

## Overview

[What does this integration do?]

## Architecture

[Data flow, components]

## Configuration

[Environment variables, setup]

## API Reference

[Endpoints, examples]

## Testing

[How to test locally]
```

---

## 🔧 Maintenance Commands

### Find Stale Docs

```bash
# Docs not modified in 3 months
find docs -name "*.md" -type f -mtime +90 -ls

# All markdown files with modification dates
find . -name "*.md" -type f -exec ls -lh {} \; | sort -k6,7
```

### Check for Broken Links

```bash
# Find all markdown links
grep -r "\[.*\](.*)" *.md docs/**/*.md

# Verify they exist
# (manual process or use markdown-link-check tool)
```

### Audit Documentation Size

```bash
# Count total lines
find . -name "*.md" -type f -exec wc -l {} + | sort -n

# Total size
du -sh docs/
```

---

## 📐 Deployment Documentation Standards

### Document Hierarchy for Deployments

```
Main Orchestration (DEPLOYMENT.md or DEPLOYMENT_STATUS.md)
    ↓ references
Component Implementation (contracts/DEPLOYMENT.md, services/*/README.md)
    ↓ references
Advanced Topics (infra/terraform/modules/*/README.md)
```

### Separation of Concerns

| Document Type | Purpose | Contains | Does NOT Contain |
|---------------|---------|----------|------------------|
| **Main Guide** | Orchestration, overview | High-level steps, prerequisites, success criteria | Detailed commands, full code |
| **Component Guide** | Implementation details | Full commands, examples, troubleshooting | Orchestration, environment setup |
| **Reference Docs** | Deep technical details | Configuration options, advanced patterns | Basic setup |

### Deployment Guide Template

Each deployment guide should have:

1. **Overview**: Purpose, use case, cost, time estimates
2. **Prerequisites**: What must be done first
3. **High-Level Steps**: Checklist format
4. **Each Step**:
   ```markdown
   ### Step N: [Name]

   **Time**: X minutes
   **Cost**: $X (if applicable)
   **Prerequisites**: [List]

   **What Gets Deployed**:
   - Component 1
   - Component 2

   **Quick Commands**:
   ```bash
   # Brief example
   ```

   **Verification**:
   ```bash
   # How to verify success
   ```
   ```
5. **Troubleshooting**: Common issues and solutions
6. **Cross-References**: Links to component guides

### Cross-Reference Patterns

**From main guide to component**:
```markdown
See [Contract Deployment Guide](./contracts/DEPLOYMENT.md) for detailed instructions.
```

**From component to main guide**:
```markdown
This is step 2 of the [Main Deployment Flow](../DEPLOYMENT.md#step-2-deploy-contracts).
```

**Between components**:
```markdown
Depends on: [Database Setup](../services/settlement/README.md#database-setup)
```

---

## 📌 Remember This!

**Save this in your LLM context**:

```
DOCUMENTATION RULES:
1. Before creating, check if exists
2. Update over create
3. Merge when overlap > 30%
4. Root-level = user-facing (UPPERCASE.md)
5. docs/ = technical deep-dives (lowercase-hyphen.md)
6. Max ~20 total files (currently 17)
7. Review monthly, audit quarterly
8. Test all commands before committing
9. One source of truth per topic
10. Cross-reference, don't duplicate
```

---

## 🎯 Success Metrics

**Good documentation is**:
- ✅ Easy to find (clear structure)
- ✅ Easy to read (concise, clear)
- ✅ Easy to maintain (no duplication)
- ✅ Always accurate (regularly tested)
- ✅ User-focused (solves real problems)

**Track**:
- Total file count (goal: < 25)
- Average file size (goal: 500-1000 lines)
- Update frequency (goal: monthly for main docs)
- Duplication rate (goal: < 5%)

---

**This document itself should be reviewed quarterly and updated as documentation practices evolve.**

Last Updated: 2025-10-19

---

## 🧹 Sprint Completion Documentation Cleanup

**Added**: 2025-11-20

### Rule: Consolidate Temporary Docs After Sprint

When completing a sprint, **consolidate temporary working documents** into permanent documentation:

#### Temporary Docs to Consolidate
- Agent task tracking (`task.md`, `implementation_plan.md`)
- Sprint walkthroughs (`walkthrough.md`)
- Cleanup summaries
- Status reports

#### Consolidation Process

1. **Merge into permanent docs**:
   - Walkthrough content → Sprint summary (e.g., `SPRINT_10_COMPLETION_SUMMARY.md`)
   - Implementation details → Component READMEs (e.g., `contracts/cross-chain/README.md`)
   - Cleanup actions → Archive with date

2. **Delete temporary files**:
   ```bash
   # Remove agent artifacts
   rm -rf .gemini/antigravity/brain/*/task.md
   rm -rf .gemini/antigravity/brain/*/implementation_plan.md
   rm -rf .gemini/antigravity/brain/*/walkthrough.md

   # Archive cleanup summaries
   mv *_CLEANUP*.md docs/archive/cleanup/$(date +%Y-%m)/
   ```

3. **Update documentation index**:
   - Ensure `DOCUMENTATION_INDEX.md` reflects current state
   - Remove references to deleted temporary docs

#### What to Keep vs Delete

**Keep (merge into permanent docs)**:
- ✅ Deployment procedures → Component README
- ✅ Feature descriptions → Sprint summary
- ✅ Architecture decisions → Architecture docs
- ✅ Testing results → Sprint summary

**Delete (after merging)**:
- ❌ Agent task tracking files
- ❌ Temporary walkthrough files
- ❌ Duplicate cleanup summaries
- ❌ Work-in-progress planning docs

#### Example: Sprint 10 Cleanup

```bash
# 1. Merge walkthrough into sprint summary
# (Manual: copy relevant sections from walkthrough.md to SPRINT_10_COMPLETION_SUMMARY.md)

# 2. Delete temporary docs
rm DOCUMENTATION_CLEANUP.md
rm DOCUMENTATION_CLEANUP_PLAN.md

# 3. Keep only essential docs
# - SPRINT_10_COMPLETION_SUMMARY.md (permanent)
# - contracts/cross-chain/README.md (permanent)
# - DOCUMENTATION_INDEX.md (permanent)
```

### Benefits

- ✅ Reduces doc count (goal: <50 files)
- ✅ Prevents documentation sprawl
- ✅ Maintains single source of truth
- ✅ Easier to navigate and maintain

---

**Last Updated**: 2025-11-20
