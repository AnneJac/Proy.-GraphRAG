import re
from pathlib import Path

def extract_entities(text: str, pdf_path: str | None = None) -> dict:
    entities = {
        "BankEntity": [],
        "BankProfile": [],
        "EvolutionEvent": [],
        "PersonnelEntity": [],
        "PersonnelRole": [],
        "ProjectEntity": [],
        "ProjectStatus": [],
        "SourceDocument": [],
    }

    if pdf_path:
        path = Path(pdf_path)
        entities["SourceDocument"].append(path.name)

        parts = path.parts
        if "output" in parts:
            idx = parts.index("output")
            if len(parts) > idx + 1:
                entities["BankEntity"].append(parts[idx + 1])
            if len(parts) > idx + 2:
                entities["ProjectEntity"].append(parts[idx + 2])

    role_matches = re.findall(
        r"\b(Project Manager|Program Manager|Technical Lead|Solution Architect|Architect|"
        r"Analyst|Engineer|Developer|Coordinator|Director|Manager|Product Owner)\b",
        text,
        flags=re.IGNORECASE,
    )
    entities["PersonnelRole"].extend(sorted(set(role_matches)))

    status_matches = re.findall(
        r"\b(Active|In Progress|Completed|Delayed|Cancelled|On Hold|Finalized)\b",
        text,
        flags=re.IGNORECASE,
    )
    entities["ProjectStatus"].extend(sorted(set(status_matches)))

    evolution_matches = re.findall(
        r"\b(Migration|Upgrade|Optimization|Modernization|Implementation|Expansion)\b",
        text,
        flags=re.IGNORECASE,
    )
    entities["EvolutionEvent"].extend(sorted(set(evolution_matches)))

    profile_matches = re.findall(
        r"\b(retail banking|corporate banking|digital banking|microfinance|commercial banking|investment banking)\b",
        text,
        flags=re.IGNORECASE,
    )
    entities["BankProfile"].extend(sorted(set(profile_matches)))

    personnel_matches = re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", text)
    if personnel_matches:
        entities["PersonnelEntity"].extend(sorted(set(personnel_matches[:20])))

    return {k: v for k, v in entities.items() if v}