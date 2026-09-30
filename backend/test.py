from tender_scraper.storage.region_mapper import get_region_name


test_cases = [
    ("Federal PPRA", "Islamabad"),
    ("Federal PPRA", "Rawalpindi"),
    ("Federal PPRA", "Wah Cantt"),
    ("Federal PPRA", "Peshawar"),
    ("Federal PPRA", "Nowshera"),
    ("Federal PPRA", "Lahore"),
    ("Federal PPRA", "Multan"),
    ("Federal PPRA", "Karachi"),
    ("Federal PPRA", "Hyderabad"),
    ("Federal PPRA", "Quetta"),
    ("Federal PPRA", "Unknown City"),
    ("Federal PPRA", None),

    ("KP PPRA", None),
    ("Punjab PPRA", None),
    ("Sindh PPRA", None),
    ("Balochistan PPRA", None),
]


for source, city in test_cases:
    region = get_region_name(
        source_name=source,
        city=city,
    )

    print(
        f"{source:20} | "
        f"{str(city):20} → "
        f"{region}"
    )