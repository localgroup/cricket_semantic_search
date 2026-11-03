"""Dash frontend for the Cricket Log Semantic Search Django API."""

import os

import requests
from dash import Dash, Input, Output, State, dash_table, dcc, html

API_BASE = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000")
TIMEOUT = 30

app = Dash(__name__)
app.title = "Cricket Log Semantic Search"
server = app.server

PAGE_STYLE = {
    "minHeight": "100vh",
    "padding": "48px 20px 72px",
    "background": "linear-gradient(135deg, #f7f9fc 0%, #eef3f8 100%)",
    "color": "#172033",
    "fontFamily": "Arial, sans-serif",
}
CONTENT_STYLE = {"maxWidth": "980px", "margin": "0 auto"}
CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "border": "1px solid #d9e2ec",
    "borderRadius": "16px",
    "boxShadow": "0 10px 28px rgba(23, 32, 51, 0.08)",
    "padding": "28px",
    "marginTop": "24px",
}
INPUT_STYLE = {
    "flex": "1 1 460px",
    "minWidth": "0",
    "boxSizing": "border-box",
    "height": "48px",
    "padding": "11px 14px",
    "border": "1px solid #b8c5d6",
    "borderRadius": "8px",
    "fontSize": "16px",
    "lineHeight": "24px",
}
BUTTON_STYLE = {
    "padding": "12px 20px",
    "border": "0",
    "borderRadius": "8px",
    "backgroundColor": "#0f5d5e",
    "color": "#ffffff",
    "fontSize": "16px",
    "fontWeight": "700",
    "cursor": "pointer",
}
MUTED_STYLE = {"color": "#5b6878", "lineHeight": "1.55", "margin": "8px 0 18px"}

SEARCH_COLUMNS = [
    {"name": "Match", "id": "match_id"},
    {"name": "Event", "id": "event_type"},
    {"name": "Player", "id": "player"},
    {"name": "Team", "id": "team"},
    {"name": "Commentary", "id": "commentary"},
    {"name": "Relevance", "id": "score"},
]


def api_post(path, payload):
    """Send a JSON request to Django and return its JSON response."""
    response = requests.post(f"{API_BASE}{path}", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def display_value(value, fallback="—"):
    """Keep absent API fields readable without inventing data."""
    return fallback if value in (None, "") else value


def format_score(value):
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "—"


def search_rows(results):
    """Restrict table data to fields returned by the search API and shown in the UI."""
    return [
        {
            "match_id": display_value(result.get("match_id")),
            "event_type": display_value(result.get("event_type")),
            "player": display_value(result.get("player")),
            "team": display_value(result.get("team")),
            "commentary": display_value(result.get("commentary")),
            "score": format_score(result.get("score")),
        }
        for result in results
    ]


def source_cards(sources):
    """Render the RAG evidence returned by the chat API."""
    if not sources:
        return html.P("No retrieved evidence was returned.", style=MUTED_STYLE)

    return [
        html.Div(
            [
                html.Div(
                    [
                        html.Span(
                            display_value(source.get("match_id")),
                            style={
                                "backgroundColor": "#e5f2f2",
                                "color": "#0f5d5e",
                                "borderRadius": "999px",
                                "fontWeight": "700",
                                "fontSize": "13px",
                                "padding": "4px 9px",
                            },
                        ),
                        html.Span(
                            display_value(source.get("event_type")),
                            style={"fontWeight": "700", "marginLeft": "10px"},
                        ),
                        html.Span(
                            f"Relevance {format_score(source.get('score'))}",
                            style={"color": "#5b6878", "fontSize": "13px", "marginLeft": "10px"},
                        ),
                    ],
                    style={"marginBottom": "8px"},
                ),
                html.P(
                    display_value(source.get("commentary")),
                    style={"margin": "0", "lineHeight": "1.55"},
                ),
            ],
            style={"borderTop": "1px solid #e6edf3", "padding": "16px 0"},
        )
        for source in sources
    ]


app.layout = html.Main(
    html.Div(
        [
            html.Header(
                [
                    html.P(
                        "CRICKET LOG ANALYTICS",
                        style={
                            "color": "#0f5d5e",
                            "fontSize": "12px",
                            "fontWeight": "700",
                            "letterSpacing": "1.4px",
                            "margin": "0 0 8px",
                        },
                    ),
                    html.H1("Cricket Log Semantic Search", style={"fontSize": "36px", "margin": "0"}),
                    html.P(
                        "Search match commentary by meaning or ask a grounded question about the indexed logs.",
                        style={"fontSize": "17px", **MUTED_STYLE},
                    ),
                ]
            ),
            html.Section(
                [
                    html.H2("Semantic search", style={"margin": "0"}),
                    html.P("Find commentary that is meaningfully related to your query.", style=MUTED_STYLE),
                    html.Div(
                        [
                            dcc.Input(
                                id="search-query",
                                type="text",
                                placeholder="e.g. disputed decisions involving a wicket",
                                style=INPUT_STYLE,
                            ),
                            html.Button("Search", id="search-button", n_clicks=0, style=BUTTON_STYLE),
                        ],
                        style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
                    ),
                    html.Div(
                        id="search-status",
                        style={"minHeight": "24px", "marginTop": "14px", "color": "#5b6878"},
                    ),
                    dash_table.DataTable(
                        id="search-results",
                        columns=SEARCH_COLUMNS,
                        data=[],
                        page_size=10,
                        style_table={"overflowX": "auto", "marginTop": "4px"},
                        style_header={
                            "backgroundColor": "#eef4f7",
                            "border": "0",
                            "color": "#172033",
                            "fontWeight": "700",
                            "padding": "12px",
                        },
                        style_cell={
                            "backgroundColor": "#ffffff",
                            "border": "0",
                            "borderBottom": "1px solid #e6edf3",
                            "color": "#243447",
                            "fontFamily": "Arial, sans-serif",
                            "fontSize": "14px",
                            "height": "auto",
                            "maxWidth": "360px",
                            "minWidth": "92px",
                            "padding": "12px",
                            "textAlign": "left",
                            "whiteSpace": "normal",
                        },
                    ),
                ],
                style=CARD_STYLE,
            ),
            html.Section(
                [
                    html.H2("Ask the cricket logs", style={"margin": "0"}),
                    html.P("Answers are grounded in the retrieved match commentary below.", style=MUTED_STYLE),
                    html.Div(
                        [
                            dcc.Input(
                                id="chat-question",
                                type="text",
                                placeholder="e.g. What types of disputed decisions appear in the logs?",
                                style=INPUT_STYLE,
                            ),
                            html.Button("Ask", id="chat-button", n_clicks=0, style=BUTTON_STYLE),
                        ],
                        style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
                    ),
                    html.Div(
                            dcc.Markdown(
                                id="chat-answer",
                                children="",
                                className="chat-markdown",
                                link_target="_blank",
                            ),
                            style={
                                "backgroundColor": "#f7fafb",
                                "borderLeft": "4px solid #0f5d5e",
                                "lineHeight": "1.6",
                                "marginTop": "18px",
                                "minHeight": "24px",
                                "padding": "14px 16px",
                            },
                        ),
                    html.Div(
                        [
                            html.H3("Retrieved evidence", style={"fontSize": "17px", "margin": "24px 0 0"}),
                            html.Div(id="chat-sources"),
                        ]
                    ),
                ],
                style=CARD_STYLE,
            ),
        ],
        style=CONTENT_STYLE,
    ),
    style=PAGE_STYLE,
)


@app.callback(
    Output("search-results", "data"),
    Output("search-status", "children"),
    Input("search-button", "n_clicks"),
    State("search-query", "value"),
    prevent_initial_call=True,
)
def search_cricket_events(_, query):
    if not query or not query.strip():
        return [], "Enter a search query first."

    try:
        result = api_post("/api/search/", {"query": query.strip(), "top_k": 10, "filters": {}})
        results = result.get("results", [])
        return search_rows(results), f"{len(results)} matching event(s) found."
    except requests.RequestException:
        return [], "Search is unavailable."
    except (TypeError, ValueError):
        return [], "Search returned an unexpected response."


@app.callback(
    Output("chat-answer", "children"),
    Output("chat-sources", "children"),
    Input("chat-button", "n_clicks"),
    State("chat-question", "value"),
    prevent_initial_call=True,
)
def ask_cricket_question(_, question):
    if not question or not question.strip():
        return "Enter a question first.", ""

    try:
        result = api_post("/api/chat/", {"question": question.strip(), "top_k": 5})
        return display_value(result.get("answer"), "No answer returned."), source_cards(result.get("sources", []))
    except requests.RequestException:
        return "Chat is unavailable.", ""
    except (TypeError, ValueError):
        return "Chat returned an unexpected response.", ""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
