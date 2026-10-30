"""Example MCP server (from the Youth AI Lab workshop kit): "live" knowledge.

It gives the model two tools:
  - territories()           : the territories for which a fire danger level is available
  - fire_danger(territory)  : today's fire danger level for one territory, with its source and advice
and a third one, only when FIRE_DANGER_RECORDED=1 is set (an exercise of the workshop kit, not
used in this guide):
  - recorded_example(territory) : a day recorded in fire-danger.recorded.json, never today

The teaching point: the model cannot know today's level. Edit fire-danger.json during the
conversation and ask again: the answer follows, without restarting Hermes.

Out of season, many sources publish no level. The server then gives no level ("level": null),
with what the source says instead (status, source_says). It also gives no level when the file
is not dated today: an old file must never pass for today's level.

Transport: stdio (Hermes starts this script itself, see mcp_servers in hermes/config.yaml).
Dependency: the `mcp` package >= 2 (installed in /opt/workshop/venv in the Codespace image).
"""

import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp.server.mcpserver import MCPServer

DATA = Path(__file__).with_name("fire-danger.json")
RECORDED = Path(__file__).with_name("fire-danger.recorded.json")
# The five territories are all on Central European time: "today" is their day, not the
# Codespace's (UTC), which still shows yesterday until 01:00 or 02:00 in Europe.
TIMEZONE = ZoneInfo("Europe/Paris")
STATUSES = {
    "live": "the source shows a level for today",
    "season-over": "the source says the fire season is over",
    "no-level-shown": "the source shows no level today",
}

mcp = MCPServer("fire-danger")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def today():
    return datetime.datetime.now(TIMEZONE).date().isoformat()


def filled_in_later(value):
    """A field still marked TO BE COMPLETED: the model gets nothing rather than the marker."""
    return isinstance(value, str) and value.upper().startswith("TO BE COMPLETED")


def find(all_territories, territory):
    return {k: v for k, v in all_territories.items() if territory.lower() in k.lower()}


def today_entry(entry, file_date, day):
    """One territory as the model must read it: a level only if the file is today's and the
    facilitator marked it live."""
    status = entry.get("status", "")
    level = entry.get("level")
    if file_date != day:
        # Another day's status, source sentence and advice could pass for today's: only the fields
        # that do not change (scale, source, season) are given.
        shown = {"status": "not filled in today", "level": None,
                 "why_no_level": (f"The file is dated {file_date}, not today ({day}). "
                                  "Nobody has filled in today's level yet.")}
        fields = ("scale", "source", "season")
    else:
        shown = {"status": status if status in STATUSES else "not filled in"}
        if status != "live":
            shown["level"] = None
            shown["why_no_level"] = (STATUSES[status] + "." if status in STATUSES
                                     else "Today's status has not been filled in yet.")
        elif not isinstance(level, str) or not level.strip() or filled_in_later(level):
            shown["level"] = None
            shown["why_no_level"] = "Today's level has not been filled in yet."
        else:
            shown["level"] = level
        fields = ("source_says", "advice", "scale", "source", "season")
    for field in fields:
        value = entry.get(field)
        if isinstance(value, list):
            value = [line for line in value if not filled_in_later(line)]
        if value and not filled_in_later(value):
            shown[field] = value
    return shown


@mcp.tool()
def territories() -> str:
    """List the territories for which today's fire danger level is available."""
    try:
        data = load(DATA)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return f"fire-danger.json cannot be read ({e}). The facilitator must fix it."
    return "\n".join(data.get("territories", {})) or "No territory yet."


@mcp.tool()
def fire_danger(territory: str) -> str:
    """Today's wildfire danger level for a territory, with its scale, official source and advice.
    Call it for any question about today's level or today's situation. The rules themselves
    (what is forbidden, fines, obligations) are in the documents, not here.
    When "level" is null, there is no official level today: say so, with "why_no_level",
    "source_says" and the source. Never guess a level, and never give a weather forecast or
    another index as the level."""
    try:
        data = load(DATA)
    except FileNotFoundError:
        return "fire-danger.json not found: the facilitator must fill it in."
    except json.JSONDecodeError as e:
        return f"fire-danger.json is malformed ({e}). Fix it and try again."
    all_territories = data.get("territories", {})
    matches = find(all_territories, territory)
    if not matches:
        return f"No data for '{territory}'. Available territories: " + ", ".join(all_territories)
    day, file_date = today(), data.get("date")
    reply = {"today": day, "file_date": file_date}
    reply.update({name: today_entry(entry, file_date, day) for name, entry in matches.items()})
    return json.dumps(reply, ensure_ascii=False, indent=2)


def recorded_example(territory: str) -> str:
    """Only an example from a PAST day, copied from the official source on that day: never
    today's level. Present it as "On <recorded_on> (not today), <source> showed …".
    Call it only when the user asks for an example of a past day."""
    try:
        data = load(RECORDED)
    except FileNotFoundError:
        return "No recorded day: fire-danger.recorded.json is missing."
    except json.JSONDecodeError as e:
        return f"fire-danger.recorded.json is malformed ({e}). Fix it and try again."
    all_territories = data.get("territories", {})
    matches = find(all_territories, territory)
    if not matches:
        return f"No recorded day for '{territory}'. Recorded territories: " + ", ".join(all_territories)
    reply: dict[str, object] = {}
    for name, entry in matches.items():
        day = entry.get("recorded_on", "")
        if not day or filled_in_later(day):
            reply[name] = "No day recorded yet for this territory."
        else:
            reply[name] = {"label": f"RECORDED ON {day}, NOT TODAY", **entry}
    return json.dumps(reply, ensure_ascii=False, indent=2)


# Off by default: a recorded day within the model's reach could pass for today's level.
if os.environ.get("FIRE_DANGER_RECORDED") == "1":
    mcp.tool()(recorded_example)


if __name__ == "__main__":
    mcp.run()
