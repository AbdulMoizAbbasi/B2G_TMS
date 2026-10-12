
import re

SOURCE_REGION_MAP = {
    "Sindh PPRA": "South",
    "Balochistan PPRA": "South",
    "KP PPRA": "North2",
    "Punjab PPRA": "Central",
}

DEFENSE_ORGANIZATIONS = {
    "directorate of procurement (navy)": "Defense Vertical",
    "ge (army)": "Defense Vertical",
    "directorate general procurement (army)": "Defense Vertical",
    "pakistan airforce": "Defense Vertical",
    "directorate of procurement (air)": "Defense Vertical",
}


def normalize_organization(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


FEDERAL_CITY_REGION_MAP = {
    # North1
    "islamabad": "North1",
    "rawalpindi": "North1",
    "wah cantt": "North1",

    # North2
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

    # Central
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

    # South - Sindh
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

    # South - Balochistan
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
    organization: str | None = None,
) -> str | None:
    """
    Determine the tender's automatic JazzWorld region.

    Priority:
    1. Defense organization mapping.
    2. Existing non-Federal source mapping.
    3. Existing Federal city mapping.
    4. None for unknown or missing mappings.

    Admin-assigned regions are preserved separately by
    the persistence layer.
    """
    normalized_organization = normalize_organization(organization)

    if normalized_organization in DEFENSE_ORGANIZATIONS:
        return DEFENSE_ORGANIZATIONS[normalized_organization]

    if source_name in SOURCE_REGION_MAP:
        return SOURCE_REGION_MAP[source_name]

    if source_name == "Federal PPRA":
        return get_federal_region(city)

    return None


def get_federal_region(city: str | None) -> str | None:
    """
    Map Federal PPRA tenders using the explicit city map.
    Unknown or missing cities return None.
    """
    if not city:
        return None

    city_normalized = re.sub(
        r"[^\w\s]", "", str(city)
    ).strip().lower()

    city_normalized = re.sub(r"\s+", " ", city_normalized)

    return FEDERAL_CITY_REGION_MAP.get(city_normalized)


if __name__ == "__main__":
    tests = [
        ("Federal PPRA", "Karachi", "Directorate of Procurement (Navy)", "Defense Vertical"),
        ("Punjab PPRA", None, "GE (Army)", "Defense Vertical"),
        ("Sindh PPRA", None, "Pakistan Airforce", "Defense Vertical"),
        ("Federal PPRA", "Lahore", "Normal Organization", "Central"),
        ("Punjab PPRA", None, "Normal Organization", "Central"),
        ("Sindh PPRA", None, "Normal Organization", "South"),
        ("Federal PPRA", "Islamabad", "Normal Organization", "North1"),
        ("Federal PPRA", "Unknown City", "Normal Organization", None),
    ]

    for source, city, organization, expected in tests:
        actual = get_region_name(source, city, organization)
        result = "PASS" if actual == expected else "FAIL"
        print(f"{result}: {source} | {organization} | expected={expected}, actual={actual}")
