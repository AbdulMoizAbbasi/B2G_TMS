import re

SOURCE_REGION_MAP = {
    "Sindh PPRA": "South",
    "Balochistan PPRA": "South",
    "KP PPRA": "North2",
    "Punjab PPRA": "Central",
}


FEDERAL_CITY_REGION_MAP = {
    # ========================================================
    # NORTH1
    # Islamabad Capital Territory
    # ========================================================
    "islamabad": "North1",

    # Rawalpindi / surrounding major city
    "rawalpindi": "North1",
    "wah cantt": "North1",

    # ========================================================
    # NORTH2
    # Khyber Pakhtunkhwa
    # ========================================================
    "peshawar": "North2",
    "nowshera": "North2",
    "abbottabad": "North2",
    "mansehra": "North2",
    "mardan": "North2",
    "swabi": "North2",
    "kohat": "North2",
    "bannu": "North2",
    "dera ismail khan": "North2",
    "mingora": "North2",
    "swat": "North2",
    "charsadda": "North2",

    # ========================================================
    # CENTRAL
    # Punjab
    # ========================================================
    "lahore": "Central",
    "multan": "Central",
    "faisalabad": "Central",
    "gujranwala": "Central",
    "sialkot": "Central",
    "gujrat": "Central",
    "bahawalpur": "Central",
    "sargodha": "Central",
    "sheikhupura": "Central",
    "jhang": "Central",
    "rahim yar khan": "Central",
    "dera ghazi khan": "Central",
    "sahiwal": "Central",
    "okara": "Central",
    "kasur": "Central",
    "chakwal": "Central",
    "attock": "Central",
    "kamra": "Central",

    # ========================================================
    # SOUTH
    # Sindh
    # ========================================================
    "karachi": "South",
    "hyderabad": "South",
    "sukkur": "South",
    "larkana": "South",
    "nawabshah": "South",
    "shaheed benazirabad": "South",
    "mirpur khas": "South",
    "thatta": "South",
    "badin": "South",
    "jacobabad": "South",
    "khairpur": "South",

    # Balochistan
    "quetta": "South",
    "gwadar": "South",
    "turbat": "South",
    "khuzdar": "South",
    "chaman": "South",
    "sibi": "South",
    "hub": "South",
}


def get_region_name(
    source_name: str,
    city: str | None = None,
) -> str | None:
    """
    Determine the JazzWorld region for a tender.

    Non-Federal sources use a fixed source-to-region
    mapping.

    Federal PPRA uses an explicit city-to-region
    mapping.

    If a Federal city is not present in the mapping,
    return None so that the Admin can assign the region
    manually.

    No region is guessed for unknown cities.
    """

    if source_name in SOURCE_REGION_MAP:
        return SOURCE_REGION_MAP[source_name]

    if source_name == "Federal PPRA":
        return get_federal_region(city)

    return None


def get_federal_region(
    city: str | None,
) -> str | None:
    """
    Determine the JazzWorld region for a Federal PPRA
    tender using the explicit city mapping.

    Unknown or missing cities return None.

    No fallback or geographic guessing is performed.
    """

    if not city:
        return None

    city_normalized = re.sub(r"[^\w\s]", "", str(city)).strip().lower()

    return FEDERAL_CITY_REGION_MAP.get(
        city_normalized
    )