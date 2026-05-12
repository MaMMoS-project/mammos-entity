# Agent Instructions for mammos-entity

This file is only for AI coding agents. Human-facing package guidance belongs in
`CONTRIBUTING.md`; shared MaMMoS standards belong in
`CONTRIBUTING-MaMMoS.md`.

Read `CONTRIBUTING.md` and `CONTRIBUTING-MaMMoS.md` before editing.

This repository must work as a standalone checkout. Do not assume
`mammos-devtools` or sibling repositories are present. Use this repository's
`pyproject.toml`, pixi tasks, tests, examples, and docs as the local source of
truth.

If this checkout is located at `mammos-devtools/packages/mammos-entity`, also
read `../../AGENTS.md` for umbrella-repository guidance.

Keep generated code and documentation simple, explicit, and easy for a human
maintainer to understand.

When new information is needed, put it in the document for its audience. Use
README files, examples, or normal docs for user-facing information. Use this
package's `CONTRIBUTING.md` for mammos-entity developer guidance and
`CONTRIBUTING-MaMMoS.md` for shared MaMMoS developer guidance. Use `AGENTS.md`
only for AI-specific operating instructions.

Be careful with generated or bundled ontology files under
`src/mammos_entity/ontology`. Update them only when the task explicitly requires
an ontology refresh.
