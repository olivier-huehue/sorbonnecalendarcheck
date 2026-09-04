import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import requests

URL = "https://boutique.saf-astronomie.fr/wp-admin/admin-ajax.php"

ATTRIBUTES = {
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
        "start": "",
        "end": ""
    },
    "availability_period": {
        "start": "",
        "end": ""
    },
    "start": "",
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

STATE_FILE = "known_events.json"

EMAIL_TO = "lugandolivier@gmail.com"
EMAIL_FROM = os.environ["GMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]


def get_events():
    # SAF expects the current date/time in this field.
    now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M:%S")

    attributes = ATTRIBUTES.copy()
    attributes["display_period"] = {"start": now, "end": ""}
    attributes["availability_period"] = {"start": now, "end": ""}
    attributes["start"] = now

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://boutique.saf-astronomie.fr",
        "Referer": "https://boutique.saf-astronomie.fr/produit/visite-de-lobservatoire-de-la-sorbonne/",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.post(
        URL,
        data={
            "action": "bookactiReloadBookingSystem",
            "attributes": json.dumps(attributes)
        },
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(f"SAF returned an error: {data}")

    return data["booking_system_data"]["events"]


def event_key(event):
    # We use date/time rather than event ID.
    # This means a date recreated by SAF with a different ID
    # will not generate a duplicate alert.
    return f"{event['start']}|{event['end']}"


def send_email(new_events):
    subject = f"SAF Sorbonne — {len(new_events)} new event(s) available"

    lines = [
        "New date(s) have been detected on the Société astronomique de France calendar:",
        ""
    ]

    for event in new_events:
        lines.append(
            f"• {event['start']} → {event['end']}"
        )

    lines.extend([
        "",
        "Check the reservation page:",
        "https://boutique.saf-astronomie.fr/produit/visite-de-lobservatoire-de-la-sorbonne/"
    ])

    body = "\n".join(lines)

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(
            EMAIL_FROM,
            EMAIL_TO,
            message.as_string()
        )


def main():
    current_events = get_events()

    # Only keep future events.
    current_events = [
        event for event in current_events
        if event.get("start")
    ]

    current = {
        event_key(event): event
        for event in current_events
    }

    print(f"Found {len(current)} events.")

    # First run = establish baseline.
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                current,
                f,
                indent=2,
                ensure_ascii=False
            )

        print("Initial baseline created. No email sent.")
        return

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        previous = json.load(f)

    new_keys = set(current) - set(previous)

    if new_keys:
        new_events = [current[key] for key in sorted(new_keys)]

        print(f"NEW EVENTS FOUND: {len(new_events)}")

        for event in new_events:
            print(
                f"NEW: {event['start']} → {event['end']}"
            )

        send_email(new_events)

        print(f"Email sent to {EMAIL_TO}")

    else:
        print("No new events.")

    # Update the stored list.
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            current,
            f,
            indent=2,
            ensure_ascii=False
        )


if __name__ == "__main__":
    main()
