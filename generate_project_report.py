"""Generate the repository-grounded TripWeaver AI project report."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf" / "tripweaver-ai-project-report.pdf"

NAVY = colors.HexColor("#102A43")
BLUE = colors.HexColor("#1D72B8")
TEAL = colors.HexColor("#0B8F8C")
MINT = colors.HexColor("#E7F6F2")
SKY = colors.HexColor("#EAF4FB")
INK = colors.HexColor("#243B53")
MUTED = colors.HexColor("#627D98")
LINE = colors.HexColor("#D9E2EC")
WHITE = colors.white


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 1.25 * cm, A4[0] - doc.rightMargin, 1.25 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.82 * cm, "TripWeaver AI - General Project Report")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.82 * cm, f"Page {doc.page}")
    canvas.restoreState()


class Band(Flowable):
    def __init__(self, color, height=8):
        super().__init__()
        self.color, self.height = color, height

    def wrap(self, avail_width, avail_height):
        self._availWidth = avail_width
        return avail_width, self.height

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self._availWidth, self.height, stroke=0, fill=1)


class ArrowFlow(Flowable):
    def __init__(self, labels):
        super().__init__()
        self.labels = labels
        self.height = 66

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return avail_width, self.height

    def draw(self):
        c = self.canv
        n = len(self.labels)
        gap = 12
        box_w = (self.width - (n - 1) * gap) / n
        for i, label in enumerate(self.labels):
            x = i * (box_w + gap)
            c.setFillColor(SKY if i % 2 == 0 else MINT)
            c.setStrokeColor(colors.HexColor("#B9D6EA"))
            c.roundRect(x, 14, box_w, 36, 5, stroke=1, fill=1)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 7.5)
            words = label.split(" ")
            if len(words) > 1:
                c.drawCentredString(x + box_w / 2, 34, " ".join(words[:2]))
                c.drawCentredString(x + box_w / 2, 23, " ".join(words[2:]))
            else:
                c.drawCentredString(x + box_w / 2, 28, label)
            if i < n - 1:
                sx = x + box_w + 2
                c.setStrokeColor(TEAL)
                c.setFillColor(TEAL)
                c.line(sx, 32, sx + gap - 5, 32)
                c.line(sx + gap - 5, 32, sx + gap - 8, 35)
                c.line(sx + gap - 5, 32, sx + gap - 8, 29)


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=31, leading=37, textColor=WHITE, alignment=TA_LEFT, spaceAfter=10))
styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="Helvetica", fontSize=14, leading=20, textColor=colors.HexColor("#D9EAF7")))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=NAVY, spaceBefore=5, spaceAfter=10))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BLUE, spaceBefore=10, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.3, leading=14.2, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=11.5, textColor=INK))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=15, textColor=NAVY, backColor=MINT, borderColor=colors.HexColor("#A7DED5"), borderWidth=0.6, borderPadding=10, spaceBefore=6, spaceAfter=12))
styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=WHITE))
styles.add(ParagraphStyle(name="TableCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.7, leading=10.2, textColor=INK))


def p(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def heading(text):
    return [Band(TEAL, 4), Spacer(1, 8), p(text, "H1x")]


def bullets(items):
    return [p(f"- {item}", "Bodyx") for item in items]


def table(headers, rows, widths):
    data = [[p(h, "TableHead") for h in headers]]
    data += [[p(cell, "TableCell") for cell in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F7FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=1.55*cm, rightMargin=1.55*cm, topMargin=1.5*cm, bottomMargin=1.65*cm)
    doc.addPageTemplates([__import__("reportlab.platypus", fromlist=["PageTemplate"]).PageTemplate(id="main", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")], onPage=footer)])
    s = []

    # Cover
    s += [Spacer(1, 1.7*cm)]
    cover = Table([[p("TRIPWEAVER AI", "CoverTitle")], [p("Multi-Agent Travel Orchestration Platform", "CoverSub")], [Spacer(1, 0.4*cm)], [p("General Structured Project Report", "CoverSub")], [Spacer(1, 1.6*cm)], [p("Repository assessment based on the implementation, documentation, configuration, and automated tests.<br/><br/>Prepared: 24 October 2026<br/>Version assessed: 2.0.0", "CoverSub")]], colWidths=[doc.width])
    cover.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("BOX", (0, 0), (-1, -1), 0, NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 28), ("RIGHTPADDING", (0, 0), (-1, -1), 28), ("TOPPADDING", (0, 0), (-1, -1), 26), ("BOTTOMPADDING", (0, 0), (-1, -1), 26)]))
    s += [cover, Spacer(1, 1.5*cm), p("Purpose", "H2x"), p("This report presents TripWeaver AI as it is implemented in the repository: its purpose, structure, workflow, technical components, interfaces, quality checks, operational constraints, and recommended next steps.", "Bodyx"), PageBreak()]

    # Executive summary
    s += heading("1. Executive Summary")
    s += [p("TripWeaver AI is a web-based travel-planning assistant that converts a plain-language request into a reviewable itinerary. It combines a FastAPI application, a LangGraph workflow, Groq-based language-model calls, Model Context Protocol (MCP) research integrations, and PostgreSQL-backed state persistence.")]
    s += [p("The core product choice is a human-in-the-loop lifecycle: the system creates a draft, pauses, and only produces a final itinerary after the user approves it or supplies revision feedback. This gives the user a decision point before the final response is generated and enables a revision path without losing workflow state.", "Callout")]
    s += [p("The platform is a planning and research tool rather than a booking system. It does not reserve travel, process payments, or guarantee availability, pricing, visa eligibility, safety, or recommendations.")]
    s += [p("<b>Assessment scope.</b> This report is repository-grounded. It reflects source code, README guidance, Docker configuration, and the automated test collection available at the time of review. No live provider keys, production database, external booking flow, or deployment environment were exercised.")]
    s += [p("Key characteristics", "H2x")]
    s += bullets(["Adaptive specialist selection: the supervisor may choose flight, hotel, weather, and budget specialists, while itinerary creation is always included.", "Durable approval workflow: LangGraph checkpoints are persisted by thread ID in PostgreSQL so paused work can resume.", "Graceful research degradation: flight, hotel, and weather integrations return clearly labelled fallback information when unavailable.", "Browser-first experience: a Jinja2/vanilla JavaScript single-page interface renders Markdown, stores the current thread ID, supports copy, and exports travel plans to PDF."])
    s += [PageBreak()]

    # Contents + objectives
    s += heading("2. Project Context and Scope")
    s += [p("<b>Problem addressed.</b> Travel planning typically requires reconciling destinations, trip duration, spending limits, transport, accommodation, weather, and daily activities. TripWeaver AI organizes this work through a supervised agent workflow that extracts constraints, gathers specialist context, and synthesizes a day-by-day draft.")]
    s += [p("<b>Primary users.</b> Individual travelers who want a structured initial itinerary and prefer to review or request changes before receiving the final version.")]
    s += [p("In scope", "H2x"), *bullets(["Natural-language travel queries and constraint extraction.", "Research-oriented guidance for flights, hotels, weather, budget, and itinerary assembly.", "Draft review, approval, and revision feedback.", "Persisted LangGraph workflow state and a browser interface."])]
    s += [p("Out of scope", "H2x"), *bullets(["Reservations, ticket issuance, hotel booking, and payment handling.", "Real-time price, availability, visa, safety, or legal guarantees.", "Authentication, role-based access, rate limiting, and multi-tenant user isolation in the current implementation."])]
    s += [p("Report outline", "H2x"), table(["Section", "Focus"], [["3", "Architecture and request lifecycle"], ["4", "Agent orchestration and external integrations"], ["5", "Application components and interfaces"], ["6", "Data, safety, operations, and deployment"], ["7", "Testing, limitations, and recommendations"]], [2.2*cm, 13.7*cm]), PageBreak()]

    # Architecture
    s += heading("3. Architecture and Request Lifecycle")
    s += [p("TripWeaver AI uses a layered architecture. The browser sends JSON over HTTP to FastAPI; FastAPI runs the synchronous LangGraph workflow in a thread pool; the graph invokes the selected specialist nodes; MCP helpers call external research providers; PostgreSQL stores checkpoints required for the approval pause and resume cycle.")]
    s += [p("High-level request path", "H2x"), ArrowFlow(["Browser UI", "FastAPI API", "LangGraph supervisor", "Specialist agents", "Draft + review", "Final plan"]), Spacer(1, 3)]
    s += [table(["Layer", "Implementation", "Role"], [["Presentation", "Jinja2 template, CSS, vanilla JavaScript", "Collect request, render Markdown, display workflow status, retain thread ID in localStorage, and trigger client-side PDF export."], ["API", "FastAPI in app.py", "Exposes the page, health response, planning endpoint, and approval endpoint. Converts errors to JSON responses."], ["Orchestration", "LangGraph StateGraph in backend.py", "Routes from supervisor to selected agents, pauses with interrupt(), and resumes the same thread after review."], ["Research", "MCP helpers plus provider APIs", "Retrieves flight context, hotel/neighbourhood research, and current weather/forecast data."], ["Persistence", "PostgreSQL with PostgresSaver", "Stores checkpoint tables and graph state keyed by thread ID."]], [2.35*cm, 4.5*cm, 9.05*cm])]
    s += [p("State transition", "H2x"), p("A normal request follows: <b>input -> guardrail -> supervisor -> selected specialists -> itinerary draft -> human approval interrupt -> final response</b>. A clearly blocked request ends immediately after the guardrail. Specialist execution follows a fixed possible order (flight, hotel, weather, budget, itinerary), but the supervisor can omit unnecessary specialists.")]
    s += [PageBreak()]

    # Agents
    s += heading("4. Agent Orchestration and Integrations")
    s += [p("The supervisor first runs the input guardrail and then asks the model to return a strict JSON routing decision. It extracts travel constraints such as destination, origin, duration, budget, style, and special preferences. If routing output cannot be parsed, the implementation falls back to the full specialist order so the user can still receive a plan.")]
    s += [table(["Node / integration", "Responsibility", "Failure behavior"], [["Input guardrail", "Allows travel-oriented requests and blocks clearly unrelated, harmful, or illegal requests.", "Fails open when the LLM call or JSON parse fails; this improves usability but is not a sufficient production safety boundary."], ["Flight agent", "Provides airport/airline context, likely routes, duration estimates, and booking advice using AviationStack MCP.", "Returns an unavailable message; graph continues."], ["Hotel agent", "Provides accommodation and neighbourhood research through Tavily MCP.", "Produces clearly labelled non-live guidance; graph continues."], ["Weather agent", "Uses a local FastMCP server that calls OpenWeather for current conditions and a short forecast.", "Returns seasonal/general guidance when unavailable; graph continues."], ["Budget agent", "Builds cost categories, risks, savings ideas, and feasibility guidance using Groq.", "Unhandled model error reaches the API."], ["Itinerary agent", "Creates the reviewable day-by-day itinerary. It is always selected.", "Unhandled model error reaches the API."], ["Final agent", "Polishes an approved draft or applies user feedback after the interrupt is resumed.", "Unhandled model error reaches the API."]], [3.0*cm, 7.1*cm, 5.8*cm])]
    s += [p("Duration handling", "H2x"), p("The workflow identifies explicit trip durations from one to 30 days, including worded examples such as “one week” and “two weeks.” When a duration is found, itinerary and final-response prompts require a separate section for every requested day and instruct the model not to omit, combine, or summarize days.")]
    s += [PageBreak()]

    # Product and API
    s += heading("5. Application Components and Interfaces")
    s += [p("The repository separates web/API concerns from workflow logic. app.py owns FastAPI setup, static assets, template rendering, Pydantic request models, and endpoint-level error handling. backend.py owns the LangGraph state, agents, routing, interrupt handling, serialization, and persistence setup.")]
    s += [p("API contract", "H2x"), table(["Endpoint", "Purpose", "Important behavior"], [["GET /", "Serves the TripMate AI browser application.", "Renders templates/index.html with static CSS and JavaScript."], ["GET /health", "Basic process health response.", "Returns status and advertised features only; it does not validate database or third-party connectivity."], ["POST /api/travel", "Starts a workflow.", "Accepts message and optional thread_id. A draft normally returns requires_approval: true with the itinerary and approval request."], ["POST /api/travel/approve", "Resumes a paused workflow.", "Requires non-empty thread_id and an approved boolean. Rejections require non-whitespace feedback."], ["GET /favicon.ico", "Provides a lightweight favicon response.", "Supports browser requests without adding a separate icon asset."]], [3.0*cm, 4.2*cm, 8.7*cm])]
    s += [p("Browser workflow", "H2x"), *bullets(["Uses fetch() with JSON payloads for planning and approval actions.", "Stores travel_thread_id in localStorage so the same client can resume a paused graph.", "Prevents a new request while a draft is awaiting approval.", "Renders model output with marked.js, supports result copying, and creates an A4 download using html2pdf.js.", "Uses public CDNs for Markdown rendering and client-side PDF export; those functions need browser CDN access."])]
    s += [p("Repository structure", "H2x"), table(["Path", "Contribution"], [["app.py", "FastAPI application and public routes."], ["backend.py", "TravelState, LangGraph agents/routing, checkpoint lifecycle, result serialization."], ["mcp_client.py", "Tavily, AviationStack, and local weather MCP client helpers."], ["custom_weather_mcp.py", "FastMCP stdio server for OpenWeather current weather and forecast."], ["templates/ and static/", "Single-page UI and its presentation/client logic."], ["tests/", "API, workflow/unit, weather-MCP, and utility coverage."], ["Dockerfile", "Python 3.11-slim container image running Uvicorn on port 8000."]], [4.0*cm, 11.9*cm]), PageBreak()]

    # Data and safety
    s += heading("6. Data, Safety, and Operations")
    s += [p("<b>Persisted state.</b> A graph checkpoint is stored in PostgreSQL using a thread ID. The browser retains that ID locally, while PostgreSQL retains the checkpoint that makes a paused approval workflow resumable. This means both the thread identifier and the checkpoint store need to remain available between draft and approval.")]
    s += [p("<b>Configuration.</b> GROQ_API_KEY and DATABASE_URL are mandatory when the backend loads. TAVILY_API_KEY, AVIATION_STACK_API_KEY (or compatibility name AVIATIONSTACK_API_KEY), and OPENWEATHER_API_KEY are required only when their corresponding specialist executes. GROQ_MODEL is optional and defaults to openai/gpt-oss-120b.")]
    s += [p("Deployment", "H2x"), table(["Area", "Current implementation", "Operational note"], [["Runtime", "Python 3.11; FastAPI/Uvicorn.", "Run locally with uvicorn app:app --reload."], ["Container", "python:3.11-slim; installs requirements; exposes port 8000.", "The stock Dockerfile does not install uv/uvx, so AviationStack MCP calls can fail while other paths continue."], ["Database", "PostgreSQL and langgraph-checkpoint-postgres.", "Startup creates checkpoint tables and appends sslmode=require if absent from the configured URL."], ["Provider network", "Groq, Tavily, AviationStack, OpenWeather.", "Container needs network access to all selected services and PostgreSQL."], ["Secrets", ".env is documented and ignored by Git.", "Production should use a managed secret store rather than a local environment file."]], [2.7*cm, 6.1*cm, 7.1*cm])]
    s += [p("Safety position", "H2x"), p("The initial LLM guardrail is useful as a conversational routing control but intentionally fails open on model/JSON problems. The README appropriately notes that this is not a production safety boundary. An internet-facing deployment needs deterministic validation and policy enforcement in addition to the model-based check.", "Callout")]
    s += [PageBreak()]

    # Quality limitations recommendations
    s += heading("7. Quality Assessment, Limitations, and Recommendations")
    s += [p("<b>Automated verification.</b> The repository test collection contains 190 tests in the available environment. They cover FastAPI routes and request models, static/template expectations, workflow helpers and routing, guardrail/supervisor behavior, duration preservation, weather MCP behaviour, MCP environment helpers, and configuration rules. Tests mock external services and are not intended to perform live provider or database calls.")]
    s += [p("<b>Recommended verification command.</b> The documented approach runs backend units, weather/utility tests, and API tests in that order, followed by Python compilation of the key modules. This ordering avoids a test backend stub affecting the other test modules.")]
    s += [p("Known limitations", "H2x"), table(["Area", "Observed limitation", "Impact"], [["Live information", "Provider data may be unavailable, stale, plan-dependent, or only context-level.", "Users must validate prices, availability, operating hours, visas, and local guidance with official sources."], ["Forecast", "The local weather server returns the first five 3-hour OpenWeather forecast entries, not a complete multi-day forecast.", "Weather planning should be framed as short-term guidance."], ["Security", "No authentication, rate limiting, formal user isolation, or production-grade policy gateway.", "Not ready for public multi-user exposure without additional controls."], ["Reliability", "Some LLM failures for budget, itinerary, or final response are unhandled.", "API can return 500 despite graceful handling of certain research integrations."], ["Container parity", "uv/uvx absent from the supplied Docker image.", "Flight MCP integration is not container-ready out of the box."]], [2.55*cm, 7.0*cm, 6.35*cm])]
    s += [p("Recommended next steps", "H2x"), *bullets(["Add authentication, authorization, rate limiting, request tracing, structured logs, and per-user thread ownership before public deployment.", "Add deterministic server-side travel-domain validation and content policy checks; do not rely on a fail-open LLM guardrail as the only control.", "Install and pin uv/uvx in Docker, then add a container-level smoke test for the AviationStack path.", "Define timeouts, retries, circuit breakers, and user-facing status for all LLM and MCP providers.", "Introduce integration tests with controlled test credentials or contract mocks for checkpoint persistence and MCP result schemas.", "Document retention, deletion, and privacy policy for persisted itinerary and user-request data."])]
    s += [Spacer(1, 8), p("Conclusion", "H2x"), p("TripWeaver AI has a clear, coherent foundation for an AI-assisted travel-planning experience: specialised research, orchestrated synthesis, and an explicit review step. The strongest next investment is operational hardening - identity, deterministic safeguards, observability, and deployment parity - so the design can move from a capable project implementation toward a dependable public service.")]

    doc.build(s)
    print(OUT)


if __name__ == "__main__":
    build()
