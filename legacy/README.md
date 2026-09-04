# Legacy Polaris

`legacy/v0_1/` preserves the pre-greenfield Polaris platform as historical donor/reference material.

It is **not** part of the current Polaris runtime or architecture.

## Rules

- Current code, tests, configuration, migrations, and tools must not import, wrap, extend, execute through, or depend on `legacy/`.
- Legacy dependencies do not belong in the current root project merely because v0.1 used them.
- Legacy schemas and migrations do not define the current database model.
- Legacy ADRs, architecture documents, wiki pages, tests, and workflows are historical evidence, not current authority.
- Salvage means deliberately copying or transplanting a useful implementation into a boundary already justified by current requirements and architecture.
- Deleting or declining to reuse donor material after learning from it is a successful greenfield outcome.

The pristine pre-greenfield implementation is anchored by Git tag `legacy-v0.1-baseline`.
