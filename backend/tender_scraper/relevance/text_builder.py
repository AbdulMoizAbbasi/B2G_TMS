def build_tender_text(tender):
    if not isinstance(tender, dict):
        return ""

    # Federal PPRA
    tender_title = tender.get("Tender Title")
    if tender_title:
        return str(tender_title).strip()

    # Punjab PPRA
    tender_details = tender.get("tender_details")
    if tender_details:
        return str(tender_details).strip()

    # Balochistan PPRA
    tender_name = tender.get("Name")
    if tender_name:
        return str(tender_name).strip()

    # Sindh PPRA
    tender_name = tender.get("name")
    if tender_name:
        return str(tender_name).strip()

    return ""