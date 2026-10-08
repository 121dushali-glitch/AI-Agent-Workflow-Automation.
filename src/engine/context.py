from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ExecutionContext:
    request: str
    workflow: dict
    data: dict
    parameters: dict = field(default_factory=dict)
    rules: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def log(self, step, status='success', details=''):
        self.trace.append({'step': step, 'status': status, 'details': details, 'timestamp': datetime.now().isoformat(timespec='seconds')})
