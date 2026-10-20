
"""
Configurable negative-keyword rules for Jazz Radar.

A rule suppresses only keyword occurrences overlapping its
configured phrase or regular-expression match.
"""

REMOVE_KEYWORDS = {
    "GSM": {
        "enabled": True,
        "patterns": [
            r"\bgsm\s+(?:paper|papers)\b",
            r"\b\d+(?:\.\d+)?\s*gsm\b",
        ],
        "reason": "GSM refers to paper weight in this context.",
    },

    "Fiber": {
        "enabled": True,
        "patterns": [
            r"\bfiber\s+(?:reel|reels)\b",
            r"\bfiber\s+(?:paper|papers)\b",
            r"\bfiber\s+(?:cheque|cheques)\b",
            r"\bbiv\+fiber\b",
        ],
        "reason": "Fiber is used in a non-telecom context.",
    },

    "Storage": {
        "enabled": True,
        "patterns": [
            r"\bcold\s+storage\b",
            r"\bbonded\s+storage\b",
            r"\bstorage\s+and\s+courier\b",
            r"\bstorage\s+services\b",
            r"\bstorage\s+facility\b",
            r"\bstorage\s+facilities\b",
        ],
        "reason": "Storage is used in a non-ICT context.",
    },

    "Computer": {
        "enabled": True,
        "patterns": [
            r"\bcomputer\s+numerical\s+control(?:led)?\b",
            r"\bcomputer\s+grinding\s+machine\b",
            r"\bcomputer\s+stationery\b",
            r"\bcomputer\s+stationary\b",
        ],
        "reason": "Computer occurs in a non-ICT phrase.",
    },
}
