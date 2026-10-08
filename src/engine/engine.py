import pandas as pd
from src.tools import business_tools as bt
from src.tools.registry import ToolRegistry
from src.engine.rules import parse_rules, parse_steps, parse_tools

# Business operations registered by workflow id. The engine itself contains no
# workflow-specific logic: steps, decision rules and required tools are read from
# workflows.xlsx on every run (see src/engine/rules.py).
HANDLERS = {
    'WF001': bt.inventory_restock, 'WF002': bt.price_validation, 'WF003': bt.vendor_validation,
    'WF004': bt.description_generator, 'WF005': bt.order_status, 'WF006': bt.duplicate_products,
    'WF007': bt.campaign_brief, 'WF008': bt.keyword_classification, 'WF009': bt.task_assignment,
    'WF010': bt.performance_report,
}


def _summarize(result):
    if isinstance(result, pd.DataFrame):
        text = f'{len(result)} record(s) returned'
        if 'Exception' in result.columns:
            text += f"; {int(result['Exception'].sum())} flagged as exceptions"
        removed = result.attrs.get('duplicates_removed')
        if removed is not None:
            text += f'; {removed} duplicate keyword(s) removed'
        return text
    if isinstance(result, dict):
        status = result.get('status', 'success')
        if status in ('needs_input', 'escalate'):
            return f"{status}: {result.get('message', '')}"
        if 'validation_summary' in result:
            s = result['validation_summary']
            return f"{s['valid_rows']} valid / {s['invalid_rows']} invalid of {s['total_rows']} rows"
        if 'problem_areas' in result:
            return f"{len(result['problem_areas'])} problem area(s) flagged"
        return 'completed'
    return 'completed'


class WorkflowEngine:
    def __init__(self, registry=None):
        self.registry = registry
        self.tools = ToolRegistry()
        for wid, fn in HANDLERS.items():
            self.tools.register(wid, fn)

    def register_workflow(self, workflow_id, fn):
        """Register the business operation for a new workflow row added to the Excel."""
        self.tools.register(workflow_id, fn)

    def _run_handler(self, handler, wid, ctx):
        rules = ctx.rules
        if wid == 'WF001':
            threshold = ctx.parameters.get('minimum_stock_threshold')
            return handler(ctx.data, threshold, rules=rules)
        if wid == 'WF005':
            return handler(ctx.data, ctx.parameters.get('order_id') or ctx.parameters.get('customer_email'), rules=rules)
        if wid in ('WF007', 'WF009'):
            return handler(ctx.data, ctx.request, rules=rules)
        return handler(ctx.data, rules=rules)

    def execute(self, context):
        wf = context.workflow
        wid = wf['Workflow_ID']
        context.rules = parse_rules(wf.get('Decision_Logic', ''))
        context.log('Validate uploaded business data', details=f'Workflow {wid}')
        if not context.data:
            raise ValueError('No business data was uploaded.')
        context.log('Load required data', details=', '.join(context.data.keys()))

        required = parse_tools(wf.get('Tools_Required', ''))
        missing = self.tools.missing_capabilities(required)
        if missing:
            msg = f'{wid} needs tool(s) that are not registered: {missing}'
            context.errors.append(msg)
            context.log('Check required tools', 'error', msg)
            raise ValueError(msg)
        context.log('Check required tools (from Excel)', details='; '.join(required))

        handler = self.tools.tools.get(wid)
        if not handler:
            raise ValueError(f'No executable tool is registered for {wid}')
        try:
            result = self._run_handler(handler, wid, context)
            context.log('Execute workflow tools', details=f'{wid} tool executed')
            for i, step in enumerate(parse_steps(wf.get('Steps', '')), 1):
                context.log(f'Step {i}: {step}', details='defined in workflows.xlsx')
            rule_text = str(wf.get('Decision_Logic', ''))[:300]
            thresholds = f' | Thresholds read from Excel: {context.rules}' if context.rules else ''
            context.log('Apply decision conditions', details=f'Rule: {rule_text}{thresholds} | Outcome: {_summarize(result)}')
            context.log('Generate final result', details=str(wf.get('Expected_Output', ''))[:300])
            return result
        except Exception as exc:
            context.errors.append(str(exc))
            context.log('Workflow execution failed', 'error', str(exc))
            raise
