from pathlib import Path


def classify_document(pdf_path: str) -> dict:
    name = Path(pdf_path).name.upper()

    document_type = "UNKNOWN"
    architecture_state = None

    if "_RFP_QA_" in name:
        document_type = "RFP_QA"
    elif "_MEETING_MINUTES_" in name:
        document_type = "MEETING_MINUTES"
    elif "_TECHNICAL_ANNEX_" in name:
        document_type = "TECHNICAL_ANNEX"
        if "AS-IS" in name or "AS_IS" in name:
            architecture_state = "AS_IS"
        elif "TO-BE" in name or "TO_BE" in name:
            architecture_state = "TO_BE"
    elif "_RFP_" in name:
        document_type = "RFP"

    return {
        "document_type": document_type,
        "architecture_state": architecture_state
    }