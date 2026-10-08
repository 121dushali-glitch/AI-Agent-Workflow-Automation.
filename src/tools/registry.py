import re


def _key(name):
    return re.sub(r'\s+', ' ', str(name).strip().lower())


# Tool capabilities that can be named in the Tools_Required column of workflows.xlsx.
# Value = where the capability is implemented in this project.
DEFAULT_CAPABILITIES = {
    'csv reader': 'pandas / load_business_data',
    'excel/csv parser': 'pandas / load_business_data',
    'csv/database reader': 'pandas / load_business_data',
    'product data reader': 'pandas / load_business_data',
    'calculator': 'Python arithmetic in src/tools/business_tools.py',
    'data validation': 'required-field checks in business_tools.vendor_validation',
    'text validation': 'missing-attribute checks in business_tools.description_generator',
    'text similarity': 'difflib.SequenceMatcher in business_tools.duplicate_products',
    'ranking logic': 'skill / workload ranking in business_tools.task_assignment',
    'reporting': 'summary tables in business_tools.performance_report',
    'order database/api': 'order sheet lookup in business_tools.order_status',
    'shipment lookup': 'tracking columns in business_tools.order_status',
    'employee/task database': 'employee sheet in business_tools.task_assignment',
    'llm': 'rule-based generator (LLM can be plugged in)',
    'llm/classifier': 'rule-based keyword classifier (LLM can be plugged in)',
}


class ToolRegistry:
    def __init__(self):
        self.tools = {}                      # workflow id -> business operation
        self.capabilities = {_key(k): v for k, v in DEFAULT_CAPABILITIES.items()}

    def register(self, name, fn):
        self.tools[name] = fn

    def register_capability(self, name, implemented_by='custom'):
        self.capabilities[_key(name)] = implemented_by

    def missing_capabilities(self, required):
        return [t for t in required if _key(t) not in self.capabilities]

    def run(self, name, *args, **kwargs):
        if name not in self.tools:
            raise KeyError(f'Tool not registered: {name}')
        return self.tools[name](*args, **kwargs)
