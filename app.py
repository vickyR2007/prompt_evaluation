import base64
import json
import os
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
st.set_page_config(page_title="Prompt Evaluation Studio", page_icon="🪄", layout="wide")

CRITERIA = ["Role", "Goal", "Context", "Constraints", "Format", "Style"]
SCENARIOS = {
    "Business": {
        "Beginner": "Draft a concise professional email to a client explaining a one-day project delay.",
        "Intermediate": "Create a decision brief comparing two customer support platforms for a 25-person team. Address cost, integrations, migration, and risks.",
        "Advanced": "Design a 90-day market-entry plan for a mid-sized company expanding into a new region. Include assumptions, workstreams, owners, KPIs, dependencies, and contingency triggers.",
    },
    "HR": {
        "Beginner": "Write a welcoming first-day message for a new employee joining a remote team.",
        "Intermediate": "Create structured interview questions for a product manager role, with a consistent scoring rubric and guidance to reduce bias.",
        "Advanced": "Propose a workforce planning framework for a company anticipating a 20% shift in skill demand over two years. Include data inputs, governance, equity safeguards, and measurable outcomes.",
    },
    "Marketing": {
        "Beginner": "Write three social media captions announcing a reusable water bottle.",
        "Intermediate": "Develop a launch campaign for a new budgeting app aimed at early-career professionals. Specify audience, channel mix, messages, and metrics.",
        "Advanced": "Build an experiment plan to improve trial-to-paid conversion for a subscription product. Include hypotheses, segmentation, sample-size considerations, guardrails, and decision rules.",
    },
    "Data Analytics": {
        "Beginner": "Explain a monthly sales chart to a non-technical audience in plain language.",
        "Intermediate": "Analyze a decline in weekly active users using event data. Outline the diagnostic steps, metrics, and likely confounders before recommending actions.",
        "Advanced": "Design a reproducible analysis to estimate the causal impact of a pricing change on revenue and retention. State identification assumptions, robustness checks, and limitations.",
    },
    "Software Development": {
        "Beginner": "Write a Python function that validates an email address and include a few examples.",
        "Intermediate": "Design a REST API endpoint for creating user accounts. Specify validation, error responses, security considerations, and tests.",
        "Advanced": "Propose a migration from a monolith to independently deployable services for a high-traffic product. Include sequencing, observability, rollback strategy, data consistency, and risk controls.",
    },
}

if "evaluations" not in st.session_state:
    st.session_state.evaluations = []
if "prompt_draft" not in st.session_state:
    st.session_state.prompt_draft = ""

st.markdown("""
<style>
:root { --ink:#eef1f8; --muted:#9ba7bd; --line:#252c3a; --blue:#9aa7ff; --mint:#37d9b2; --panel:#111720; --text-color:#eef1f8; --background-color:#080a0f; --secondary-background-color:#111720; --primary-color:#8794ff; }
.stApp { background:radial-gradient(ellipse at 12% 5%,#123f50 0,transparent 34%),radial-gradient(ellipse at 88% 12%,#352254 0,transparent 32%),radial-gradient(ellipse at 50% 100%,#15264a 0,transparent 48%),#080a12; color:var(--ink); }
.stApp::before { content:""; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:.22; background-image:linear-gradient(rgba(122,157,255,.12) 1px,transparent 1px),linear-gradient(90deg,rgba(122,157,255,.12) 1px,transparent 1px),radial-gradient(circle at 1px 1px,rgba(85,224,255,.42) 1px,transparent 1.7px); background-size:56px 56px,56px 56px,56px 56px; mask-image:radial-gradient(ellipse at 50% 38%,#000 8%,transparent 82%); }
.block-container { position:relative; z-index:1; max-width:1440px; padding:1.8rem 2rem 4rem; }
[data-testid="stSidebar"] { position:relative; z-index:1; background:linear-gradient(180deg,#0c151e,#111321); border-right:1px solid #2b3b50; box-shadow:8px 0 35px #0003; }
[data-testid="stSidebar"] * { color:#e8ecf5; }
.hero { position:relative; overflow:hidden; padding:2rem 2.3rem; background:linear-gradient(115deg,#0c2530 0%,#141c32 52%,#2b1c46 100%); border:1px solid #3a4d68; color:white; border-radius:26px; margin:0 0 1.4rem; box-shadow:0 20px 60px #0007,0 0 55px #5369d51c; }
.hero:after { content:""; position:absolute; z-index:0; inset:0; background:radial-gradient(ellipse at 78% 50%,#a855f733,transparent 35%),radial-gradient(ellipse at 52% 95%,#22d3ee18,transparent 40%); pointer-events:none; }
.hero > .eyebrow, .hero > h1, .hero > p { position:relative; z-index:2; }
.hero-target { position:absolute; z-index:1; width:clamp(105px,14vw,180px); height:auto; object-fit:contain; right:5%; top:50%; transform:translateY(-50%); filter:drop-shadow(0 12px 24px #0008); }
@media (max-width:760px) { .top-badge { display:none; } .hero-target { width:90px; right:1rem; opacity:.8; } .hero h1 { max-width:72%; font-size:1.8rem; } .hero p { max-width:75%; } }
.eyebrow { color:#c5d3ff; text-transform:uppercase; letter-spacing:.18em; font-size:.72rem; font-weight:800; }
.hero h1 { color:white; font-size:2.3rem; margin:.45rem 0 .3rem; letter-spacing:-.045em; }
.hero p { color:#dce5ff; margin:0; font-size:1rem; }
.top-badge { position:absolute; right:2rem; top:2rem; color:#e5ebff; border:1px solid #ffffff35; background:#ffffff12; padding:.55rem .85rem; border-radius:999px; font-size:.8rem; z-index:2; }
.kicker { color:#a6b0ff; text-transform:uppercase; font-size:.7rem; font-weight:850; letter-spacing:.16em; margin:0 0 .45rem; }
.surface { background:linear-gradient(145deg,rgba(20,29,43,.96),rgba(13,19,29,.98)); border:1px solid #2e4056; border-radius:20px; padding:1.35rem 1.45rem; box-shadow:0 12px 34px #0005, inset 0 1px 0 #ffffff08; backdrop-filter:blur(12px); }
[data-testid="stMetric"] { transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease; }
[data-testid="stMetric"]:hover { transform:translateY(-3px); border-color:#526b8c; box-shadow:0 14px 32px #0006,0 0 24px #42d6f315; }
.challenge { min-height:148px; display:flex; flex-direction:column; justify-content:center; }
.challenge-text { color:#dce3f1; font-size:1.08rem; line-height:1.65; }
.pill { display:inline-block; border:1px solid #e3e8f5; color:#55647f; background:#f7f9ff; border-radius:999px; padding:.3rem .7rem; font-size:.77rem; margin:0 .3rem .3rem 0; }
[data-testid="stMetric"] { background:#111720; border:1px solid #252c3a; padding:15px 17px; border-radius:17px; box-shadow:0 6px 20px #0004; }
[data-testid="stMetricValue"] { color:#f2f4fb !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricDelta"] { color:#a6b0c3 !important; }
[data-testid="stRadio"] > div { gap:.55rem; }
[data-testid="stRadio"] label { background:linear-gradient(135deg,#111a26,#141728); border:1px solid #304156; border-radius:12px; color:#e4e9f5; padding:.55rem .8rem; transition:all .18s ease; }
[data-testid="stRadio"] label:hover { border-color:#7785ea; background:#20263a; box-shadow:0 0 0 1px #7785ea33; }
.stButton > button[kind="primary"] { border:0; border-radius:13px; background:linear-gradient(110deg,#087e9b,#5264df 55%,#8654cf); font-weight:750; padding:.78rem 1.1rem; box-shadow:0 9px 26px #247ae044,0 0 22px #3cd7e51c; }
.stButton > button:not([kind="primary"]) { border-radius:11px; border-color:#343d50; color:#e0e5f1; background:#1b2432; border-color:#465578; }
.stTextArea { background:#111720; border:1px solid #2b3445; border-radius:17px; padding:.8rem; box-shadow:0 6px 20px #0004; }
.stProgress > div > div { background:linear-gradient(90deg,#26b99b,#6574e8); }
textarea { border-radius:15px !important; }
[data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:#111720; color:#eef1f8; }
[data-baseweb="tab-list"] { gap:.45rem; }
button[data-baseweb="tab"] { background:#111720; color:#cbd3e3; border:1px solid #293142; border-radius:12px 12px 0 0; padding:.65rem 1rem; }
hr { border-color:var(--line); }
[data-testid="stAppViewContainer"], [data-testid="stHeader"] { background:transparent; color:#eef1f8; }
.stTextArea textarea, .stTextInput input { background:#0c1017 !important; color:#eef1f8 !important; border:1px solid #30394b !important; border-radius:12px !important; }
.stTextArea textarea::placeholder, .stTextInput input::placeholder { color:#99a6bd !important; }
[data-baseweb="select"] > div { background:#111720; border-color:#30394b; color:#eef1f8; }
[data-baseweb="select"] * { color:#eef1f8; }
[data-testid="stProgress"] > div { background:#252d3b; }
.stProgress > div > div { background:linear-gradient(90deg,#28d9ca,#548dff 55%,#bb69ff); }
[data-testid="stExpander"] { border:1px solid #293142; border-radius:14px; background:#111720; color:#eef1f8; }
button[data-baseweb="tab"][aria-selected="true"] { background:#1c2232; color:#fff; border-color:#6877e9; }
[data-testid="stAlert"] { background:#151c27; border-color:#30394b; color:#e7ebf5; }
[data-testid="stCaptionContainer"] { color:#b1bdd1; }
</style>
""", unsafe_allow_html=True)
with open("assets/prompt_target.png", "rb") as target_file:
    target_image = base64.b64encode(target_file.read()).decode("ascii")
st.markdown(f'<div class="hero"><div class="eyebrow">✦ GROQ POWERED PROMPT LAB</div><div class="top-badge">⚡ Practice mode · Feedback in seconds</div><h1>Make every prompt count.</h1><p>Take a real-world challenge, shape your instructions, and see what makes them stronger.</p><img class="hero-target" src="data:image/png;base64,{target_image}" alt="Arrow hitting a target"></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🪄 Prompt Lab")
    st.caption("Tune the evaluator and see your session activity.")
    model = st.text_input("Groq model", value=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), help="Must be a model available to your Groq account.")
    st.divider()
    st.markdown("**What gets evaluated?**")
    for label, icon in [("Role", "🎭"), ("Goal", "🎯"), ("Context", "🗺️"), ("Constraints", "🧱"), ("Format", "📐"), ("Style", "🎨")]:
        st.markdown(f"{icon} &nbsp; {label}")
    st.divider()
    st.metric("Prompts evaluated", len(st.session_state.evaluations))
    if st.session_state.evaluations:
        best = max(e["overall"] for e in st.session_state.evaluations)
        st.metric("Personal best", f"{best}/100")

domain_icons = {"All domains":"🌐", "Business":"💼", "HR":"🧑‍🤝‍🧑", "Marketing":"📣", "Data Analytics":"📊", "Software Development":"💻"}
st.markdown('<div class="kicker">STEP 1  /  PICK A CHALLENGE</div>', unsafe_allow_html=True)
domain_labels = [f"{domain_icons[name]}  {name}" for name in domain_icons]
selected_label = st.radio("Choose a domain", domain_labels, horizontal=True, label_visibility="collapsed", key="domain_choice")
domain = selected_label.split("  ", 1)[1]
level = st.radio("Choose difficulty", ["Beginner", "Intermediate", "Advanced"], horizontal=True, key="difficulty_choice", format_func=lambda x: {"Beginner":"🌱 Beginner", "Intermediate":"🚀 Intermediate", "Advanced":"🏆 Advanced"}[x])
ALL_DOMAIN_SCENARIOS = {
    "Beginner": "Create a simple launch plan for a reusable water bottle. Include a short business goal, one marketing message, a basic success metric, an HR or customer support consideration, and one software or operations need.",
    "Intermediate": "Plan the rollout of a new employee onboarding platform for a growing company. Cover business goals, HR workflows, employee communications, success metrics and data, and software integration requirements.",
    "Advanced": "Design a cross-functional plan for expanding a digital subscription service into a new region. Integrate business strategy, hiring and HR operations, marketing, data measurement, and software architecture. Include assumptions, owners, KPIs, risks, dependencies, and rollout stages.",
}
if domain == "All domains":
    challenge_choices = ["All domains"] + list(SCENARIOS)
    challenge_domain = st.selectbox(
        "Choose a challenge",
        challenge_choices,
        format_func=lambda name: f"{domain_icons[name]}  {name}",
        key="all_domain_challenge",
    )
else:
    challenge_domain = domain
if challenge_domain == "All domains":
    scenario = ALL_DOMAIN_SCENARIOS[level]
else:
    scenario = SCENARIOS[challenge_domain][level]

brief_left, brief_right = st.columns([4,1])
with brief_left:
    st.markdown('<div class="surface challenge"><div class="kicker">TASK BRIEF</div><div class="challenge-text">' + scenario + '</div></div>', unsafe_allow_html=True)
with brief_right:
    st.markdown('<div class="surface challenge" style="text-align:center"><div style="font-size:2rem">' + domain_icons[challenge_domain] + '</div><b>' + challenge_domain + '</b><div style="color:#71809a;font-size:.85rem;margin-top:.3rem">' + level + ' challenge</div></div>', unsafe_allow_html=True)

st.markdown('<div style="height:1.2rem"></div><div class="kicker">STEP 2  /  WRITE YOUR PROMPT</div>', unsafe_allow_html=True)
editor, coach = st.columns([2.15, .85], gap="large")
with editor:
    st.markdown('<div class="surface"><b>✍️ Prompt editor</b><div style="color:#71809a;font-size:.85rem;margin:.25rem 0 0">Be specific. You can improve your draft as many times as you like.</div></div>', unsafe_allow_html=True)
    if st.button("＋ Insert a guided prompt framework", use_container_width=True):
        st.session_state.prompt_draft = "You are [role/expertise].\n\nYour goal is to [specific outcome].\n\nContext: [relevant background and audience].\n\nConstraints: [requirements, limits, and what to avoid].\n\nFormat: [structure, length, and required sections].\n\nStyle: [tone and level of detail]."
    prompt_text = st.text_area("Your prompt", height=245, key="prompt_draft", label_visibility="collapsed", placeholder="Start with who the AI should be, then explain the task, context, rules, output format, and tone…")
    st.caption(f"✍️  {len(prompt_text):,} characters  ·  {len(prompt_text.split()):,} words")

lower = prompt_text.lower()
checks = {
    "Role": any(x in lower for x in ["you are", "act as", "as a ", "role:"]),
    "Goal": any(x in lower for x in ["write", "create", "draft", "analyze", "design", "explain", "goal", "task"]),
    "Context": any(x in lower for x in ["context", "background", "audience", "for a ", "given "]),
    "Constraints": any(x in lower for x in ["must", "do not", "don't", "avoid", "limit", "constraint"]),
    "Format": any(x in lower for x in ["format", "bullet", "table", "json", "sections", "output as"]),
    "Style": any(x in lower for x in ["tone", "style", "concise", "friendly", "professional", "formal"]),
}
with coach:
    st.markdown('<div class="surface"><div class="kicker">Live prompt coach</div><b>Prompt checklist</b><div style="color:#71809a;font-size:.83rem;margin:.25rem 0 0">A quick checklist updates as you type.</div></div>', unsafe_allow_html=True)
    complete = sum(checks.values())
    st.progress(complete / len(CRITERIA), text=f"{complete} of 6 covered")
    for item in CRITERIA:
        st.markdown(f"{'✅' if checks[item] else '○'} &nbsp; **{item}**")
    st.caption("Check each element before you submit. The AI evaluator will score the detail and clarity.")
def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


ROLE_BY_DOMAIN = {
    "All domains": "a cross-functional team spanning business, HR, marketing, data analytics, and software development",
    "Business": "a senior business advisor",
    "HR": "an experienced HR partner who values fairness and inclusion",
    "Marketing": "a senior marketing strategist",
    "Data Analytics": "a senior data analyst who distinguishes correlation from causation",
    "Software Development": "a senior software engineer focused on secure, maintainable solutions",
}


def build_user_grounded_prompt(user_prompt, scenario_text, selected_domain):
    role = ROLE_BY_DOMAIN.get(selected_domain, "a knowledgeable expert for this task")
    return (
        f"You are {role}.\n\n"
        "Goal: Complete the user's task while preserving its original subject, purpose, and requested deliverable.\n\n"
        f"Task from the user's submitted prompt (keep this as the source of truth):\n{user_prompt.strip()}\n\n"
        "Context: Use the user's stated audience and background. The practice scenario below is evaluation context only; "
        "use it only where it fits the user's task. Do not replace the user's task with the scenario.\n"
        f"Practice scenario: {scenario_text}\n\n"
        "Constraints: Do not change the central task or add unsupported facts. State assumptions or use placeholders for missing information. "
        "Make the instructions specific and actionable.\n\n"
        "Format: Return the deliverable requested in the user's original task. Use clear headings or bullets when useful.\n\n"
        "Style: Be clear, concise, and appropriate for the audience and subject."
    )


def evaluate_prompt(user_prompt, scenario_text, selected_model, selected_domain):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "gsk_your_groq_api_key_here":
        raise ValueError("Add your Groq API key to the .env file as GROQ_API_KEY=gsk_… and restart the app.")
    client = Groq(api_key=api_key)
    schema = {
        "scores": {criterion.lower(): "integer from 0 to 10" for criterion in CRITERIA},
        "feedback": {criterion.lower(): "specific explanation of this score" for criterion in CRITERIA},
        "strengths": ["specific strength"],
        "missing_components": ["component or detail missing"],
        "suggestions": ["actionable improvement"],
        "optimized_prompt": "complete improved prompt that preserves the user's intent",
        "summary": "short overall assessment",
    }
    messages = [
        {"role": "system", "content": "You are a rigorous, constructive prompt-engineering evaluator. Evaluate only the submitted prompt, using the selected practice scenario as the benchmark. Score each criterion independently from 0 (absent) to 10 (excellent and specific). Keep feedback practical. Return ONLY valid JSON. The optimized_prompt must improve the USER SUBMITTED PROMPT while preserving its core task, subject, purpose, audience, and deliverable. Treat the submitted prompt as the source of truth. The scenario is only a benchmark for feedback: never replace the user task with the scenario. If the prompt does not match the scenario, preserve and improve the user task anyway, and clearly note the mismatch in feedback or missing_components. Do not invent facts; use clear placeholders where needed."},
        {"role": "user", "content": f"Practice scenario for evaluating alignment:\n{scenario_text}\n\nUSER SUBMITTED PROMPT (this is the task to preserve and improve):\n{user_prompt}\n\nFor optimized_prompt, keep the user task, subject, and requested output. Add or clarify role, goal, context, constraints, format, and style without changing what the user asked for. Use scenario details only when relevant to the submitted prompt. If the prompt is off-scenario, improve the submitted task as written and mention the mismatch in feedback. Return JSON with this structure (all six score keys must be present):\n{json.dumps(schema, ensure_ascii=False)}"},
    ]
    response = client.chat.completions.create(
        model=selected_model, messages=messages, temperature=0.2,
        response_format={"type": "json_object"},
    )
    data = parse_json(response.choices[0].message.content)
    scores = data.get("scores", {})
    normalized = {}
    for criterion in CRITERIA:
        value = scores.get(criterion.lower(), scores.get(criterion, 0))
        normalized[criterion] = max(0, min(10, int(round(float(value)))))
    data["scores"] = normalized
    optimized = str(data.get("optimized_prompt", "")).strip()
    if not optimized or user_prompt.strip().casefold() not in optimized.casefold():
        data["optimized_prompt"] = build_user_grounded_prompt(user_prompt, scenario_text, selected_domain)
    else:
        data["optimized_prompt"] = optimized
    for key in ("strengths", "missing_components", "suggestions"):
        if not isinstance(data.get(key), list):
            data[key] = []
    if not isinstance(data.get("feedback"), dict):
        data["feedback"] = {}
    return data


def load_optimized_prompt():
    st.session_state.prompt_draft = st.session_state.evaluations[-1].get("optimized_prompt", "")


if "evaluations" not in st.session_state:
    st.session_state.evaluations = []

st.markdown("<div class=\"kicker\">STEP 3  /  GET YOUR EVALUATION</div>", unsafe_allow_html=True)
if st.button("✦  Evaluate my prompt", type="primary", use_container_width=True, disabled=not prompt_text.strip()):
    try:
        with st.spinner("Evaluating your prompt with Groq…"):
            result = evaluate_prompt(prompt_text.strip(), scenario, model.strip(), challenge_domain)
        result["overall"] = round(sum(result["scores"].values()) / 60 * 100)
        result["submitted_prompt"] = prompt_text.strip()
        result["scenario"] = scenario
        result["domain"] = challenge_domain
        result["level"] = level
        result["created_at"] = datetime.now().strftime("%H:%M:%S")
        st.session_state.evaluations.append(result)
    except Exception as exc:
        st.error(f"Evaluation failed: {exc}")

if st.session_state.evaluations:
    current = st.session_state.evaluations[-1]
    st.divider()
    st.markdown('<div class="kicker">Your latest results</div>', unsafe_allow_html=True)
    st.subheader(current.get("summary", "Your prompt evaluation"))
    previous = st.session_state.evaluations[-2] if len(st.session_state.evaluations) > 1 else None
    delta = current["overall"] - previous["overall"] if previous else None
    cols = st.columns(4)
    cols[0].metric("Overall score", f"{current['overall']}/100", f"{delta:+d} points vs last" if delta is not None else "First attempt")
    cols[1].metric("Strongest component", max(current["scores"], key=current["scores"].get), f"{max(current['scores'].values())}/10")
    cols[2].metric("Focus next", min(current["scores"], key=current["scores"].get), f"{min(current['scores'].values())}/10")
    cols[3].metric("Attempts this session", len(st.session_state.evaluations))

    result_tabs = st.tabs(["📊 Score profile", "🧩 Feedback", "✨ Improve prompt", "📈 Progress"])
    with result_tabs[0]:
        gauge_col, radar_col, right = st.columns([.82, 1, 1.1])
        with gauge_col:
            gauge = go.Figure(go.Indicator(mode="gauge+number", value=current["overall"], number={"suffix":"/100", "font":{"size":34,"color":"#eef1f8"}}, title={"text":"Prompt score", "font":{"size":16}}, gauge={"axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#d8deeb"},"bar":{"color":"#5267d8","thickness":.27},"bgcolor":"#111720","borderwidth":0,"steps":[{"range":[0,40],"color":"#302127"},{"range":[40,70],"color":"#302b1e"},{"range":[70,100],"color":"#19332f"}],"threshold":{"line":{"color":"#dce3f1","width":3},"thickness":.8,"value":current["overall"]}}))
            gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=15,r=15,t=60,b=15), font=dict(color="#dce3f1"))
            st.plotly_chart(gauge, use_container_width=True)
        with radar_col:
            radar = go.Figure(go.Scatterpolar(r=[current["scores"][c] for c in CRITERIA], theta=CRITERIA, fill="toself", name="Your prompt", line_color="#5267d8", fillcolor="rgba(82,103,216,.18)"))
            radar.update_layout(title="Prompt component profile", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", polar=dict(bgcolor="#111720", radialaxis=dict(visible=True, range=[0, 10], tickvals=[0, 2, 4, 6, 8, 10], gridcolor="#30394b"), angularaxis=dict(gridcolor="#30394b")), showlegend=False, height=360, margin=dict(l=25,r=25,t=55,b=20), font=dict(color="#dce3f1"))
            st.plotly_chart(radar, use_container_width=True)
        with right:
            score_df = pd.DataFrame({"Component": CRITERIA, "Score": [current["scores"][c] for c in CRITERIA]})
            bar = px.bar(score_df, x="Score", y="Component", orientation="h", range_x=[0,10], text="Score", color="Score", color_continuous_scale=["#f07b70", "#f4c96b", "#56b89a"])
            bar.update_layout(title="Score by component", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=390, coloraxis_showscale=False, margin=dict(l=10,r=25,t=55,b=25), yaxis=dict(categoryorder="array", categoryarray=CRITERIA[::-1]), font=dict(color="#dce3f1"))
            bar.update_traces(textposition="outside", marker_line_width=0)
            st.plotly_chart(bar, use_container_width=True)
    with result_tabs[1]:
        st.markdown("#### Criterion by criterion")
        for criterion in CRITERIA:
            score = current["scores"][criterion]
            with st.expander(f"{criterion}  ·  {score}/10", expanded=score <= 5):
                st.progress(score / 10)
                feedback = current.get("feedback", {})
                st.write(feedback.get(criterion.lower(), feedback.get(criterion, "No detailed feedback returned.")))
        a, b = st.columns(2)
        with a:
            st.markdown("#### ✅ Strengths")
            for item in current.get("strengths", []) or ["Keep practicing to build clear, repeatable instructions."]:
                st.markdown(f"- {item}")
        with b:
            st.markdown("#### 🔎 Missing components")
            for item in current.get("missing_components", []) or ["No major omissions identified."]:
                st.markdown(f"- {item}")
    with result_tabs[2]:
        st.markdown("#### Suggested improvements")
        suggestions = current.get("suggestions", [])
        if suggestions:
            for i, item in enumerate(suggestions, 1):
                st.markdown(f"**{i}.** {item}")
        else:
            st.write("No additional suggestions returned.")
        st.markdown("#### Optimized version")
        st.code(current.get("optimized_prompt", ""), language="markdown")
        if current.get("optimized_prompt"):
            st.button("Use optimized prompt in workspace ↑", on_click=load_optimized_prompt)
    with result_tabs[3]:
        if len(st.session_state.evaluations) > 1:
            history = pd.DataFrame([{"Attempt": i + 1, "Overall score": e["overall"], "Time": e["created_at"]} for i, e in enumerate(st.session_state.evaluations)])
            progress_fig = px.line(history, x="Attempt", y="Overall score", markers=True, hover_data=["Time"], range_y=[0,100])
            progress_fig.update_traces(line_color="#5267d8", marker_size=10, line_width=3)
            progress_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111720", yaxis_title="Score out of 100", xaxis_title="Attempt", height=320)
            st.plotly_chart(progress_fig, use_container_width=True)
            detail = pd.DataFrame([{"Attempt": i + 1, **e["scores"]} for i, e in enumerate(st.session_state.evaluations)]).set_index("Attempt")
            st.dataframe(detail, use_container_width=True)
        else:
            st.info("Your score history will appear here after you submit another prompt. Try the optimized version and compare your results.")
def load_suggested_prompt():
    st.session_state.prompt_draft = st.session_state.suggested_prompt


latest_suggestion = st.session_state.evaluations[-1].get("optimized_prompt", "") if st.session_state.evaluations else ""
if latest_suggestion.strip():
    suggested_prompt = latest_suggestion.strip()
    suggestion_note = "Built from your latest evaluation. Use it as a new draft, then adapt it to your needs."
else:
    suggested_prompt = (
        f"You are {ROLE_BY_DOMAIN[challenge_domain]}.\n\n"
        f"Goal: {scenario}\n\n"
        "Context: The intended audience is [describe the audience]. Relevant background is [add the facts, data, or situation the AI should use]. "
        "If important information is missing, state your assumptions and do not invent facts.\n\n"
        "Constraints: Address every part of the goal. Keep the response practical and specific. Separate facts from assumptions, and mention important risks or limitations.\n\n"
        "Format: Provide the requested deliverable first. Use clear headings or bullets where helpful, then briefly list assumptions and next steps.\n\n"
        "Style: Be clear, concise, professional, and appropriate for the intended audience."
    )
    suggestion_note = "A scenario-specific starting point. Fill in the bracketed details before submitting it."
st.session_state.suggested_prompt = suggested_prompt
st.divider()
st.markdown('<div class="kicker">STEP 4  /  YOUR STRONGER PROMPT</div>', unsafe_allow_html=True)
st.subheader("A stronger version to try")
st.write(suggestion_note)
st.code(suggested_prompt, language="markdown")
st.button("Use this suggested prompt in the editor ↑", on_click=load_suggested_prompt, use_container_width=True)
st.caption("Scores are AI-generated feedback, not an objective measure. Avoid entering confidential or personal data.")




















