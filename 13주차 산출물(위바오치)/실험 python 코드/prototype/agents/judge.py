"""LLM-based Judge Agent for semantic conflict detection and resolution."""

import json
import time

from openai import OpenAI

from prototype.config import API_KEY, API_BASE_URL, MODEL_NAME


JUDGE_PROMPT = """You are a Judge Agent in a multi-agent shared memory system. Two agents have written potentially conflicting values to the same memory key.

Your task:
1. Determine if the two values semantically conflict (contradict each other, draw opposite conclusions, or make mutually exclusive claims).
2. If they conflict, choose which value is more correct/appropriate (MUST pick one).
3. If they do not conflict, return the more complete value.

Context:
Memory Key: {key}
Agent A ({agent_a}): {value_a}
Agent B ({agent_b}): {value_b}

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "conflict": true/false,
  "resolution": "value_a" or "value_b",
  "reasoning": "brief explanation"
}}"""


class JudgeAgent:
    """LLM-based semantic conflict judge using DeepSeek API."""

    def __init__(self):
        self.client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
        self.call_count = 0
        self.total_latency_ms = 0.0

    def judge(self, key: str, agent_a: str, value_a: str,
              agent_b: str, value_b: str) -> dict:
        """Evaluate whether two memory values semantically conflict and resolve."""
        prompt = JUDGE_PROMPT.format(
            key=key, agent_a=agent_a, value_a=value_a,
            agent_b=agent_b, value_b=value_b
        )

        start = time.time()
        self.call_count += 1
        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=500
            )
            latency_ms = (time.time() - start) * 1000
            self.total_latency_ms += latency_ms

            content = response.choices[0].message.content
            # Try to parse JSON from response
            result = self._parse_response(content)
            result["latency_ms"] = latency_ms
            return result
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            self.total_latency_ms += latency_ms
            return {
                "conflict": False,
                "resolution": "value_a",
                "merged_value": "",
                "reasoning": f"API error: {e}",
                "latency_ms": latency_ms
            }

    def _parse_response(self, content: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Strip markdown code fences
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "conflict": False,
                "resolution": "value_a",
                "merged_value": "",
                "reasoning": "Failed to parse judge response"
            }

    def reset_stats(self):
        self.call_count = 0
        self.total_latency_ms = 0.0
