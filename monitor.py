import json
import os
import sys
from datetime import datetime, timezone

import requests


URL = "https://boutique.saf-astronomie.fr/wp-admin/admin-ajax.php"

KNOWN_EVENTS_FILE = "known_events.json"


def get_attributes():
    # Generate the current timestamp dynamically.
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "id": "bookacti-wc-form-fields-product-variation-13208",
        "class": "bookacti-woocommerce-product-booking-system",
        "hide_availability": 100,
        "hide_calendar": ["none"],
        "calendars": [2],
        "activities": [3],
        "group_categories": ["none"],
        "groups_only": 0,
        "groups_single_events": 0,
        "groups_first_event_only": 0,
        "multiple_bookings": 0,
        "bookings_only": 0,
        "tooltip_booking_list": 0,
        "tooltip_booking_list_columns": [],
        "status": [],
        "user_id": [],
        "method": "calendar",
        "auto_load": 0,
        "display_period": {
            "start": now,
            "end": ""
        },
        "availability_period": {
            "start": now,
            "end": ""
        },
        "start": now,
        "end": "",
        "trim": 1,
        "out_of_period_events": 0,
        "past_events": 0,
        "past_events_bookable": 0,
        "use_global_days_off": 0,
        "days_off": [],
        "check_roles": 1,
        "picked_events": [],
        "form_id": 10,
        "form_action": "default",
        "when_perform_form_action": "on_submit",
        "select_first_event": 0,
        "redirect_url_by_activity": [],
        "redirect_url_by_group_category": [],
        "redirect_url_by_group_category": [],
        "display_data": {
            "slotMinTime": "19:00",
            "slotMaxTime": "23:00"
        },
        "context": "",
        "custom_dataset": "",
        "product_by_activity": [],
        "product_by_group_category": [],
        "products_page_url": []
    }


def fetch_events():
    attributes = get_attributes()

    response = requests.post(
        URL,
        data={
            "action": "bookactiReloadBookingSystem",
            "attributes": json.dumps(attributes),
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "success":
        print("SAF returned an error:")
        print(json.dumps(data, indent=2))
        sys.exit(1)

    booking_data = data["booking_system_data"]

    return booking_data.get("events", [])


def load_known_events():
    if not os.path.exists(KNOWN_EVENTS_FILE):
        return {}

    with open(KNOWN_EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_known_events(events):
    with open(KNOWN_EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def main():
    current_events = fetch_events()

    # Create a clean dictionary indexed by event ID.
    current = {
        str(event["id"]): {
            "id": event["id"],
            "title": event.get("title"),
            "start": event.get("start"),
            "end": event.get("end"),
            "activity_id": event.get("activity_id"),
        }
        for event in current_events
    }

    previous = load_known_events()

    # First run: establish baseline without sending an alert.
    if not previous:
        print(f"Initial baseline: {len(current)} events found.")
        save_known_events(current)
        return

    new_event_ids = set(current) - set(previous)

    if new_event_ids:
        print(f"NEW EVENTS FOUND: {len(new_event_ids)}")

        for event_id in sorted(new_event_ids):
            event = current[event_id]

            print(
                f"NEW: {event['title']} | "
                f"{event['start']} - {event['end']} | "
                f"ID {event['id']}"
            )

        # Save the updated list.
        save_known_events(current)

        # Tell GitHub Actions that an alert is required.
        with open("new_events.json", "w", encoding="utf-8") as f:
            json.dump(
                [current[event_id] for event_id in new_event_ids],
                f,
                indent=2,
                ensure_ascii=False,
            )

    else:
        print(f"No new events. {len(current)} events currently known.")

        # Still save in case the response has changed.
        save_known_events(current)


if __name__ == "__main__":
    main()
