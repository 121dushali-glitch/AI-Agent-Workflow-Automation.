class WorkflowRegistry:
    def __init__(self, definitions):
        self.definitions = definitions

    def all(self):
        return self.definitions

    def get(self, workflow_id):
        return next((w for w in self.definitions if w['Workflow_ID'] == workflow_id), None)
