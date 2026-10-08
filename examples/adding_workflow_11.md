# Adding an 11th workflow

The workflow selector and execution engine do not contain a ten-workflow `if/elif` routing tree.

To add a workflow that uses an existing tool capability:

1. Add one row to `data/workflows.xlsx` in the `Workflows` sheet.
2. Define its `Workflow_ID`, trigger, inputs, steps, decision logic, tools, and expected output.
3. Restart the application so the registry reloads the Excel file.

The LLM selector automatically receives the new registry entry and can select it.

If the new workflow requires a capability that does not exist yet, add one reusable function to `src/tools/` and register that tool in the generic `WorkflowEngine`. This is the only workflow-specific code required for a genuinely new capability; no new chatbot or routing tree is created.
