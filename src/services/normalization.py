from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, Optional


def _coerce_date(value: Any) -> Optional[str]:
    """Best-effort date normalization to ISO format string."""
    if not value:
        return None
    if isinstance(value, (datetime,)):
        return value.date().isoformat()
    if isinstance(value, str):
        txt = value.strip()
        # Common formats: YYYY-MM-DD, YYYYMMDD, DD Mon YYYY, RFC822 snippets
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d %b %Y", "%a, %d %b %Y %H:%M:%S %Z"):
            try:
                return datetime.strptime(txt, fmt).date().isoformat()
            except Exception:
                continue
        # Try partial ISO (first 10 chars)
        if len(txt) >= 10 and txt[4] == "-":
            return txt[:10]
    try:
        # numeric timestamp
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value).date().isoformat()
    except Exception:
        return None
    return None


def _stringify_model_numbers(model_numbers: Any) -> str:
    if not model_numbers:
        return ""
    if isinstance(model_numbers, str):
        return model_numbers
    if isinstance(model_numbers, Iterable):
        return ", ".join([str(x) for x in model_numbers if x])
    return str(model_numbers)


@dataclass
class NormalizedRecord:
    source: str
    jurisdiction: str
    category: str
    recall_class: str = "Unspecified"
    product_type: str = "Unknown"
    product: str = ""
    manufacturer: str = ""
    model_numbers: Any = field(default_factory=list)
    date: Any = None
    description: str = ""
    reason: str = ""
    link: str = ""
    document_url: str = ""
    status: str = ""
    risk_level: str = "Medium"
    provenance: Optional[Dict[str, Any]] = None
    ai_verified: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        model_str = _stringify_model_numbers(self.model_numbers)
        normalized_date = _coerce_date(self.date)
        provenance_payload = self.provenance or {}

        record = {
            "Source": self.source,
            "Jurisdiction": self.jurisdiction,
            "Category": self.category,
            "Recall_Class": self.recall_class or "Unspecified",
            "Product_Type": self.product_type or "Unknown",
            "Product": self.product,
            "Manufacturer": self.manufacturer,
            "Firm": self.manufacturer,  # backward compatibility with UI
            "Model_Numbers": model_str,
            "Date": normalized_date or "",
            "Description": self.description,
            "Reason": self.reason,
            "Link": self.link,
            "Document_URL": self.document_url or self.link,
            "Status": self.status,
            "Risk_Level": self.risk_level,
            "Provenance": provenance_payload,
        }

        if self.ai_verified is not None:
            record["AI_Verified"] = self.ai_verified
        return record

    @classmethod
    def from_raw(cls, raw: Dict[str, Any], defaults: Dict[str, Any] | None = None) -> "NormalizedRecord":
        defaults = defaults or {}
        merged = {**defaults, **raw}
        return cls(
            source=merged.get("Source") or merged.get("source") or "Unknown",
            jurisdiction=merged.get("Jurisdiction") or merged.get("jurisdiction") or "Global",
            category=merged.get("Category") or merged.get("category") or "regulatory_action",
            recall_class=merged.get("Recall_Class") or merged.get("recall_class") or merged.get("Class", "Unspecified"),
            product_type=merged.get("Product_Type") or merged.get("product_type") or merged.get("Type", "Unknown"),
            product=merged.get("Product") or merged.get("product") or merged.get("Title", ""),
            manufacturer=merged.get("Manufacturer") or merged.get("Firm") or merged.get("manufacturer", ""),
            model_numbers=merged.get("Model_Numbers") or merged.get("model_numbers") or merged.get("Model Info") or merged.get("Model"),
            date=merged.get("Date") or merged.get("date"),
            description=merged.get("Description") or merged.get("description", ""),
            reason=merged.get("Reason") or merged.get("reason", ""),
            link=merged.get("Link") or merged.get("url") or merged.get("URL", ""),
            document_url=merged.get("Document_URL") or merged.get("Document") or merged.get("document_url", ""),
            status=merged.get("Status") or merged.get("status", ""),
            risk_level=merged.get("Risk_Level") or merged.get("risk_level") or "Medium",
            provenance=merged.get("Provenance"),
            ai_verified=merged.get("AI_Verified"),
        )
