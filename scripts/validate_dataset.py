from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ingestion.parser import parse_text_file

source = Path(__file__).resolve().parents[1] / "data" / "cricket_log.txt"
events = parse_text_file(source)
print(f"Parsed events: {len(events)}")
print(f"Matches: {len({e['match_id'] for e in events})}")
print(f"Event types: {len({e['event_type'] for e in events})}")
print(f"Flagged records: {sum(bool(e['quality_flags']) for e in events)}")
