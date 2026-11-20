"""Build the expanded SCITEPRESS-style manuscript from the saved project data."""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OUT = Path(os.environ.get(
    "DQN_PAPER_OUT", PAPER / "State_Representation_DQN_Traffic_Signal_Pilot.docx"
))
SUMMARY = ROOT / "results" / "high_demand_evaluation_summary.csv"
_BODY_START_AFTER_HEADING = False
_LAST_HEADING_LEVEL: int | None = None


def read_summary() -> dict[tuple[str, str], dict[str, str]]:
    with SUMMARY.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return {(row["agent"], row["state_mode"]): row for row in rows}


SUMMARY_ROWS = read_summary()


def set_font(run, size: float = 10, bold=None, italic=None, name="Times New Roman"):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for key in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{key}"), name)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    return run


def set_style(style, size: float, bold=False, italic=False):
    style.font.name = "Times New Roman"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = None


def set_page(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.3)
    section.bottom_margin = Cm(4.2)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.6)
    section.header_distance = Cm(1.4)
    section.footer_distance = Cm(2.5)


def set_columns(section, count: int, spacing_cm: float = 0.8):
    cols = section._sectPr.xpath("./w:cols")
    if cols:
        element = cols[0]
    else:
        element = OxmlElement("w:cols")
        section._sectPr.append(element)
    element.set(qn("w:num"), str(count))
    element.set(qn("w:space"), str(int(Cm(spacing_cm).twips)))
    element.set(qn("w:equalWidth"), "1")


def paragraph_format(p, *, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, size_after=4,
                    before=0, left=0, first=0, line=1.0):
    p.alignment = alignment
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(size_after)
    pf.left_indent = Cm(left)
    pf.first_line_indent = Cm(first)
    pf.line_spacing = line
    return p


def add_body(doc, text: str, indent=None, *, keep=False):
    global _BODY_START_AFTER_HEADING
    if indent is None:
        indent = not _BODY_START_AFTER_HEADING
    _BODY_START_AFTER_HEADING = False
    p = doc.add_paragraph(style="Normal")
    paragraph_format(p, first=0.5 if indent else 0)
    p.paragraph_format.keep_together = keep
    set_font(p.add_run(text), 10)
    return p


def add_heading(doc, text: str, level=1):
    global _BODY_START_AFTER_HEADING, _LAST_HEADING_LEVEL
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.keep_together = True
    if level == 1:
        before = 0 if text == "1 INTRODUCTION" else 24
        after, line, left, hanging, size = 12, 15, 0.7, 0.7, 13
        text = text.upper()
    elif level == 2:
        before = 0 if _LAST_HEADING_LEVEL == 1 else 11
        after, line, left, hanging, size = 11, 13, 1.0, 1.0, 12
    else:
        before = 0 if _LAST_HEADING_LEVEL == 2 else 10
        after, line, left, hanging, size = 10, 12, 1.0, 1.0, 11
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = Pt(line)
    p.paragraph_format.first_line_indent = Cm(-hanging)
    p.paragraph_format.left_indent = Cm(left)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(p.add_run(text), size, bold=True)
    _BODY_START_AFTER_HEADING = True
    _LAST_HEADING_LEVEL = level
    return p


def add_caption(doc, text: str, *, before=6, after=12, figure=False):
    p = doc.add_paragraph()
    alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if len(text) > 120 else WD_ALIGN_PARAGRAPH.CENTER
    paragraph_format(p, alignment=alignment, size_after=after, before=before, line=1.0)
    p.paragraph_format.keep_with_next = not figure
    set_font(p.add_run(text), 9)
    return p


def add_equation(doc, text: str, number: int):
    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT, size_after=12, before=12, line=1.0)
    p.paragraph_format.keep_together = True
    p.paragraph_format.tab_stops.add_tab_stop(Cm(3.75), WD_TAB_ALIGNMENT.CENTER)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(7.5), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    set_font(p.add_run(text), 9)
    p.add_run("\t")
    set_font(p.add_run(f"({number})"), 9)
    return p


def add_section(doc, count: int):
    section = doc.add_section(WD_SECTION.CONTINUOUS)
    set_page(section)
    set_columns(section, count, 0.8)
    return section


def set_cell_border(cell, **edges):
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.append(borders)
    for edge, props in edges.items():
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        for key, value in props.items():
            element.set(qn(f"w:{key}"), str(value))


def set_cell_margins(cell, top=50, start=65, bottom=50, end=65):
    tcpr = cell._tc.get_or_add_tcPr()
    margins = tcpr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tcpr.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_table(doc, caption: str, headers: list[str], rows: list[list[str]], widths_cm: list[float], *, font=8):
    add_caption(doc, caption, before=12, after=6)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header_props = table.rows[0]._tr.get_or_add_trPr()
    repeat_header = OxmlElement("w:tblHeader")
    repeat_header.set(qn("w:val"), "true")
    header_props.append(repeat_header)
    for index, (cell, text, width) in enumerate(zip(table.rows[0].cells, headers, widths_cm)):
        cell.width = Cm(width)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cell.text = ""
        p = cell.paragraphs[0]
        paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, size_after=1, before=1)
        set_font(p.add_run(text), font, bold=True)
        set_cell_border(cell, top={"val": "single", "sz": 8, "color": "000000"},
                        bottom={"val": "single", "sz": 6, "color": "000000"})
        set_cell_margins(cell)
    for row_values in rows:
        cells = table.add_row().cells
        row_props = table.rows[-1]._tr.get_or_add_trPr()
        row_props.append(OxmlElement("w:cantSplit"))
        for index, (cell, text, width) in enumerate(zip(cells, row_values, widths_cm)):
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT if index == 0 else WD_ALIGN_PARAGRAPH.LEFT,
                             size_after=1, before=1)
            set_font(p.add_run(text), font)
            set_cell_border(cell, bottom={"val": "single", "sz": 3, "color": "A0A0A0"})
            set_cell_margins(cell)
    for row in table.rows:
        for cell, width in zip(row.cells, widths_cm):
            cell.width = Cm(width)
    return table


def add_full_width_figure(doc, image_name: str, caption: str, *, width_cm=15.7):
    add_section(doc, 1)
    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, size_after=4)
    p.paragraph_format.keep_together = True
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(PAPER / "figures" / image_name), width=Cm(width_cm))
    add_caption(doc, caption, before=6, after=12, figure=True)
    add_section(doc, 2)


def metric_value(key, metric, digits=2):
    return float(SUMMARY_ROWS[key][metric])


def mean_sd(key, mean_key, sd_key, digits=2):
    return f"{metric_value(key, mean_key):.{digits}f} ± {metric_value(key, sd_key):.{digits}f}"


def main():
    doc = Document()
    normal = doc.styles["Normal"]
    set_style(normal, 10)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_after = Pt(4)
    for style_name, size in (("Heading 1", 13), ("Heading 2", 12), ("Heading 3", 11)):
        set_style(doc.styles[style_name], size, bold=True)
    set_page(doc.sections[0])
    set_columns(doc.sections[0], 1)

    # SCITEPRESS front matter.
    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, size_after=0, before=0, line=Pt(17))
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run("A Pilot Comparison of State Representations for DQN Traffic Signal Control"), 15, bold=True)

    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, size_after=0, before=24, line=Pt(13))
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run("Nikshay Kumar Nagda¹, Aashutosh Nagda¹, Neel Soni¹, Keiyur Savani¹"), 11)

    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, size_after=0, line=Pt(11))
    p.paragraph_format.keep_with_next = True
    set_font(p.add_run("¹Department of IT and Computer Science, Parul University; MCA, Parul Institute of Engineering and Technology, Post-Limda, Waghodia, Vadodara, India"), 9, italic=True)

    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.CENTER, size_after=0, line=Pt(11))
    set_font(p.add_run("nikshay724@gmail.com, ashutoshnagda07@gmail.com"), 9, italic=True)

    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, size_after=0, before=48,
                     left=2.0, first=-2.0, line=Pt(11))
    set_font(p.add_run("Keywords: "), 9)
    set_font(p.add_run("Deep Reinforcement Learning, Deep Q-Network, Traffic Signal Control, State Representation, SUMO."), 9)

    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, size_after=30, before=12,
                     left=2.0, first=-2.0, line=Pt(11))
    set_font(p.add_run("Abstract: "), 9)
    abstract = (
        "This pilot examines whether adding traffic-state features changes deep Q-network (DQN) performance at one synthetic, "
        "high-demand SUMO intersection. We trained a three-feature controller and a nine-feature controller for 160 episodes "
        "each, then evaluated both on ten shared, held-out demand seeds alongside fixed-time and seeded-random baselines. The "
        "richer observation combines queue counts and active green axis with waiting-time, speed, and occupancy summaries. "
        "Across the ten evaluation seeds, it had lower mean queue (11.906 versus 12.252 vehicles), lower completed-trip mean "
        "waiting time (13.551 versus 15.388 s), and higher mean arrivals (219.1 versus 210.2). The compact DQN matched the "
        "fixed-time baseline on every recorded outcome for every seed. These results are descriptive: each state mode had one "
        "training run, action traces were not retained, and unfinished trips are excluded from waiting-time averages. The "
        "experiment does not establish statistical significance, generalization, or real-world benefit."
    )
    set_font(p.add_run(abstract), 9)

    add_section(doc, 2)

    add_heading(doc, "1 INTRODUCTION", 1)
    add_body(doc,
        "Traffic signals allocate a scarce resource: green time at a conflict point. A controller that grants too little time "
        "to an approach can build a queue, while an unnecessary phase change consumes time in clearance and delays vehicles "
        "on both axes. Deep reinforcement learning (DRL) frames this task as sequential decision-making: the controller "
        "observes a state, selects an action, receives a reward, and uses experience to improve its future choices. Deep "
        "Q-networks (DQN) approximate action values with neural networks and use replay and a target network to stabilize "
        "learning (Mnih et al., 2015)."
    )
    add_body(doc,
        "A central design question is what the controller can observe. Queue counts are intuitive and inexpensive, but do not "
        "directly express how long vehicles have waited, whether they are moving, or how much of an approach lane is occupied. "
        "Additional measurements might help a policy distinguish traffic situations that look similar under queue counts; "
        "they also increase input dimension and can add redundant or noisy signals. A richer state is therefore a hypothesis "
        "about useful information, not an automatic improvement."
    )
    add_body(doc,
        "Prior studies provide mixed motivation. Genders and Razavi (2018) compared state resolutions for adaptive traffic "
        "control and reported similar performance for lower- and higher-resolution representations in their simulated "
        "setting. A separate preprint reported benefits from high-dimensional observations under a different design "
        "(Francis et al., 2024). IntelliLight and PressLight illustrate other choices in how reinforcement learning "
        "observations and objectives are constructed for signal control (Wei et al., 2018, 2019). Differences in simulator, "
        "demand, policy, state, reward, and evaluation make these studies context rather than direct predictions for this pilot."
    )
    add_body(doc,
        "We compare two DQNs that share their hidden-layer structure, action space, reward, training budget, traffic profile, "
        "and held-out evaluation seeds. Their planned difference is the observation: three features versus nine. Both operate "
        "at a single isolated intersection in SUMO. The work is a reproducible engineering pilot that asks whether the saved "
        "evaluation outcomes differ under one frozen configuration; it does not propose a new learning algorithm or claim a "
        "field-tested traffic controller."
    )
    add_heading(doc, "1.1 Research questions", 2)
    add_body(doc,
        "RQ1 asks whether the nine-feature DQN has different descriptive queue, waiting-time, and throughput outcomes from the "
        "three-feature DQN on the same ten simulated demand seeds. RQ2 asks how both DQNs compare with a fixed schedule and a "
        "seeded-random action policy under the same episode and signal settings. RQ3 asks what the recorded training curve and "
        "per-seed outcomes can and cannot explain about any observed differences. The questions are exploratory: no null "
        "hypothesis test or pre-registered effect threshold was used."
    )
    add_heading(doc, "1.2 Contributions and scope", 2)
    add_body(doc,
        "This paper contributes a paired-seed comparison using the project's verified SUMO network, an explicit description of "
        "the state and DQN update, transparent per-seed and aggregate outcome reporting, and Matplotlib figures generated from "
        "the tracked training and evaluation CSV files. It also records two findings that constrain interpretation: the rich "
        "DQN has more favorable evaluation averages in this run, and the compact DQN has exactly the same recorded outcomes as "
        "the fixed-time schedule on each seed. The project releases configuration, checkpoints, raw episode rows, and analysis "
        "through its public repository."
    )

    add_heading(doc, "2 BACKGROUND AND RELATED WORK", 1)
    add_body(doc,
        "DQN applies value-based reinforcement learning to problems with a finite action set. At an observation, the network "
        "outputs one estimated return for each available action. During training, epsilon-greedy selection sometimes explores "
        "by sampling an action; otherwise it selects the action with the largest estimated value. Experience replay breaks "
        "some of the correlation between consecutive transitions by sampling previous experiences, while a target network "
        "provides a slower-moving target for the temporal-difference update (Mnih et al., 2015). In signal control, the action "
        "set can represent phase selections or signal changes, while the observation may summarize queues, phase, arrivals, or "
        "other traffic features."
    )
    add_body(doc,
        "Traffic-signal learning papers differ not only in algorithm but in representation and objective. IntelliLight learns "
        "from traffic measurements and treats signal control as a reinforcement-learning problem (Wei et al., 2018). "
        "PressLight connects the learning objective to max-pressure traffic control and studies coordination in arterial "
        "networks (Wei et al., 2019). These designs show why comparing state size in isolation requires holding the rest of the "
        "experiment fixed. This pilot keeps a simple two-action interface and a single queue-based reward so that the "
        "observation length remains the intended factor, subject to the limitation that only one model per state is trained."
    )
    add_body(doc,
        "State representation has been examined directly in adaptive signal control. Genders and Razavi (2018) report that "
        "lower- and higher-resolution state alternatives performed similarly in their tested simulation. Francis et al. "
        "(2024) report gains from a high-dimensional representation in their own experimental setting. The contrast is useful "
        "because it cautions against universal claims: the value of a feature depends on whether it changes a decision in the "
        "particular network, demand regime, reward, and policy. The present test adds six aggregate measurements to queue and "
        "phase features but does not perform feature ablation; it cannot attribute the result to waiting time, speed, or "
        "occupancy individually."
    )
    add_body(doc,
        "SUMO supplies a microscopic simulation environment for vehicle movement and signal-phase interaction. The project "
        "uses SUMO 1.28.0 and TraCI to inspect lane measurements and apply the verified program at decision points (López et "
        "al., 2018). The environment owns the signal identifiers and clearance phases so that a policy selects only among two "
        "abstract actions. This separation avoids allowing an agent to issue an arbitrary signal string and makes its input "
        "dimension the experimental variable."
    )
    add_body(doc,
        "The comparison is intentionally narrower than a deployment study. It concerns one generated road layout, one "
        "synthetic arrival profile, one episode horizon, and one DQN configuration. That scope makes the saved outcomes "
        "reproducible from the repository and keeps the meaning of each feature tractable. It also prevents claims about "
        "intersections with turning traffic, pedestrians, transit priority, multiple coordinated junctions, or real demand "
        "measurements."
    )

    add_heading(doc, "3 SIMULATION SETTING", 1)
    add_heading(doc, "3.1 Intersection and signal program", 2)
    add_body(doc,
        "The simulated network contains one isolated four-approach junction, one incoming lane on each approach, and straight-"
        "through routes. The verified traffic-light identifier is J0 and the active signal program is 0. North-south green is "
        "phase 0, east-west green is phase 2, and each direction of a switch uses a three-second yellow phase (phase 1 or 3). "
        "These identifiers and phase mappings come from the repository's generated network manifest and SUMO network, not "
        "from assumed defaults."
    )
    add_body(doc,
        "SUMO advances one second at a time, while the controller acts every fifteen seconds. When it requests a switch, the "
        "environment executes the verified three-second yellow clearance; the remaining twelve seconds of that decision "
        "interval run on the newly active green axis. When it holds, the currently active axis remains green through the "
        "interval. Each 300-second episode therefore contains twenty decision intervals."
    )
    add_heading(doc, "3.2 Demand generation", 2)
    add_body(doc,
        "Four SUMO flows represent north-to-south, south-to-north, east-to-west, and west-to-east vehicles. Each flow is "
        "configured at 900 vehicles per hour from simulation time zero to 300 seconds. The configured total is 3,600 "
        "vehicles per hour across the four approaches; this is a generated peak-load scenario, not a measured local count or "
        "calibrated urban demand model. Vehicle attributes are the values in routes.rou.xml, including a maximum speed of "
        "13.89 m/s. Seeds vary the stochastic traffic generation between episodes."
    )
    add_body(doc,
        "The scenario excludes turns, pedestrians, incidents, lane changes between approaches, and coordination with nearby "
        "signals. It is designed to produce competition between the two green axes while avoiding route-choice or multi-agent "
        "effects. The same network, routes, step length, demand configuration, and 300-second horizon are used for both state "
        "modes and all evaluation controllers."
    )
    add_heading(doc, "3.3 Markov decision process", 2)
    add_body(doc,
        "We represent the simulator as a finite-horizon Markov decision process with observation sₜ, action aₜ ∈ {0, 1}, "
        "queue reward rₜ, and next observation sₜ₊₁. Action 0 means hold the currently active green axis. Action 1 means "
        "request the other axis; the environment applies the clearance phase and returns at a legal green decision point. The "
        "policy does not control the yellow duration directly. The episode ends at 300 seconds, with no bootstrap beyond the "
        "terminal transition."
    )
    add_body(doc,
        "For each decision interval, the environment samples the total number of halted vehicles after each one-second SUMO "
        "step. The reward is the negative average of those queue samples for the interval. Thus, a less-negative reward "
        "corresponds to fewer halted vehicles. The objective asks the agent to reduce accumulated queue burden rather than "
        "maximize arrivals alone. The evaluation still reports arrivals and completed-trip waiting time because they capture "
        "different aspects of episode performance."
    )
    add_equation(doc, "rₜ = −Δ⁻¹ Σₖ₌₁^Δ Qₜ,ₖ", 1)
    add_equation(doc, "G = Σₜ₌₁²⁰ rₜ,  Δ = 15 s", 2)

    add_heading(doc, "4 STATE REPRESENTATIONS", 1)
    add_body(doc,
        "The compact state contains the total north-south queue, total east-west queue, and active green axis. The rich state "
        "preserves those three measurements and appends six lane-derived summaries: accumulated waiting time, mean speed, and "
        "mean occupancy for each axis. Queue and waiting-time values are summed across the corresponding two incoming lanes; "
        "speed and occupancy are averaged across those lanes. Occupancy is represented as a fraction from zero to one."
    )
    add_body(doc,
        "Before entering the network, each feature is divided by a fixed scale. The shared queue features use 20 vehicles; "
        "waiting-time sums use 300 seconds; speed uses 13.89 m/s; occupancy fractions and the binary green-axis feature use "
        "one. These values are normalization divisors and do not clip observations. The rich mode adds no vehicle identities, "
        "camera frames, or information about turning movements."
    )

    add_section(doc, 1)
    feature_rows = [
        ["1–2", "Both", "North-south and east-west totals of halted vehicles on incoming lanes.", "20 vehicles each"],
        ["3", "Both", "Current green axis: 0 for north-south; 1 for east-west.", "1"],
        ["4–5", "Rich only", "North-south and east-west sums of SUMO lane waiting-time readings.", "300 s each"],
        ["6–7", "Rich only", "Mean lane speed across the two incoming lanes on each axis.", "13.89 m/s each"],
        ["8–9", "Rich only", "Mean lane occupancy fraction across the two incoming lanes on each axis.", "1 each"],
    ]
    add_table(doc, "Table 1: Ordered observations and their fixed input scales.",
              ["Index", "Mode", "Feature meaning", "Scale divisor"], feature_rows,
              [1.4, 2.2, 8.1, 4.1], font=8)
    add_body(doc,
        "The feature design is deliberately axis-aggregated. In the simple mode, two traffic states with equal queue totals and "
        "the same active axis are indistinguishable to the network even if vehicles on one approach have waited longer or are "
        "moving at a different speed. The rich mode can represent some of those differences, but it still collapses north with "
        "south and east with west. It therefore remains a low-dimensional summary of the simulator rather than a complete "
        "description of each vehicle."
    , False)
    add_section(doc, 2)

    add_heading(doc, "5 DQN CONTROLLER", 1)
    add_heading(doc, "5.1 Network and value estimates", 2)
    add_body(doc,
        "Both agents use a fully connected neural network with two hidden layers of 64 units and rectified-linear (ReLU) "
        "activations. The input layer accepts either three or nine normalized values. The output layer produces two action "
        "values, one for holding and one for switching. At evaluation time, the controller selects the action with the greater "
        "estimated value; ties are resolved by the first maximum returned by the implementation."
    )
    add_body(doc,
        "The network parameters are θ for the online policy and θ⁻ for the target network. After storing a transition, a "
        "minibatch is drawn from replay. For each transition, the one-step target uses the observed reward and the best "
        "estimated value at the next state, unless the transition is terminal. The target network is held constant between "
        "scheduled copies from the online network."
    )
    add_equation(doc, "yᵢ = rᵢ + γ (1 − dᵢ) maxₐ′ Qθ⁻(s′ᵢ, a′)", 3)
    add_equation(doc, "L(θ) = mean SmoothL1(Qθ(sᵢ, aᵢ), yᵢ)", 4)
    add_body(doc,
        "The optimizer is Adam with learning rate 0.001 and discount γ = 0.99. The implementation uses Smooth L1 (Huber) "
        "loss, clips gradient norm at 10, and copies policy weights to the target network every 100 gradient steps. These "
        "settings are shared by the two agents. The only model-shape difference is the input dimension and consequently the "
        "first layer's parameter count."
    )
    add_heading(doc, "5.2 Replay and exploration", 2)
    add_body(doc,
        "The replay buffer holds up to 5,000 transitions and training samples 32 per update. Learning begins once the buffer "
        "contains 32 transitions. Epsilon begins at 1.0, is multiplied by 0.995 after every training action, and is bounded "
        "below by 0.05. As each episode has twenty decisions, the minimum is reached after roughly 600 action selections, or "
        "around the beginning of episode 31. After that point exploration is reduced but not eliminated: a random action is "
        "still selected with probability 0.05 during training. Evaluation disables epsilon-greedy exploration."
    )
    add_body(doc,
        "Each model receives 160 episodes, or 3,200 decision transitions when all episodes run the full 300 seconds. Since "
        "this is below the 5,000-transition capacity, the replay buffer does not reach its maximum size in this run. Training "
        "uses a single initialization seed of 42 for each agent and the same ordered traffic seeds 42–201 for its episodes. "
        "The two parameter sets are not independent repetitions of a multi-seed training design."
    )

    add_section(doc, 1)
    algo_lines = [
        "Input: mode m ∈ {simple, rich}; 160 episodes; γ = 0.99.",
        "Initialize Qθ, target Qθ⁻ ← Qθ, Adam, replay B, ε = 1.0.",
        "For each episode, reset SUMO with the next training seed; observe s.",
        "For each of 20 decision intervals:",
        "    Select a random action with probability ε; else argmaxₐ Qθ(s, a).",
        "    Execute action; step SUMO 15 s; observe r, s′, done.",
        "    Store (s, a, r, s′, done) in B.",
        "    If |B| ≥ 32, sample 32 and compute the target y.",
        "    Update Qθ with SmoothL1 loss; clip gradient norm to 10.",
        "    Every 100 updates, copy online weights to Qθ⁻.",
        "    ε ← max(0.05, 0.995ε).",
        "At evaluation, act greedily on shared seeds 300–309.",
    ]
    for line in algo_lines:
        p = doc.add_paragraph()
        paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT, size_after=0, line=1.0)
        p.paragraph_format.keep_with_next = True
        set_font(p.add_run(line), 9, name="Courier New")
    algo_caption = add_caption(doc, "Algorithm 1: Shared DQN training loop.", before=6, after=12)
    algo_caption.paragraph_format.keep_with_next = False
    add_section(doc, 2)
    add_body(doc,
        "The pseudocode emphasizes the boundary between agent and simulator. The network never changes a traffic-light "
        "program directly: it returns 0 or 1. The environment maps that request to the verified green or clearance phases, "
        "steps SUMO for the decision interval, and then returns a numeric state. This makes the same control loop usable by "
        "the three- and nine-feature agents without changing the network or phase logic."
    )

    add_heading(doc, "6 EXPERIMENTAL PROTOCOL", 1)
    add_heading(doc, "6.1 Training and held-out evaluation", 2)
    add_body(doc,
        "The two state modes were each trained for 160 episodes using the same consecutive traffic seeds, 42 through 201. "
        "Evaluation used ten held-out seeds, 300 through 309, shared by every controller. These seeds do not overlap the "
        "training range. Each episode lasted 300 seconds. The DQN checkpoints were evaluated greedily, without exploration. "
        "The saved evaluation CSV contains 40 episodes: ten for each of the rich DQN, compact DQN, fixed-time, and random "
        "controllers."
    )
    add_body(doc,
        "The fixed-time baseline requests a switch on every decision interval, alternating the green axis every fifteen "
        "seconds. The seeded-random baseline samples either action with a reproducible random generator tied to the evaluation "
        "seed. The baselines use the same environment and route generation as the DQNs. The comparison does not include an "
        "optimized cycle length, actuated logic, pressure-based controller, or a human-designed local timing plan."
    )
    add_heading(doc, "6.2 Outcome measures", 2)
    add_body(doc,
        "Episode return is the sum of twenty interval rewards. Mean queue is the time average of the total halted-vehicle "
        "count across all one-second simulation steps. Throughput is the number of vehicles that arrive before 300 seconds. "
        "Completed-trip mean waiting time is the arithmetic mean of SUMO TripInfo waitingTime for trips that completed by the "
        "episode cutoff. Any trip still in the network at the cutoff is omitted from that waiting-time value; this right "
        "censoring can make a run appear to have lower mean waiting if more delayed trips remain unfinished."
    )
    add_body(doc,
        "Because each episode contains exactly twenty equal decision intervals and the reward is the negative interval mean "
        "queue, episode return is a deterministic rescaling of time-average mean queue: G = −20 × mean queue, up to the CSV "
        "rounding. The two statistics should not be treated as independent evidence. Waiting time and arrivals provide "
        "different information but carry their own measurement limits. All table means and sample standard deviations below "
        "are across the ten evaluation seeds for each controller."
    )
    add_heading(doc, "6.3 Descriptive analysis", 2)
    add_body(doc,
        "We report means, sample standard deviations, and the direction of paired per-seed differences. No p-values, confidence "
        "intervals, or inferential claims are provided. The ten seeds quantify variability in demand realization for the "
        "saved checkpoints; they do not quantify variability across independent training runs. The training figure uses a "
        "trailing ten-episode moving mean to show broad movement without hiding the raw episode-to-episode variability."
    )

    add_heading(doc, "7 RESULTS", 1)
    add_heading(doc, "7.1 Held-out outcomes", 2)
    add_body(doc,
        "The nine-feature DQN recorded a mean queue of 11.906 vehicles, compared with 12.252 for the compact DQN, a "
        "descriptive reduction of 0.346 vehicles or about 2.8%. Its completed-trip mean wait was 13.551 seconds rather than "
        "15.388 seconds, a reduction of about 1.84 seconds or 11.9%. Mean arrivals increased from 210.2 to 219.1 per episode, "
        "an increase of 8.9 vehicles or 4.2%. Episode return was −238.120 versus −245.047; this is consistent with the queue "
        "difference because return is calculated from queue."
    )
    add_body(doc,
        "The rich-versus-compact per-seed differences favor the rich model on waiting time and arrivals for all ten seeds. "
        "Queue and return favor the rich model on nine seeds, with one seed slightly favoring the compact model. These counts "
        "are descriptive summaries of this one model pair, not evidence of a repeatable probability of winning. Figure 2 "
        "shows the actual paired differences so readers can see their size and spread rather than relying only on averages."
    )
    add_section(doc, 1)
    outcome_rows = []
    for label, key in (
        ("Rich DQN (9 features)", ("DQN", "rich")),
        ("Compact DQN (3 features)", ("DQN", "simple")),
        ("Fixed-time (switch each decision)", ("fixed_time_1decision", "simple")),
        ("Seeded random", ("random", "simple")),
    ):
        outcome_rows.append([
            label,
            mean_sd(key, "episode_return_mean", "episode_return_sd", 2),
            mean_sd(key, "mean_queue_vehicles_mean", "mean_queue_vehicles_sd", 3),
            mean_sd(key, "mean_wait_s_mean", "mean_wait_s_sd", 2),
            mean_sd(key, "throughput_vehicles_mean", "throughput_vehicles_sd", 1),
        ])
    add_table(doc, "Table 2: Held-out outcomes, mean ± sample SD across ten shared seeds.",
              ["Controller", "Return¹", "Mean queue", "Completed wait (s)", "Arrivals / episode"],
              outcome_rows, [3.5, 2.7, 2.8, 3.4, 3.3], font=7.6)
    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT, size_after=4, before=2)
    set_font(p.add_run("¹ Episode return equals approximately −20 times mean queue in these fixed-length episodes; it is not an independent outcome. Waiting time includes completed trips only."), 8)
    add_section(doc, 2)
    add_full_width_figure(doc, "evaluation_means.png",
        "Figure 1: Mean queue, completed-trip waiting time, and arrivals for the four controllers. Error bars show ±1 sample standard deviation across ten shared evaluation seeds.")
    add_body(doc,
        "The compact DQN and fixed-time controller have exactly matching saved values for episode return, mean queue, "
        "completed-trip waiting time, and arrivals on every shared seed. Their group means and standard deviations are also "
        "identical. This equality is stronger than similar averages, but it does not reveal the action sequence because the "
        "evaluation CSV stores episode summaries rather than decision-level actions. It does establish that this trained "
        "compact controller did not separate from the fixed schedule on any outcome retained in the file."
    )
    add_body(doc,
        "The random baseline had a mean queue of 15.000 vehicles and a completed-trip wait of 17.636 seconds, both higher "
        "than the DQN and fixed-time means. Its mean arrivals, 213.9, were higher than the compact and fixed-time means of "
        "210.2, but lower than the rich DQN's 219.1. Its arrival standard deviation was 13.9, substantially larger than "
        "those of the other controllers. This illustrates why throughput alone does not summarize queueing performance."
    )

    add_heading(doc, "7.2 Paired differences by evaluation seed", 2)
    add_body(doc,
        "Table 3 gives the mean of the ten paired differences and their sample standard deviation. Differences are oriented "
        "so positive values favor the rich state: compact minus rich for queue and waiting time, and rich minus compact for "
        "arrivals. The queue reduction is small in absolute vehicle count and the paired differences have one negative value; "
        "the waiting and arrival differences are positive for all ten seeds. These summaries describe consistency within the "
        "held-out set, not statistical significance or policy-level uncertainty."
    )
    add_section(doc, 1)
    paired_rows = [
        ["Mean queue reduction (vehicles)", "0.3463 ± 0.2257", "9 / 10"],
        ["Completed-trip wait reduction (s)", "1.8373 ± 0.8091", "10 / 10"],
        ["Arrivals increase (vehicles)", "8.90 ± 3.48", "10 / 10"],
    ]
    add_table(doc, "Table 3: Paired rich-versus-compact differences across the same ten demand seeds (mean ± sample SD).",
              ["Outcome; positive favors rich", "Paired difference", "Seeds favoring rich"], paired_rows,
              [7.5, 5.0, 3.2], font=8)
    add_section(doc, 2)

    add_heading(doc, "7.3 Training trajectories", 2)
    add_body(doc,
        "The training CSV contains 160 episode rows per state mode. Raw outcomes vary substantially between successive traffic "
        "seeds. In the first versus last twenty episodes, compact-state mean queue changed from 13.295 to 12.800 vehicles, "
        "completed-trip waiting time from 16.317 to 15.916 seconds, and arrivals from 214.35 to 210.05. For the rich state, "
        "the corresponding changes were 13.560 to 13.261 vehicles, 16.692 to 15.059 seconds, and 213.55 to 224.05 arrivals. "
        "These window averages are descriptions of a single exploratory training run, not independent validation results."
    )
    add_full_width_figure(doc, "training_progress.png",
        "Figure 2: Episode-level training queue, completed-trip wait, and arrivals. Faint lines show raw episode values; bold lines show trailing ten-episode means. The dashed marker indicates the approximate episode at which epsilon reaches its 0.05 floor.")
    add_body(doc,
        "The curves remain noisy after the exploration floor is reached. The compact and rich training trajectories do not "
        "show a smooth monotonic decline in queue or waiting time, and arrivals fluctuate with the traffic seeds. The rich "
        "model's final held-out advantage therefore cannot be described as a clear monotonic training convergence pattern. "
        "The training return includes exploratory actions, whereas evaluation uses the greedy policy; training and evaluation "
        "averages answer different questions and should not be compared as though they were drawn under the same policy."
    )
    add_full_width_figure(doc, "paired_seed_differences.png",
        "Figure 3: Paired per-seed differences between rich and compact DQNs. Positive values favor the rich state; a zero value indicates a tie. The vertical colored line marks the mean difference. No inferential test is implied.")

    add_heading(doc, "8 DISCUSSION", 1)
    add_heading(doc, "8.1 What could explain the richer state's averages?", 2)
    add_body(doc,
        "A plausible mechanism is that waiting time, speed, and occupancy provide signals about congestion that queue totals "
        "alone do not express. For example, the same halted-vehicle count may occur when a queue is dissolving after green or "
        "when arrivals are building during red. A waiting-time sum can distinguish the age of accumulated delay; mean speed "
        "can signal movement or blockage; occupancy can indicate how fully an approach lane is filled. Under four simultaneous "
        "high-rate flows, these additional summaries may help a value network assign different action values to situations "
        "that collapse to the same three-feature vector."
    )
    add_body(doc,
        "That mechanism is an interpretation, not a result established by the experiment. The study did not remove individual "
        "features one at a time, inspect Q-values or action frequencies, or repeat training across several independent "
        "initialization seeds. The extra dimensions could also change optimization behavior or interact with the fixed "
        "normalization values. The measured improvement is therefore associated with the nine-feature configuration as a "
        "whole; it cannot be attributed to any particular measurement or asserted as a general benefit of richer observations."
    )
    add_heading(doc, "8.2 Why does the compact DQN match fixed-time?", 2)
    add_body(doc,
        "The fixed-time controller requests action 1 on every decision, so the signal alternates axes every fifteen seconds "
        "with the same yellow clearance as the learned controller. The compact DQN's exact outcome match across all ten "
        "seeds is consistent with its greedy decisions reproducing that alternating schedule. If so, queue reward and the "
        "available queue and phase inputs could have led the compact model to a stable period-like policy. The current records "
        "do not prove that explanation: another action sequence could, in principle, produce the same episode aggregates, "
        "and the tracked evaluation file contains no action traces."
    )
    add_body(doc,
        "A second possibility is that the compact model did not learn a useful state-dependent switching rule within 160 "
        "episodes. The training plot is noisy and there is only one training run per mode, so neither learned behavior nor "
        "failure to learn can be diagnosed from the saved averages. The appropriate follow-up is to record every decision's "
        "state, Q-values, chosen action, active phase, and reward, then compare the compact policy's action sequence directly "
        "against the baseline on identical seeds. Repeated model seeds would show whether this match is stable."
    )
    add_heading(doc, "8.3 Reading the outcome measures together", 2)
    add_body(doc,
        "The rich DQN's lower queue and higher throughput move in a consistent direction for this seed set, while the random "
        "controller demonstrates that throughput can rise without reducing queues. Completed-trip waiting is also favorable "
        "for the rich model, but it must be interpreted with the cutoff: a trip that has not arrived by 300 seconds does not "
        "contribute to waiting-time mean. Consequently, waiting-time improvement is not a full accounting of system delay. "
        "Reporting queue and arrivals alongside waiting time reduces, but does not eliminate, this censoring concern."
    )
    add_body(doc,
        "Episode return and mean queue should be read as one queue outcome in two forms, not as separate confirmation. The "
        "return is approximately minus twenty times the mean queue because the episode contains twenty equal intervals. A "
        "larger number of related metrics does not compensate for a small number of independent training runs. The ten "
        "shared traffic seeds do support a paired descriptive view, which is why Figure 3 presents seed-by-seed differences, "
        "but they do not replace repeated policy training."
    )
    add_heading(doc, "8.4 What the state-size comparison isolates", 2)
    add_body(doc,
        "Here, state complexity means the width of the engineered observation vector: three values for the compact DQN and "
        "nine for the rich DQN. It is not a measure of the full theoretical state space of the traffic process. Both models "
        "use the same two hidden layers of 64 units and the same two actions. The change is the six added input summaries: "
        "axis-specific waiting time, mean speed, and occupancy. This makes the comparison easy to reproduce and keeps most "
        "of the learning setup fixed, while targeting the question of whether these extra observations help in this scenario."
    )
    add_body(doc,
        "The input width also changes the number of fitted weights. With a 64-unit first hidden layer, the nine-input policy "
        "network has 384 more trainable parameters than the three-input policy network: six additional inputs multiplied by "
        "64 first-layer units. Counting the two dense hidden layers and the two action outputs gives 4,546 parameters for the "
        "compact policy network and 4,930 for the rich one, an 8.5% increase. This arithmetic is derived from the stated "
        "layer dimensions. Consequently, the observed contrast combines richer observations with a modest increase in "
        "function-approximation capacity; it is not a test that holds parameter count exactly constant."
    )
    add_body(doc,
        "A parameter-matched follow-up could reduce a hidden width in the rich model or widen the compact model, but either "
        "choice changes a different part of the architecture and should be treated as a separate control condition. More "
        "directly, feature ablations can show whether the added waiting, speed, or occupancy summaries contribute useful "
        "information under the current architecture. The present pilot cannot distinguish the effect of that information "
        "from the effect of the additional input-layer weights, so conclusions should refer to the tested configurations "
        "rather than to feature count alone."
    )

    add_heading(doc, "9 LIMITATIONS AND THREATS TO VALIDITY", 1)
    add_body(doc,
        "The findings are bounded by the simulation, sample, metrics, and implementation records. Table 3 summarizes the "
        "main threats and the evidence needed to address them. The results should not be represented as measured traffic "
        "improvement, a validated local signal plan, or evidence that nine features are generally better than three."
    )
    add_section(doc, 1)
    threats = [
        ["Training variation", "One trained checkpoint per state mode; evaluation seeds do not estimate initialization or learning variation.", "Train multiple independent model seeds and report between-run spread."],
        ["Scenario scope", "One synthetic straight-through four-approach junction at 900 veh/h per approach; no real counts or network diversity.", "Calibrate demand and test turns, multiple layouts, and coordinated signals."],
        ["Waiting-time censoring", "Only completed SUMO trips enter TripInfo waiting-time mean; unfinished trips are omitted at 300 s.", "Extend the horizon, report completion fraction, or use a censoring-aware measure."],
        ["Mechanism", "No action, Q-value, or per-feature ablation log; exact simple-versus-schedule equality has no unique explanation.", "Log decisions and run feature ablations with matched training seeds."],
        ["Compute traceability", "CSV records outcomes and wall time but not a complete hardware/runtime manifest for the final training run.", "Record Python, PyTorch, SUMO, device, and package versions for each run."],
    ]
    add_table(doc, "Table 4: Main validity limits and the next evidence needed.",
              ["Threat", "Limit in this pilot", "Follow-up"], threats,
              [2.5, 6.4, 6.8], font=7.7)
    add_section(doc, 2)
    add_heading(doc, "9.1 Statistical interpretation", 2)
    add_body(doc,
        "The ten evaluation episodes per controller use shared traffic seeds and are not ten independent policy fits. A "
        "standard deviation across these seeds describes demand-seed variation for a fixed checkpoint. It is not a confidence "
        "interval for the expected performance of a family of trained DQNs. The paper avoids significance claims and treats "
        "the mean differences as observed descriptive effects. A better follow-up would pair several independent training "
        "seeds with several held-out demand seeds and analyze the crossed variation explicitly."
    )
    add_heading(doc, "9.2 External validity", 2)
    add_body(doc,
        "A single isolated junction omits spillback from neighboring intersections, route diversion, turning conflicts, "
        "pedestrian clearance, emergency priority, and demand imbalance that can dominate a real signal's operating context. "
        "The equal 900-vehicle/hour rates are deliberately symmetrical and the 300-second horizon is short. SUMO's vehicle "
        "dynamics are simulated rather than observed. Results therefore indicate how these particular implementations "
        "behaved in this configured environment and should not be extrapolated to a city or deployed signal."
    )

    add_heading(doc, "10 REPRODUCIBILITY AND DATA AVAILABILITY", 1)
    add_body(doc,
        "The public repository contains the SUMO network and route files, verified network manifest, experiment JSON, "
        "DQN and environment implementation, training and evaluation entry points, checkpoints, raw episode CSV files, "
        "TripInfo outputs, and summary analyses. The paper's data plots are generated from the tracked high-demand training "
        "and evaluation CSV files. The figure-generation script is included in the paper directory so the presented graphs "
        "can be regenerated without estimating values from the manuscript."
    )
    add_body(doc,
        "The configured software identifies SUMO version 1.28.0. Training and evaluation scripts accept a device option for "
        "CPU or CUDA execution, but the final outcome CSV does not identify which device produced the saved checkpoints; "
        "this paper does not claim a particular GPU was used. The project records per-episode wall time, but does not retain "
        "a complete host and library-version manifest alongside the final run. Those omissions are noted rather than filled "
        "with assumptions."
    )
    p = doc.add_paragraph()
    paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.LEFT, size_after=4)
    set_font(p.add_run("Repository: "), 9, bold=True)
    set_font(p.add_run("https://github.com/nikshay01/traffic-dqn-state-complexity"), 9)

    add_heading(doc, "11 CONCLUSION", 1)
    add_body(doc,
        "In one synthetic high-demand SUMO intersection, a nine-feature DQN had lower mean queue and completed-trip waiting "
        "time, and higher mean arrivals, than a three-feature DQN across ten shared evaluation seeds. The simple DQN matched "
        "the fixed-time baseline exactly on every recorded episode outcome. The added waiting, speed, and occupancy features "
        "could help distinguish traffic states, but the existing evidence cannot show that mechanism or establish a "
        "generalizable advantage. The principal next steps are repeated independent training, decision-level action logging, "
        "a completed-trip-aware delay analysis, and evaluation under calibrated, varied traffic scenarios."
    , False)

    add_heading(doc, "REFERENCES", 1)
    references = [
        "Francis, L., Guda, B., & Biyabani, A. (2024). Optimizing traffic signal control using high-dimensional state representation and efficient deep reinforcement learning. arXiv preprint arXiv:2411.07759. https://doi.org/10.48550/arXiv.2411.07759",
        "Genders, W., & Razavi, S. (2018). Evaluating reinforcement learning state representations for adaptive traffic signal control. Procedia Computer Science, 130, 26–33. https://doi.org/10.1016/j.procs.2018.04.008",
        "López, P. Á., Behrisch, M., Bieker-Walz, L., Erdmann, J., Flötteröd, Y.-P., Hilbrich, R., Lücken, L., Rummel, J., Wagner, P., & Wießner, E. (2018). Microscopic traffic simulation using SUMO. In 2018 21st International Conference on Intelligent Transportation Systems (ITSC) (pp. 2575–2582). IEEE. https://doi.org/10.1109/ITSC.2018.8569938",
        "Mnih, V., Kavukcuoglu, K., Silver, D., Rusu, A. A., Veness, J., Bellemare, M. G., Graves, A., Riedmiller, M., Fidjeland, A. K., Ostrovski, G., Petersen, S., Beattie, C., Sadik, A., Antonoglou, I., King, H., Kumaran, D., Wierstra, D., Legg, S., & Hassabis, D. (2015). Human-level control through deep reinforcement learning. Nature, 518, 529–533. https://doi.org/10.1038/nature14236",
        "Wei, H., Zheng, G., Yao, H., & Li, Z. (2018). IntelliLight: A reinforcement learning approach for intelligent traffic light control. In Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (pp. 2496–2505). Association for Computing Machinery. https://doi.org/10.1145/3219819.3220096",
        "Wei, H., Chen, C., Zheng, G., Wu, K., Gayah, V. V., Xu, K., & Li, Z. (2019). PressLight: Learning max pressure control to coordinate traffic signals in arterial network. In Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (pp. 1290–1298). Association for Computing Machinery. https://doi.org/10.1145/3292500.3330949",
    ]
    italic_fragments = [
        ("arXiv preprint", "arXiv preprint"),
        ("Procedia Computer Science, 130", "Procedia Computer Science, 130"),
        ("2018 21st International Conference on Intelligent Transportation Systems (ITSC)", "2018 21st International Conference on Intelligent Transportation Systems (ITSC)"),
        ("Nature, 518", "Nature, 518"),
        ("Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining", "Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining"),
        ("Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining", "Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining"),
    ]
    for index, reference in enumerate(references):
        p = doc.add_paragraph()
        paragraph_format(p, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, size_after=4, left=0.5, first=-0.5, line=1.0)
        fragment = italic_fragments[index][0]
        if fragment in reference:
            before, after = reference.split(fragment, 1)
            set_font(p.add_run(before), 9)
            set_font(p.add_run(fragment), 9, italic=True)
            set_font(p.add_run(after), 9)
        else:
            set_font(p.add_run(reference), 9)


    add_heading(doc, "APPENDIX", 1)
    add_heading(doc, "Reading the Episode Records", 2)
    add_body(doc,
        "The raw CSV files are the source for the tables and figures. Each training or evaluation row represents one completed "
        "300-second simulation episode. The column names below are preserved as written so a reader can match the manuscript "
        "to results/high_demand_train_episodes.csv and results/high_demand_evaluation.csv. The summary CSV aggregates these "
        "rows by controller and state mode; it is not a separate simulation run."
    , False)
    add_section(doc, 1)
    data_dictionary = [
        ["seed", "SUMO traffic-generation seed for the episode.", "Training range 42–201; held-out evaluation 300–309."],
        ["agent", "Controller family: DQN, fixed-time, or random.", "Baselines share the same SUMO environment."],
        ["state_mode", "Observation label: simple or rich.", "Baseline rows use simple because they do not consume DQN state features."],
        ["episode", "Episode counter within the saved run.", "Training rows run from 1 to 160 per state mode."],
        ["episode_return", "Sum of the 20 queue-based interval rewards.", "Derived from mean queue for these fixed-length episodes."],
        ["mean_wait_s", "Mean TripInfo waitingTime for completed trips.", "Trips unfinished at the 300 s cutoff are omitted."],
        ["mean_queue_vehicles", "Time-average total halted-vehicle count.", "Computed from one-second SUMO samples."],
        ["throughput_vehicles", "Vehicles that arrived before episode end.", "Does not count unfinished trips as arrivals."],
        ["simulated_seconds", "Simulation time reached by the episode.", "The saved high-demand rows report 300 s."],
        ["wall_time_seconds", "Host elapsed time measured for the episode.", "Depends on the computer and software environment."],
    ]
    add_table(doc, "Table 5: Data dictionary for the saved episode-level CSV files.",
              ["CSV field", "Meaning", "Interpretation"], data_dictionary,
              [4.0, 6.2, 5.5], font=7.6)
    add_section(doc, 2)
    add_body(doc,
        "For the current summary, filter evaluation rows to one controller and state mode, then compute the arithmetic mean "
        "and sample standard deviation of the selected outcome across its ten seeds. For a paired comparison, join compact "
        "and rich rows on seed before subtracting outcomes. Keep raw episode rows when making a plot; do not reconstruct "
        "seed-level values from the summary means. The figure script follows this procedure for the training curves, mean "
        "and standard-deviation plot, and paired-difference plot."
    )

    add_heading(doc, "Follow-up Study Design", 2)
    add_body(doc,
        "A useful next experiment should resolve the main uncertainties in sequence. First, instrument the controller loop to "
        "record the state vector, Q-values, action, active axis, phase, reward, and traffic seed at every decision. This would "
        "show whether the compact model actually alternates like the fixed-time baseline and reveal how rich-state decisions "
        "differ. Second, repeat training with independent neural-network initialization seeds while keeping the train and "
        "evaluation seed lists shared across state conditions. This separates traffic-seed variation from model-training "
        "variation."
    )
    add_body(doc,
        "Third, use ablations that add one feature family at a time: queue and phase only; add waiting-time summaries; add "
        "speed summaries; add occupancy summaries; and the full nine-feature set. The same network, action set, reward, "
        "training budget, and evaluation demand should be retained for each ablation. Fourth, vary both the total arrival rate "
        "and directional balance, then test more than one network layout. Finally, record the number and age of unfinished "
        "trips at cutoff and report a delay measure that accounts for them, alongside queue, completed-trip wait, and "
        "arrivals. These are proposed next steps, not outcomes of the current pilot."
    )
    add_section(doc, 1)
    followup = [
        ["Decision logging", "Test the fixed-schedule explanation for the compact model.", "State, Q-values, action, phase, queue, reward, seed, and decision index."],
        ["Independent training runs", "Estimate variation caused by initialization and learning.", "Several training seeds crossed with shared held-out traffic seeds."],
        ["Feature ablation", "Identify whether waiting, speed, or occupancy carries useful information.", "Base state; then one feature family at a time; then full rich state."],
        ["Demand and network variation", "Assess whether the pattern depends on one symmetric scenario.", "Calibrated rates, directional imbalance, and multiple junction layouts."],
        ["Complete-trip accounting", "Reduce the bias from omitting trips unfinished at the cutoff.", "Completion fraction, unfinished-trip count, queue, arrivals, and delay."],
    ]
    add_table(doc, "Table 6: Proposed follow-up steps; none were part of the present results.",
              ["Step", "Question addressed", "Evidence to record"], followup,
              [3.2, 5.8, 6.7], font=7.6)
    add_section(doc, 2)
    add_body(doc,
        "A larger study should state its analysis plan before examining final outcomes. The primary outcome should be "
        "selected in advance, for example time-average queue, with completed-trip delay and arrivals treated as secondary "
        "outcomes. The episode horizon and the treatment of unfinished trips must also be fixed before running the final "
        "comparison. One option is to stop generating vehicles at the same time for every controller, then continue the "
        "simulation long enough for vehicles already in the network to finish. If a finite cutoff remains necessary, the "
        "report should include the completion fraction and remaining queue, and should not describe the completed-trip mean "
        "as total system delay."
    )
    add_body(doc,
        "For each observation configuration, train multiple independently initialized checkpoints. Evaluate every checkpoint "
        "on an identical held-out list of traffic seeds, and keep training seeds separate from evaluation seeds. This creates "
        "two sources of variation: which demand sequence is simulated and which training run produced the policy. Report "
        "per-checkpoint averages as well as paired differences by demand seed. Uncertainty calculations should resample or "
        "model both levels; treating all episodes from one checkpoint as independent trained policies would understate "
        "learning variation. The number of independent training runs should be chosen before the main study using pilot "
        "variance and available compute, then reported alongside all exclusions and failed runs."
    )
    add_body(doc,
        "The control conditions should include the existing fixed schedule and at least one responsive baseline, such as a "
        "properly configured actuated or pressure-based policy. Any baseline tuning must use training or development seeds, "
        "not the held-out evaluation set. For the DQNs, publish the full configuration, random seeds, state scales, checkpoint "
        "selection rule, software versions, and device. Log each decision's observations, Q-values, action, active phase, "
        "reward, and simulation time. These records make it possible to distinguish an algorithmic improvement from a "
        "baseline match, a measurement artifact, or a training-run fluctuation."
    )
    add_body(doc,
        "Finally, vary total demand, directional imbalance, and network layout while keeping the matched comparisons intact. "
        "Feature ablations should be specified before inspecting their evaluation outcomes, and the primary contrast should "
        "remain easy to interpret. This design would let a later study estimate whether the richer observation works "
        "reliably across independently trained policies and different traffic conditions. It is a proposed protocol; none "
        "of these additional runs or analyses were performed for the present pilot."
    )

    doc.core_properties.title = "A Pilot Comparison of State Representations for DQN Traffic Signal Control"
    doc.core_properties.author = "Nikshay Kumar Nagda; Aashutosh Nagda; Neel Soni; Keiyur Savani"
    doc.core_properties.subject = "Single-intersection DQN traffic signal state-complexity pilot"
    doc.core_properties.keywords = "DQN, traffic signals, state representation, SUMO"
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
