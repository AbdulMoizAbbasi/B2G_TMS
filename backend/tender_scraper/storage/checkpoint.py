import json
from datetime import datetime
from pathlib import Path


CHECKPOINT_FILE = (
    Path(__file__).resolve().parent.parent
    / "state"
    / "checkpoints.json"
)


def _ensure_checkpoint_file():
    """
    Create the checkpoint directory and file
    if they do not already exist.
    """

    CHECKPOINT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not CHECKPOINT_FILE.exists():

        with open(
            CHECKPOINT_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                {},
                file,
                indent=4,
                ensure_ascii=False,
            )


def load_checkpoints():
    """
    Load all portal checkpoints.

    Returns:
        dict
    """

    _ensure_checkpoint_file()

    try:

        with open(
            CHECKPOINT_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return {}

    if not isinstance(data, dict):
        return {}

    return data


def save_checkpoints(checkpoints):
    """
    Save all portal checkpoints.
    """

    CHECKPOINT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = CHECKPOINT_FILE.with_suffix(
        ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            checkpoints,
            file,
            indent=4,
            ensure_ascii=False,
        )

    temporary_file.replace(
        CHECKPOINT_FILE
    )


def get_checkpoint(portal):
    """
    Get the checkpoint for a specific portal.

    Returns:
        {
            "last_date": "...",
            "last_tender_key": "...",
            "last_run_at": "..."
        }

    If no checkpoint exists, returns:
        {
            "last_date": None,
            "last_tender_key": None,
            "last_run_at": None
        }
    """

    checkpoints = load_checkpoints()

    checkpoint = checkpoints.get(
        portal
    )

    if not isinstance(
        checkpoint,
        dict,
    ):
        return {
            "last_date": None,
            "last_tender_key": None,
            "last_run_at": None,
        }

    return {
        "last_date": checkpoint.get(
            "last_date"
        ),
        "last_tender_key": checkpoint.get(
            "last_tender_key"
        ),
        "last_run_at": checkpoint.get(
            "last_run_at"
        ),
    }


def update_checkpoint(
    portal,
    last_date,
    last_tender_key,
):
    """
    Update the checkpoint for a portal.

    The checkpoint is updated only after the caller
    confirms that the portal's data was successfully
    processed and stored.
    """

    if not portal:
        raise ValueError(
            "portal cannot be empty."
        )

    if not last_date:
        raise ValueError(
            "last_date cannot be empty."
        )

    if not last_tender_key:
        raise ValueError(
            "last_tender_key cannot be empty."
        )

    checkpoints = load_checkpoints()

    checkpoints[portal] = {
        "last_date": str(
            last_date
        ),
        "last_tender_key": str(
            last_tender_key
        ),
        "last_run_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
    }

    save_checkpoints(
        checkpoints
    )

    return checkpoints[portal]


def clear_checkpoint(portal):
    """
    Remove a portal's checkpoint.

    Useful during development/testing when we want
    to perform a fresh scrape for that portal.
    """

    checkpoints = load_checkpoints()

    if portal in checkpoints:

        del checkpoints[portal]

        save_checkpoints(
            checkpoints
        )

        return True

    return False


def clear_all_checkpoints():
    """
    Remove all portal checkpoints.
    """

    save_checkpoints({})


if __name__ == "__main__":

    print("=" * 70)
    print("CHECKPOINT SYSTEM TEST")
    print("=" * 70)

    portal = "Punjab PPRA"

    print()
    print("Current checkpoint:")
    print(
        get_checkpoint(portal)
    )

    print()
    print("Updating checkpoint...")

    updated = update_checkpoint(
        portal=portal,
        last_date="2026-09-09",
        last_tender_key=(
            "https://eproc.punjab.gov.pk/"
            "Tenders/50485054/4857/"
            "0909202607415253562330255530.pdf"
        ),
    )

    print()
    print("Updated checkpoint:")
    print(updated)

    print()
    print("Reading checkpoint again:")

    print(
        get_checkpoint(portal)
    )

    print()
    print("=" * 70)
    print("CHECKPOINT TEST COMPLETE")
    print("=" * 70)