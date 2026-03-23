Analyze the most recent changes to this project and update the docs/ folder to reflect them.

## Steps

1. Run `git log --oneline -10` to see recent commits
2. Run `git diff HEAD~1 HEAD --name-only` to identify which files changed
   - If $ARGUMENTS is provided (e.g. a commit hash or filename), use that instead
3. For each changed file, map it to affected docs:

   | Changed file | Docs to update |
   |---|---|
   | `src/dcf_calculator.py` | `docs/dcf_methodology.md` |
   | `src/alpaca_client.py` | `docs/beta_and_capm.md`, `docs/data_sources.md` |
   | `src/xbrl_parser.py` | `docs/data_sources.md` |
   | `src/email_reporter.py` | `docs/pipeline_architecture.md` |
   | `src/sec_client.py` | `docs/data_sources.md`, `docs/pipeline_architecture.md` |
   | `main.py` | `docs/pipeline_architecture.md` |
   | `config.py` | `docs/design_decisions.md`, `docs/pipeline_architecture.md` |
   | Any new `src/*.py` | `docs/pipeline_architecture.md` (file map section) |
   | Any new `tests/*.py` | `docs/pipeline_architecture.md` (testing strategy section) |
   | New financial formula | `docs/glossary.md` |
   | New design choice | `docs/design_decisions.md` |

4. Read the affected docs/ files
5. Read the changed source files (or run `git diff HEAD~1 HEAD -- <file>`) to understand what changed
6. Update each affected docs file:
   - Add new methods/classes with explanation of what they do and why
   - Remove or correct outdated descriptions
   - Update the file map table if files were added or removed
   - Add new glossary entries for any new financial or technical terms
   - Add new design decision entries for any non-obvious choices made
7. Report a summary: which docs files were updated and what changed in each

## Rules
- Only update what actually changed — do not rewrite docs that are still accurate
- Preserve the existing writing style (plain English, "why" explanations, code snippets)
- Keep the same section structure unless a new section is genuinely needed
- If a change introduces a new financial formula or method, always include: the formula, why this method was chosen over alternatives, and a code reference
