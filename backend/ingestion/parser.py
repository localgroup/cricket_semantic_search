from __future__ import annotations
import hashlib
import re
from datetime import datetime
from pathlib import Path

LINE_RE = re.compile(
    r'^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+'
    r'Match:(?P<match_id>\S+)\s+Team:(?P<team>.+?)\s+Player:(?P<player>.+?)\s+'
    r'Event:(?P<event_type>.+?)\s+Runs:(?P<runs>-?\d+)\s+Over:(?P<over>-?\d+)\s+'
    r'Status:(?P<status>.+?)\s+Commentary:(?P<commentary>.*)$'
)
ROLE_RE = re.compile(r'\(([^()]*)\)')
VENUE_RE = re.compile(r'\bat\s+([^()]+?)\s*\(([^()]*)\)')

def parse_line(line: str, line_number: int = 1) -> dict:
    raw = line.strip()
    match = LINE_RE.match(raw)
    if not match:
        raise ValueError(f"Line {line_number} does not match the expected cricket log format")
    data = match.groupdict()
    try:
        timestamp = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(f"Line {line_number} has an invalid timestamp") from exc
    commentary = data["commentary"].strip()
    # Optional metadata is extracted only when the commentary provides a clear signal.
    role_match = re.search(rf"{re.escape(data['player'])}\s*\(([^()]*)\)", commentary, re.I)
    venue_match = VENUE_RE.search(commentary)
    weather = venue_match.group(2).strip() if venue_match and venue_match.group(2).strip().lower() not in {"", "unknown", "n/a"} else None
    venue = venue_match.group(1).strip() if venue_match and venue_match.group(1).strip() else None
    role = role_match.group(1).strip() if role_match and role_match.group(1).strip().lower() not in {"", "unknown", "n/a"} else None
    event = {
        "event_id": hashlib.sha256(f"{line_number}:{raw}".encode("utf-8")).hexdigest()[:24],
        "line_number": line_number,
        "timestamp": timestamp,
        "match_id": data["match_id"].strip(),
        "team": data["team"].strip(),
        "player": data["player"].strip(),
        "event_type": data["event_type"].strip(),
        "runs": int(data["runs"]),
        "over": int(data["over"]),
        "status": data["status"].strip(),
        "commentary": commentary,
        "role": role,
        "venue": venue,
        "weather": weather,
        "raw_line": raw,
    }
    event["search_text"] = (
        f"Match {event['match_id']}. Team {event['team']}. Player {event['player']}. "
        f"Event {event['event_type']}. Runs {event['runs']}. Over {event['over']}. "
        f"Status {event['status']}. Commentary: {commentary}. "
        f"Role: {role or 'not specified'}. Venue: {venue or 'not specified'}. "
        f"Weather: {weather or 'not specified'}."
    )
    anomalies = []
    if event["runs"] < 0:
        anomalies.append("negative_runs")
    if event["over"] < 0:
        anomalies.append("negative_over")
    if event["event_type"].lower() == "six hit" and event["runs"] == 0:
        anomalies.append("six_hit_with_zero_runs")
    if event["event_type"].lower() == "lbw given" and event["runs"] > 0:
        anomalies.append("lbw_given_with_positive_runs")
    event["quality_flags"] = anomalies
    return event

def parse_text_file(path: str | Path) -> list[dict]:
    path = Path(path)
    lines = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    events = []
    errors = []
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            events.append(parse_line(line, line_no))
        except ValueError as exc:
            errors.append(str(exc))
    if not events:
        raise ValueError("No valid cricket events were parsed.")
    if errors:
        raise ValueError(f"Could not parse {len(errors)} line(s): " + "; ".join(errors[:5]))
    return events
