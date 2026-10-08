# AI Agent Workflow Automation

A reusable, Excel-driven AI agent that reads business workflow definitions, understands a user's request, selects the correct workflow, executes registered tools, evaluates workflow conditions, handles missing/invalid data, and returns a transparent execution trace and final result.

## Assignment alignment

The project is designed around the assignment requirement that the **Excel file is the workflow source** and that the application is **not ten separate hard-coded chatbots**.

The architecture is:

```text
Workflow Excel
      |
      v
Workflow Parser / Registry
      |
      +------------------------------+
      |                              |
User Request + Uploaded Data --> LLM Workflow Selector
                                     |
                                     v
                             Validated Workflow ID
                                     |
                                     v
                              Generic Executor
                                     |
                              Tool Registry
                                     |
                       +-------------+-------------+
                       |             |             |
                   File/Data     Calculator     LLM/API tools
                       |             |             |
                       +-------------+-------------+
                                     |
                                     v
                           Conditions / Validation
                                     |
                                     v
                         Execution Trace + Result
```

### Why this is scalable

- `data/workflows.xlsx` is the workflow registry and source of truth.
- The selector can choose only workflows present in that registry.
- The generic execution engine owns the lifecycle: validation, loading, tool execution, conditions, error capture, and result generation.
- Business operations are registered as tools rather than separate chatbots.
- Adding an 11th workflow requires adding its definition to the Excel registry and registering the new business operation/tool if the workflow introduces a capability not already available. No new chatbot or routing tree is required.
- With `OPENAI_API_KEY`, an LLM performs workflow selection. Without a key, a deterministic registry-backed fallback keeps the project runnable for local evaluation.

## What is in the Excel

`data/workflows.xlsx` contains:

- `Workflows` — Workflow ID, name, trigger, inputs, steps, decision logic, required tools, and expected output.
- `Test_Questions` — example user requests used for evaluation.

The application reads these definitions at startup; workflow descriptions are not duplicated in the UI.

## Supported workflows

| ID | Workflow | Typical input | Main decisions/tools |
|---|---|---|---|
| WF001 | Inventory Restock Check | Inventory CSV/XLSX + threshold | `current_stock < minimum_stock` |
| WF002 | Product Price Validation | Product + vendor prices | SKU match; exception when difference > 10% |
| WF003 | Vendor File Processing | Vendor CSV/XLSX | required-field validation; clean vs invalid rows |
| WF004 | Product Description Generator | Product attributes | missing-information handling; content generation |
| WF005 | Customer Order Status | Order ID/email + order data | identifier lookup; not-found handling |
| WF006 | Duplicate Product Detection | Product catalog | exact SKU vs similarity confidence |
| WF007 | Marketing Campaign Brief | Goal, audience, promotion, dates | missing required inputs |
| WF008 | SEO Keyword Classification | Keyword data + product/category | intent classification and mapping |
| WF009 | Employee Task Assignment | Task + employee skills/workload | skill match + capacity |
| WF010 | Workflow Performance Report | Execution logs | failure rate / performance analysis |

## Client experience

The client does **not** select WF001–WF010.

They upload a CSV/XLS/XLSX file and optionally enter a natural-language request:

```text
Upload input data: inventory.csv
Request: Which products need restocking?
```

The agent then:

1. Reads the file.
2. Inspects sheet names, columns, and available data.
3. Uses the workflow registry plus the request to select the best workflow.
4. Validates the selected workflow against the registry.
5. Executes its registered tools.
6. Applies conditions and error handling.
7. Displays the selected workflow, selection confidence/source, execution trace, and final result.

For workflows where the uploaded file alone is sufficient, the request can be left blank.

## Input formats

- CSV: treated as one dataset.
- XLSX/XLS: all sheets are loaded and made available to the workflow tools.

## LLM configuration

The preferred workflow-selection path uses an OpenAI-compatible LLM through the official Python SDK.

Copy `.env.example` to `.env` and set:

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4.1-mini
```

If no key is configured, the application uses a deterministic schema/filename/request fallback. This makes the repository runnable without external credentials while preserving an LLM-backed architecture when credentials are available.

## Setup — Windows / VS Code

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest
```

Start the application:

```powershell
$env:PYTHONPATH="."
streamlit run src/ui_app.py
```

Open the local Streamlit URL shown in the terminal.

## Example request

Upload `data/sample_daily_business_data.xlsx` and enter:

```text
Which products need restocking?
```

Expected display:

```text
Selected Workflow:
WF001 — Inventory Restock Check

Steps Executed:
✓ Validate uploaded business data
✓ Load required data
✓ Execute workflow tools
✓ Apply decision conditions
✓ Generate final result
```

## Error and condition handling

The executor records errors in the execution context and displays failed steps. Workflow tools return structured `needs_input` results for cases such as:

- missing campaign dates;
- missing order identifier;
- order not found;
- missing required business-data columns.

The system does not silently fabricate missing business values.

## Tests

The test suite covers:

- workflow Excel parsing;
- CSV/XLSX loading;
- automatic workflow routing;
- all ten end-to-end workflows;
- threshold changes;
- order lookup;
- vendor validation;
- price exceptions;
- missing campaign dates.

Run:

```powershell
python -m pytest -q
```


