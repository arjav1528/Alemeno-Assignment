import json
import time

import google.generativeai as genai

from lib.env import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

MAX_RETRIES = 3


def _call_with_retry(prompt: str) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0,
                },
            )
            return response.text
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
