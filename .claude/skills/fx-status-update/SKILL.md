---
name: fx-status-update
description: Gather FX infrastructure status from GitHub (merged PRs, open PR activity, review comments, code diffs) and update IMPLEMENTATION_STATUS.md and PROGRESS.md with timestamped findings, then commit.
---

# FX Status Update

Update the FX infrastructure tracking documents with the latest state from GitHub.

$ARGUMENTS

## Step 1: Read current state

Read both `IMPLEMENTATION_STATUS.md` and `PROGRESS.md` in this directory. Note:
- The "Last updated" timestamps (to know what's new since then)
- Which PRs are in the merged table vs open/unmerged table
- Current gap statuses and percentage progress
- The "Next Actions by Person" section

## Step 2: Gather updates from GitHub

Use `gh` against `GaloyMoney/lana-bank` for all queries. Run these in parallel where possible:

### 2a. New merges to main

```bash
gh pr list -R GaloyMoney/lana-bank --state merged --base main --limit 50 --json number,title,author,mergedAt,url
```

Filter for FX-relevant PRs merged since the last update timestamp. FX-relevant means: touching `core/fx`, `core/price`, `lib/money`, deposit/withdrawal currency handling, exchange rate types, ledger templates, or any PR already tracked in the status documents.

### 2b. State of every tracked open/draft PR

For each PR currently in the "Unmerged branches & open PRs" table, fetch its current state:

```bash
gh pr view <NUMBER> -R GaloyMoney/lana-bank --json state,title,updatedAt,commits,reviews,comments,labels,isDraft
```

Check for: state changes (merged/closed), new commits since last update, new reviews or comments, label changes.

### 2c. Search for new untracked FX-relevant PRs

```bash
gh pr list -R GaloyMoney/lana-bank --state open --limit 100 --json number,title,author,createdAt,isDraft,url
```

Scan for PRs not already tracked that touch FX infrastructure (look for keywords: fx, exchange rate, currency, price, deposit currency, withdrawal currency, revaluation, collateral, trading account).

### 2d. Deep-dive review comments on actively reviewed PRs

For PRs marked as "review in progress" or with recent review activity:

```bash
gh api repos/GaloyMoney/lana-bank/pulls/<NUMBER>/comments --paginate
gh api repos/GaloyMoney/lana-bank/pulls/<NUMBER>/reviews --paginate
```

Extract design decisions, unresolved questions, and requested changes. Summarize key review themes.

## Step 3: Verify claims against code

PR metadata (titles, descriptions, review comments) can be inaccurate or incomplete. Use actual diffs to verify what PRs really contain before updating the status documents.

### 3a. Triage with diffstat

For every PR that will cause a status document change (newly merged, state changed, or referenced in a gap update), fetch the diffstat first:

```bash
gh pr diff <NUMBER> -R GaloyMoney/lana-bank --stat
```

Identify which files/modules were actually touched. Flag discrepancies where the PR description claims changes in modules that the diff doesn't touch.

### 3b. Targeted diff reads for FX-relevant files

From the diffstat, fetch full diffs only for files in FX-relevant paths (`core/fx/`, `core/price/`, `lib/money/`, `core/deposit/src/ledger/templates/`, deposit/withdrawal currency handling). Use the GitHub API to read specific file diffs:

```bash
gh pr diff <NUMBER> -R GaloyMoney/lana-bank | head -5000
```

For very large PRs (1000+ lines), focus on the files identified in the diffstat rather than reading the entire diff. Look for:
- Template entry counts (do they match what the gap sections claim?)
- New types, traits, or functions (do they match what the description says was added?)
- Deleted or renamed items (descriptions often omit removals)

### 3c. Spot-check gap claims

For each gap section that will be updated, verify its claims against the code:
- "Addressed in #XXXX" — confirm the diff actually contains the claimed change
- "X-entry template" — count the actual entry legs in the template code
- "Integration tests added" — confirm test files exist in the diff
- Status symbol changes (⬜→🔵, 🔶→✅) — verify the code supports the claimed status

If a discrepancy is found between metadata and actual code, use the code as the source of truth for the status update.

## Step 4: Fetch real timestamps

- Current time: use `date -u +"%Y-%m-%dT%H:%MZ"` for the "Last updated" field
- PR dates: use `mergedAt`, `updatedAt`, `createdAt` from GitHub API responses — never estimate or fabricate dates
- For merge dates in tables, use the date portion only (YYYY-MM-DD) from `mergedAt`

## Step 5: Update IMPLEMENTATION_STATUS.md

Update these sections with findings:

1. **"Current state of main" table** — add any newly merged FX-relevant PRs with: PR number, author, merge date, one-line description of what it delivered (based on the actual diff, not just the PR title)
2. **"Unmerged branches & open PRs" table** — update status/relevance for each tracked PR; add newly discovered PRs; move merged PRs out (they go to the merged table); move closed PRs to the "Closed PRs" table
3. **Gap sections (Gap 1–6)** — update "Progress since last update" with any new PR activity, review feedback, or design decisions. Update "What still needs to happen" if items were resolved. Base claims on verified diffs from Step 3, not just PR descriptions
4. **"Dependency chain"** — update the parallelizable/blocked lists and PR chain status
5. **"Actionable steps"** — update checkmarks and remaining items based on new merges/progress
6. **"Closed PRs" table** — add any PRs closed since last update with reason
7. **"Last updated" timestamp** — update to current UTC time from Step 4
8. **"Branch-specific shortcomings" table** — update status column if any shortcomings were addressed

## Step 6: Update PROGRESS.md

Update these sections with findings:

1. **Stage percentage bars** — recalculate based on item-level statuses. Use the formula: `completed_items / total_items` as a sanity check, then round to nearest 5%. The bar width is 30 characters; fill proportionally with `█` and `░`
2. **Per-stage item tables** — update status symbols (✅ 🟢 🔵 🔶 ⬜) and owner columns based on new activity
3. **Dependency graph (ASCII art)** — update percentage labels if they changed
4. **Critical path** — update the pipeline diagram with current bottleneck
5. **Infrastructure PRs table** — add/update infrastructure-adjacent PRs
6. **"Next Actions by Person"** — update with current priorities based on what's changed. Strike through completed items. Add new action items from review feedback or newly discovered work
7. **"Last updated" timestamp** — update to current UTC time from Step 4

## Step 7: Verify consistency

Before committing, check:
- No PR appears in both the merged and open/unmerged tables
- Percentage bars match item-level statuses (count ✅ items vs total)
- All timestamps are real values from GitHub or `date -u`, not estimates
- Gap progress sections reference real PR numbers and dates
- The dependency graph percentages match the stage sections
- Claims about PR contents match what was verified in Step 3

## Step 8: Commit

Stage and commit the updated files in this repository (the FX infrastructure tracking repo, not lana-bank):

```bash
git add IMPLEMENTATION_STATUS.md PROGRESS.md

git commit -m "$(cat <<'EOF'
docs: update status — <concise summary of key changes>

- <bullet: what merged>
- <bullet: status changes>
- <bullet: review progress>
- <bullet: other notable changes>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

The commit subject should summarize the 1–2 most important changes (e.g., "#4957 approved, #4986 closed"). The body bullets should cover: new merges, PR state changes, review progress, percentage changes.
