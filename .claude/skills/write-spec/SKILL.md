---
name: write-spec
description: Write or revise a feature spec (specs/<feature>/spec.md) with verifiable, ID-tagged acceptance criteria. Use when the user asks for a spec, requirements or acceptance criteria for a feature of this project.
argument-hint: "<feature-slug> [short description]"
---

# Write a spec

Feature: $ARGUMENTS

## Steps

1. Read `specs/_template.md` and any existing spec in `specs/` to reuse
   the style and to avoid ID collisions (`grep -rn "AC-" specs/`).
2. Pick a short uppercase prefix for the feature (`ADD` for
   add-expense) and create `specs/<feature-slug>/spec.md` from the
   template with `status: draft`.
3. Write the acceptance criteria. Each one must pass this checklist:
   - **Observable**: says what the MCP client or caller sees (return
     value, error message, stored state as seen through another tool),
     never how it is implemented.
   - **One behaviour**: one "then". Split otherwise.
   - **Concrete**: uses example values (`amount "12.50"`), not "a valid
     amount".
   - **Covers failure**: invalid input and edge cases get their own
     criteria, with the exact error the client gets.
   - **Testable offline**: no real LLM, network or clock; say which
     fake or fixed date the criterion assumes.
4. Fill in "Out of scope" with anything a reader might assume but we
   will not build. Keep the spec under ~80 lines.
5. List unresolved questions under "Open questions" and ask the user
   about them. Do not invent answers to business questions.
6. Run `.venv/bin/python scripts/check_specs.py`; it must pass.
7. Show the user the criteria and stop. Commit only after approval,
   with the message `spec(<feature-slug>): <summary>`.

## Do not

- Do not write plan, tasks or code in this skill.
- Do not renumber existing criterion IDs; append new ones.
