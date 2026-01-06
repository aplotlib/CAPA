from __future__ import annotations
from typing import Any, Dict
from openai import OpenAI
from .config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM = """You are a safety/compliance analyst.
Classify whether a web/recall record likely pertains to the given product.
Be conservative: if unclear, say "uncertain" and lower confidence.
Return ONLY JSON."""
SCHEMA = {
  "type": "object",
  "properties": {
    "relation": {"type":"string","enum":["likely_match","similar_product","not_related","uncertain"]},
    "category": {"type":"string","enum":["recall","regulatory_action","injury","lawsuit","negative_press","other"]},
    "severity": {"type":"string","enum":["low","medium","high"]},
    "confidence": {"type":"number","minimum":0,"maximum":1},
    "why": {"type":"string"}
  },
  "required":["relation","category","severity","confidence","why"],
  "additionalProperties": False
}

def classify_hit(sku: str, product_name: str, hit: Dict[str, Any]) -> Dict[str, Any]:
    user = {
        "sku": sku,
        "product_name": product_name,
        "hit": hit
    }
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role":"system","content":SYSTEM},
            {"role":"user","content":f"Classify:\n{user}"}
        ],
        response_format={"type":"json_schema","json_schema":{"name":"hit_classification","schema":SCHEMA}}
    )
    return resp.output_parsed  # dict
