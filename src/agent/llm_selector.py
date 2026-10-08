"""LLM-backed workflow selection with an actual tool call and safe fallback.

The model can only call ``select_workflow`` with an ID that exists in the
Excel-backed registry. Python validates the tool-call result before execution.
"""
import json
import os


def _schema(data, filename):
    result = {"filename": filename, "datasets": []}
    for name, df in data.items():
        result["datasets"].append({
            "name": name,
            "rows": int(len(df)),
            "columns": [str(c) for c in df.columns],
        })
    return result


def build_selection_prompt(request, workflows, data, filename):
    catalog = []
    for w in workflows:
        catalog.append({
            "id": w["Workflow_ID"],
            "name": w["Workflow_Name"],
            "trigger": w["Trigger"],
            "inputs": w["Inputs"],
            "steps": w["Steps"],
            "decisions": w["Decision_Logic"],
            "tools": w["Tools_Required"],
            "output": w["Expected_Output"],
        })
    return (
        "You are the workflow-selection agent for a business automation system. "
        "Choose exactly one workflow by calling the select_workflow tool. "
        "Use the user's request, uploaded-file schema, sheet names, triggers, inputs and decision logic. "
        "Never invent a workflow. If evidence is insufficient, do not call the tool.\n\n"
        f"USER REQUEST:\n{request or '(no explicit request; infer from uploaded data)'}\n\n"
        f"UPLOADED DATA:\n{json.dumps(_schema(data, filename), default=str)}\n\n"
        f"WORKFLOW REGISTRY:\n{json.dumps(catalog, ensure_ascii=False)}"
    )


def _tool_definition(workflows):
    ids = [w["Workflow_ID"] for w in workflows]
    names = {w["Workflow_ID"]: w["Workflow_Name"] for w in workflows}
    return {
        "type": "function",
        "function": {
            "name": "select_workflow",
            "description": "Select one workflow from the supplied Excel workflow registry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "enum": ids},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                },
                "required": ["workflow_id", "confidence", "reason"],
                "additionalProperties": False,
            },
        },
    }


def select_with_llm(request, workflows, data, filename):
    """Return (workflow_id, confidence, reason, used_llm), or None.

    Requires OPENAI_API_KEY and the openai package. Without them, callers use
    the registry-backed deterministic fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            tools=[_tool_definition(workflows)],
            tool_choice={"type": "function", "function": {"name": "select_workflow"}},
            messages=[
                {"role": "system", "content": "You are a precise workflow-routing agent. Use the provided tool; do not invent workflow IDs."},
                {"role": "user", "content": build_selection_prompt(request, workflows, data, filename)},
            ],
        )
        calls = response.choices[0].message.tool_calls or []
        if not calls:
            return None
        call = calls[0]
        if call.function.name != "select_workflow":
            return None
        payload = json.loads(call.function.arguments)
        ids = {w["Workflow_ID"] for w in workflows}
        wid = payload.get("workflow_id")
        if wid not in ids:
            return None
        confidence = float(payload.get("confidence", 0))
        return wid, max(0.0, min(1.0, confidence)), str(payload.get("reason", "LLM tool selected workflow")), True
    except Exception:
        return None
