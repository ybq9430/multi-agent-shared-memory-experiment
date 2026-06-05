"""Role-specific agents: Planner, Executor, Reviewer."""

from prototype.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    """Plans tasks and writes task plans to working memory."""

    def __init__(self, store, agent_id: str = "planner_1", trust_score: float = 0.5):
        super().__init__(agent_id, "planner", store, trust_score)

    def create_plan(self, task_description: str) -> str:
        plan = f"[PLAN] {task_description} → Step1: analyze → Step2: execute → Step3: review"
        self.write_memory("task_plan", plan)
        return plan

    def update_status(self, status: str):
        self.write_memory("task_status", status)


class ExecutorAgent(BaseAgent):
    """Executes tasks based on plans in working memory."""

    def __init__(self, store, agent_id: str = "executor_1", trust_score: float = 0.5):
        super().__init__(agent_id, "executor", store, trust_score)

    def read_plan(self) -> str | None:
        entry = self.read_memory("task_plan")
        return entry.value if entry else None

    def execute(self, result: str):
        self.write_memory("task_status", f"[EXECUTED] {result}")
        self.write_memory("current_step", "execution_complete")


class ReviewerAgent(BaseAgent):
    """Reviews execution results and writes feedback. Serves as leader agent."""

    def __init__(self, store, agent_id: str = "reviewer_1", trust_score: float = 0.5):
        super().__init__(agent_id, "reviewer", store, trust_score)

    def review(self, feedback: str):
        self.write_memory("task_status", f"[REVIEWED] {feedback}")
        self.write_memory("current_step", "review_complete")

    def arbitrate(self, value_a: str, value_b: str, context: str = "") -> str:
        """Leader mediation: pick the more appropriate value based on context."""
        # Rule-based arbitration: prefer concrete results over vague ones
        if len(value_a) > len(value_b) * 1.5:
            return value_a
        if len(value_b) > len(value_a) * 1.5:
            return value_b
        # Default: prefer the value with explicit status markers
        markers = ["[EXECUTED]", "[REVIEWED]", "[PLAN]", "[DONE]", "[APPROVED]"]
        for marker in markers:
            if marker in value_a and marker not in value_b:
                return value_a
            if marker in value_b and marker not in value_a:
                return value_b
        return value_a  # Default to first value
