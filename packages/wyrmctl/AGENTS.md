# wyrmctl package agent guidance

- Keep client, schema, planner, apply, and CLI concerns separated.
- Planner must be side-effect free.
- Apply must execute only a clean validated plan.
- Capability detection must fail closed.
- Add happy and unhappy pytest coverage for every behavior.
