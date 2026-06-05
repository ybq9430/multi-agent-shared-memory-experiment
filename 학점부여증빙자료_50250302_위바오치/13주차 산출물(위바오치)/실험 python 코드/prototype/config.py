"""Experiment configuration constants."""

# DeepSeek API (via openai SDK — uses OpenAI-compatible endpoint)
# Set DEEPSEEK_API_KEY environment variable before running, or replace None with your key
import os
API_KEY = os.environ.get("DEEPSEEK_API_KEY", None)
API_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

# Database
DB_PATH = "experiment_results.db"

# Agents
AGENT_COUNT = 3
AGENT_ROLES = ["planner", "executor", "reviewer"]
LEADER_ROLE = "reviewer"  # Reviewer agent serves as leader

# Memory
WORKING_MEMORY_KEYS = ["task_plan", "task_status", "current_step"]
LONG_TERM_MEMORY_KEYS = ["knowledge_base", "decision_log", "feedback_history"]

# Experiment
ITERATIONS = 30
RANDOM_SEED = 42

# Timing (seconds)
SIMULTANEOUS_WRITE_WINDOW = 0.05  # 50ms
ORDERING_CONFLICT_DELAY_MIN = 1
ORDERING_CONFLICT_DELAY_MAX = 300

# Trust score simulation
INITIAL_TRUST_SCORE = 0.5
TRUST_SCORE_RANGE = (0.0, 1.0)
