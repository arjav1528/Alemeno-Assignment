import json
import time

from groq import Groq

from lib.env import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.1-8b-instant"
MAX_RETRIES = 3


def _call_with_retry(prompt: str) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("LLM returned empty response")
            return content
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise e
            time.sleep(2**attempt)
    raise RuntimeError("LLM call failed after all retries")


def classify_transactions(transactions: list[dict]) -> dict:
    prompt = f"""Classify each transaction into exactly one category:
Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, or Other.

Transactions:
{json.dumps(transactions)}

Return a JSON object mapping txn_id to category.
Example: {{"TXN001": "Food", "TXN002": "Shopping"}}"""

    return json.loads(_call_with_retry(prompt))


def generate_summary(stats: dict) -> dict:
    prompt = f"""Given these transaction statistics:
{json.dumps(stats)}

Write a 2-3 sentence spending narrative and assess risk level.
Return JSON with:
- "narrative": 2-3 sentence spending summary
- "risk_level": "low", "medium", or "high" based on anomaly ratio"""

    llm_result = json.loads(_call_with_retry(prompt))

    return {
        "total_spend_inr": stats["total_spend_inr"],
        "total_spend_usd": stats["total_spend_usd"],
        "top_merchants": stats["top_merchants"],
        "anomaly_count": stats["anomaly_count"],
        "narrative": llm_result["narrative"],
        "risk_level": llm_result["risk_level"],
    }
