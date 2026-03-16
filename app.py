import math
import os
import random
import tempfile
from dataclasses import dataclass

import streamlit as st

# Optional computer vision imports for the squat review section
# The app still works even if these are not installed yet.
try:
    import cv2
    import mediapipe as mp
    CV_AVAILABLE = True
except Exception:
    CV_AVAILABLE = False


# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(page_title="Sportze.AI", layout="wide")
st.title("Sportze.AI")
st.caption("Generate more realistic sport-specific sessions and review squat form with video.")


# ----------------------------
# Helpers
# ----------------------------
def fmt_minutes(total_minutes: int) -> str:
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}min"
    if hours > 0:
        return f"{hours}h"
    return f"{mins}min"


def clamp(n, low, high):
    return max(low, min(high, n))


def choose(options):
    return random.choice(options)


def section(title, lines):
    out = [f"### {title}"]
    for line in lines:
        out.append(f"- {line}")
    return "\n".join(out)


def experience_multiplier(level: str) -> float:
    if level == "Beginner":
        return 0.85
    if level == "Intermediate":
        return 1.0
    return 1.15


def goal_tone(goal: str) -> str:
    mapping = {
        "Performance": "push performance while keeping quality high",
        "Technique": "clean up mechanics and quality",
        "Fitness": "build general fitness with good rhythm",
        "Return from break": "return gradually and avoid sudden load spikes",
        "Competition prep": "prepare with sharper, more specific work",
    }
    return mapping.get(goal, "train with quality and consistency")


def safety_notes(injury: str, pain: int):
    notes = []
    if injury != "No":
        notes.append("You reported a current or recent injury/limitation, so reduce volume and stop any drill that reproduces pain.")
    if pain >= 6:
        notes.append("Pain is moderate to high. This session should be conservative, and medical/physio clearance is strongly recommended before harder loading.")
    elif pain >= 3:
        notes.append("Keep intensity controlled and prioritize technique over speed or load.")
    else:
        notes.append("No significant pain reported, so the session can stay normal but still controlled.")
    return notes


# ----------------------------
# Data model
# ----------------------------
@dataclass
class AthleteProfile:
    sport: str
    level: str
    days_per_week: int
    available_minutes: int
    injury: str
    pain: int
    sport_goal: str
    extras: dict


# ----------------------------
# Gym generator
# ----------------------------
def generate_gym_session(profile: AthleteProfile) -> str:
    focus = profile.extras["gym_focus"]
    style = profile.extras["gym_style"]
    sport_specific = profile.extras["sport_specific"]
    target_sport = profile.extras.get("target_sport", "General")
    mins = profile.available_minutes
    mult = experience_multiplier(profile.level)

    warmup = [
        "5 min easy cardio (bike, treadmill walk, or row)",
        "Dynamic mobility: ankle rocks, hip openers, thoracic rotations",
        "Movement prep: 2 x 8 bodyweight squats, 2 x 6 reverse lunges each side, 2 x 8 band pull-aparts",
    ]

    main = []

    if focus == "Upper body":
        main = [
            "A1. Dumbbell bench press - 4 x 6-10",
            "A2. Chest-supported row - 4 x 8-12",
            "B1. Seated shoulder press - 3 x 8-10",
            "B2. Lat pulldown or assisted pull-up - 3 x 8-12",
            "C1. Cable face pull - 3 x 12-15",
            "C2. Biceps curl + rope triceps pressdown - 2-3 x 10-15 each",
        ]
    elif focus == "Lower body":
        main = [
            "A. Squat pattern (goblet squat, back squat, or front squat) - 4 x 5-8",
            "B. Romanian deadlift - 4 x 6-10",
            "C. Walking lunges - 3 x 8 each leg",
            "D. Leg curl - 3 x 10-12",
            "E. Calf raises - 3 x 12-20",
            "F. Core: dead bug or plank - 3 rounds",
        ]
    elif focus == "Full body":
        if style == "Strength":
            main = [
                "A. Trap-bar deadlift or squat - 4 x 4-6",
                "B. Dumbbell bench press - 4 x 6-8",
                "C. One-arm row - 3 x 8 each side",
                "D. Split squat - 3 x 8 each leg",
                "E. Shoulder external rotation or face pull - 2-3 x 12-15",
                "F. Farmer carry - 3 x 20-30 m",
            ]
        elif style == "Hypertrophy":
            main = [
                "A. Leg press or squat - 4 x 8-12",
                "B. Dumbbell incline press - 4 x 8-12",
                "C. Seated row - 4 x 8-12",
                "D. Romanian deadlift - 3 x 8-10",
                "E. Lateral raise - 3 x 12-15",
                "F. Core circuit - 3 rounds",
            ]
        else:
            main = [
                "A. Kettlebell or dumbbell squat - 3 x 10",
                "B. Push-up or machine chest press - 3 x 10-12",
                "C. Cable or machine row - 3 x 10-12",
                "D. Reverse lunges - 3 x 8 each leg",
                "E. Medicine-ball slams or battle ropes - 6 rounds of 20 sec work / 40 sec rest",
                "F. Core finisher - 3 rounds",
            ]
    else:  # sport-specific
        sport_blocks = {
            "Tennis": [
                "A. Split squat - 3 x 8 each leg",
                "B. Lateral bound stick landings - 3 x 5 each side",
                "C. Cable row - 3 x 10",
                "D. Half-kneeling press - 3 x 8 each side",
                "E. Rotational med-ball throw - 4 x 5 each side",
                "F. Copenhagen plank or side plank - 3 rounds",
            ],
            "Running": [
                "A. Goblet squat - 3 x 8",
                "B. Romanian deadlift - 3 x 8",
                "C. Step-ups - 3 x 8 each leg",
                "D. Single-leg calf raises - 3 x 15 each side",
                "E. Hamstring bridge curl - 3 x 10",
                "F. Pallof press - 3 x 10 each side",
            ],
            "Swimming": [
                "A. Lat pulldown - 4 x 8-10",
                "B. Dumbbell bench or push-up - 3 x 8-10",
                "C. Single-arm cable pull - 3 x 10 each side",
                "D. Rear delt fly - 3 x 12-15",
                "E. Split squat - 3 x 8 each leg",
                "F. Hollow hold - 3 x 20-30 sec",
            ],
            "Basketball": [
                "A. Trap-bar jump or box jump - 4 x 3-5",
                "B. Squat - 4 x 5-6",
                "C. Rear-foot elevated split squat - 3 x 8 each leg",
                "D. Pull-up or pulldown - 3 x 8-10",
                "E. Lateral shuffles / mini-band slides - 4 rounds",
                "F. Anti-rotation core - 3 rounds",
            ],
            "Baseball": [
                "A. Trap-bar deadlift - 4 x 4-6",
                "B. Split-stance cable row - 3 x 10 each side",
                "C. Landmine press - 3 x 8 each side",
                "D. Rotational med-ball scoop toss - 4 x 5 each side",
                "E. Shoulder external rotation - 3 x 12-15",
                "F. Side plank - 3 rounds",
            ],
            "General": [
                "A. Goblet squat - 3 x 8",
                "B. Dumbbell press - 3 x 8-10",
                "C. Cable row - 3 x 10",
                "D. Reverse lunge - 3 x 8 each leg",
                "E. Carry variation - 3 rounds",
                "F. Core - 3 rounds",
            ],
        }
        main = sport_blocks.get(target_sport, sport_blocks["General"])

    if mins < 45:
        main = main[:4]
    elif mins >= 75:
        main.append("Optional finisher: 8 min easy conditioning bike/row + breathing cooldown")

    cooldown = [
        "5 min easy cooldown",
        "Stretch the main worked areas for 20-30 sec each",
        "Finish with 1-2 min relaxed breathing",
    ]

    txt = [
        f"## Your Gym Session",
        f"**Focus:** {focus}",
        f"**Style:** {style}",
        f"**Goal:** {profile.sport_goal}",
        f"**Load intention:** {goal_tone(profile.sport_goal)}",
        "",
        section("Warm-up", warmup),
        "",
        section("Main session", main),
        "",
        section("Cooldown", cooldown),
        "",
        "### Coaching notes",
    ]
    for n in safety_notes(profile.injury, profile.pain):
        txt.append(f"- {n}")
    txt.append(f"- Train around RPE {6 if profile.level == 'Beginner' else 7}/10 for most sets.")
    txt.append(f"- Rest around {60 if style != 'Strength' else 90}-{90 if style != 'Strength' else 150} seconds on most exercises.")
    if sport_specific == "Yes":
        txt.append(f"- The session was biased toward transfer to **{target_sport}**.")
    return "\n".join(txt)


# ----------------------------
# Running generator
# ----------------------------
def running_paces_text(event: str) -> str:
    if event == "100m dash":
        return "full recovery between quality sprint reps"
    if event in ["5k", "10k"]:
        return "controlled work on tempo, intervals, and aerobic support"
    if event in ["Half marathon", "Marathon"]:
        return "steady aerobic structure with long-run logic"
    return "mixed endurance and speed work"


def generate_running_session(profile: AthleteProfile) -> str:
    event = profile.extras["running_event"]
    run_goal = profile.extras["running_goal"]
    surface = profile.extras["surface"]
    mins = profile.available_minutes
    mult = experience_multiplier(profile.level)

    warmup = [
        "8-12 min easy jog",
        "Dynamic mobility: ankle mobility, leg swings, A-march, hip openers",
        "Drills: 2 x 20 m A-skip, 2 x 20 m straight-leg bound, 2 x 20 m high-knee run",
    ]

    main = []
    total_run_text = ""

    if event == "100m dash":
        session_type = choose(["Acceleration", "Max velocity", "Speed endurance", "Start technique"])
        if session_type == "Acceleration":
            main = [
                "4 x 10 m falling starts",
                "4 x 20 m acceleration sprints",
                "4 x 30 m sprints from 3-point or block-style start",
                "2 x 40 m build-ups at 90-95%",
                "Rest 2-4 min between quality reps",
            ]
        elif session_type == "Max velocity":
            main = [
                "4 x 20 m build-up + 20 m fast zone",
                "4 x flying 30 m (20 m build / 30 m sprint)",
                "3 x 60 m relaxed-fast stride at around 90-95%",
                "Rest fully between reps so speed stays high",
            ]
        elif session_type == "Speed endurance":
            main = [
                "3 x 80 m at strong but controlled race-specific effort",
                "2 x 120 m at smooth speed-endurance rhythm",
                "3 x 40 m relaxed accelerations",
                "Long rest between reps",
            ]
        else:
            main = [
                "6 x block or 3-point starts over 10-20 m",
                "4 x reaction starts on a clap or voice cue",
                "4 x 30 m acceleration runs",
                "2 x 60 m smooth sprint rhythm",
            ]
        total_run_text = "Main running volume: short high-quality sprint reps with full recoveries."

    elif event in ["5k", "10k"]:
        session_type = choose(["Tempo", "Cruise intervals", "VO2 intervals", "Easy run + strides"])
        if session_type == "Tempo":
            work = clamp(int(mins * 0.45), 18, 35)
            main = [
                f"Run {work} min continuously at comfortably hard tempo effort",
                "Then 4 x 20 sec relaxed fast strides with full walk-back recovery",
            ]
            total_run_text = f"Main running target: about {fmt_minutes(work)} of tempo work."
        elif session_type == "Cruise intervals":
            reps = 4 if mins < 60 else 5
            main = [
                f"{reps} x 5 min at threshold effort with 90 sec easy jog recovery",
                "Finish with 4 x 15 sec quick relaxed strides",
            ]
            total_run_text = f"Main running target: {reps * 5} min of threshold intervals."
        elif session_type == "VO2 intervals":
            reps = 5 if profile.level != "Beginner" else 4
            main = [
                f"{reps} x 3 min strong interval effort with 2 min easy jog",
                "Then 5-8 min very easy jogging",
            ]
            total_run_text = f"Main running target: {reps * 3} min of interval work."
        else:
            easy = clamp(int(mins * 0.65), 20, 50)
            main = [
                f"Run {fmt_minutes(easy)} easy conversational pace",
                "Then 6 x 15 sec strides with full recovery",
            ]
            total_run_text = f"Main running target: {fmt_minutes(easy)} easy running."

    elif event == "Half marathon":
        session_type = choose(["Long run", "Tempo blocks", "Progression run", "Easy run + strides"])
        if session_type == "Long run":
            run_minutes = clamp(int(mins * 0.75), 45, 120)
            main = [
                f"Run {fmt_minutes(run_minutes)} steadily at easy to moderate long-run effort",
                "In the final 15 min, gradually lift the pace slightly if you feel smooth",
            ]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} long run."
        elif session_type == "Tempo blocks":
            main = [
                "3 x 10 min at half-marathon rhythm with 3 min easy jog",
                "Finish with 10 min easy jog",
            ]
            total_run_text = "Main running target: 30 min of half-marathon pace work."
        elif session_type == "Progression run":
            run_minutes = clamp(int(mins * 0.7), 40, 90)
            main = [
                f"Run {fmt_minutes(run_minutes)} total",
                "First third easy, middle third steady, final third moderately hard but controlled",
            ]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} progression run."
        else:
            easy = clamp(int(mins * 0.6), 35, 70)
            main = [
                f"Run {fmt_minutes(easy)} easy aerobic pace",
                "Then 6 x 20 sec strides",
            ]
            total_run_text = f"Main running target: {fmt_minutes(easy)} easy run."

    elif event == "Marathon":
        session_type = choose(["Long run", "Marathon-pace blocks", "Steady aerobic run", "Recovery run"])
        if session_type == "Long run":
            run_minutes = clamp(int(mins * 0.8), 60, 210)
            main = [
                f"Run {fmt_minutes(run_minutes)} total",
                "Keep the first half easy and smooth",
                "Optionally include the last 20-30 min at steady marathon effort if you feel good",
            ]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} long run."
        elif session_type == "Marathon-pace blocks":
            blocks = 2 if mins < 90 else 3
            block_minutes = 15 if mins < 120 else 20
            main = [
                f"{blocks} x {block_minutes} min at marathon effort with 5 min easy jog between blocks",
                "Jog easy to cool down after the final block",
            ]
            total_run_text = f"Main running target: {blocks * block_minutes} min at marathon effort."
        elif session_type == "Steady aerobic run":
            run_minutes = clamp(int(mins * 0.72), 50, 120)
            main = [
                f"Run {fmt_minutes(run_minutes)} at smooth steady aerobic effort",
                "Stay relaxed and do not force the pace",
            ]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} steady aerobic running."
        else:
            run_minutes = clamp(int(mins * 0.55), 30, 60)
            main = [
                f"Run {fmt_minutes(run_minutes)} very easy conversational pace",
                "Finish feeling fresher than when you started",
            ]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} recovery running."

    else:
        session_type = choose(["Easy run", "Strides", "Mixed fartlek"])
        if session_type == "Easy run":
            run_minutes = clamp(int(mins * 0.6), 25, 60)
            main = [f"Run {fmt_minutes(run_minutes)} easy pace"]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} easy running."
        elif session_type == "Strides":
            run_minutes = clamp(int(mins * 0.45), 20, 40)
            main = [
                f"Run {fmt_minutes(run_minutes)} easy pace",
                "Then 6 x 20 sec relaxed strides with full recovery",
            ]
            total_run_text = f"Main running target: {fmt_minutes(run_minutes)} easy running plus strides."
        else:
            main = [
                "10 min easy",
                "8 x 1 min brisk / 1 min easy",
                "10-15 min easy cool run",
            ]
            total_run_text = "Main running target: short fartlek session."

    cooldown = [
        "5-10 min walk or light jog",
        "Calf, hip flexor, and hamstring mobility",
    ]

    txt = [
        "## Your Running Session",
        f"**Event focus:** {event}",
        f"**Primary goal:** {run_goal}",
        f"**Surface:** {surface}",
        f"**Training emphasis:** {running_paces_text(event)}",
        "",
        section("Warm-up", warmup),
        "",
        section("Main session", main),
        "",
        section("Cooldown", cooldown),
        "",
        "### Coaching notes",
        f"- {total_run_text}",
        "- Session descriptions use distance/reps or hour-style time, so you do not have to mentally convert big minute totals.",
        "- Keep sprint work crisp; once speed drops clearly, stop the rep quality block.",
    ]
    for n in safety_notes(profile.injury, profile.pain):
        txt.append(f"- {n}")
    return "\n".join(txt)


# ----------------------------
# Swimming generator
# ----------------------------
def generate_swimming_session(profile: AthleteProfile) -> str:
    event = profile.extras["swim_event"]
    stroke = profile.extras["stroke"]
    swim_goal = profile.extras["swim_goal"]
    mins = profile.available_minutes

    warmup = [
        "200-400m easy swim",
        "4 x 50m drill/swim by 25m",
        "4 x 25m kick with controlled effort",
    ]

    if event == "50m":
        main = choose([
            [
                "8 x 25m from push, fast but technically clean, 45-60 sec rest",
                "6 x 15m breakout focus",
                "4 x 50m easy recovery swim",
            ],
            [
                "6 x 25m sprint from push with full recovery",
                "4 x 50m as 25 fast / 25 easy",
                "4 x 15m start + acceleration focus",
            ],
        ])
    elif event == "100m":
        main = choose([
            [
                "8 x 50m at race-pace control with 30-45 sec rest",
                "4 x 25m fast with full recovery",
                "4 x 50m easy loosen",
            ],
            [
                "4 x 75m as 50 strong + 25 easy",
                "6 x 25m sprint with clean turns",
                "200m easy recovery",
            ],
        ])
    elif event == "200m":
        main = choose([
            [
                "6 x 100m at controlled threshold effort with 20-30 sec rest",
                "4 x 50m race-pace feel",
                "200m easy loosen",
            ],
            [
                "3 x 200m as negative split",
                "6 x 25m fast but smooth",
                "100-200m easy recovery",
            ],
        ])
    else:
        main = choose([
            [
                "8 x 50m technique focus",
                "6 x 100m aerobic steady pace",
                "4 x 25m build to fast",
            ],
            [
                "12 x 50m as 1 easy / 1 moderate / 1 strong repeated",
                "200m pull easy",
                "4 x 25m kick strong",
            ],
        ])

    cooldown = [
        "100-200m very easy swim",
        "Light shoulder mobility after leaving the pool",
    ]

    txt = [
        "## Your Swimming Session",
        f"**Event focus:** {event}",
        f"**Stroke:** {stroke}",
        f"**Primary goal:** {swim_goal}",
        "",
        section("Warm-up", warmup),
        "",
        section("Main set", main),
        "",
        section("Cooldown", cooldown),
        "",
        "### Coaching notes",
        "- The app now includes 50m, 100m, and 200m event options directly.",
        "- Sprint sets should keep stroke quality, line, and turns organized instead of becoming sloppy.",
    ]
    for n in safety_notes(profile.injury, profile.pain):
        txt.append(f"- {n}")
    return "\n".join(txt)


# ----------------------------
# Tennis generator
# ----------------------------
def generate_tennis_session(profile: AthleteProfile) -> str:
    focus = profile.extras["tennis_focus"]
    hand = profile.extras["playing_hand"]
    mins = profile.available_minutes

    warmup = [
        "5 min light jog and side shuffles",
        "Dynamic mobility: hips, thoracic spine, shoulders",
        "Split-step rhythm + shadow swings for 5 min",
    ]

    if focus == "Baseline consistency":
        main = [
            "10 min cooperative cross-court forehand rally",
            "10 min cooperative cross-court backhand rally",
            "4 x 4 min deep cross-court patterns with 90 sec rest",
            "10 min live points starting with cross-court feed",
        ]
    elif focus == "Serve + first ball":
        main = [
            "10 min serve mechanics and target work",
            "4 x 8 first serves to target zones",
            "4 x 6 second serves with shape and margin",
            "12 min serve + first forehand pattern",
            "8 min points starting from serve",
        ]
    elif focus == "Movement":
        main = [
            "4 x 30 sec split-step + recovery footwork",
            "4 x 4-ball wide recovery pattern",
            "10 min approach + recover sequences",
            "10 min live points with movement emphasis",
        ]
    else:
        main = [
            "8 min volley technique and touch",
            "8 min overhead repetitions",
            "10 min approach + volley patterns",
            "10 min transition points",
        ]

    cooldown = [
        "Easy walk and breathing 2-3 min",
        "Calf, hip, and shoulder mobility",
    ]

    txt = [
        "## Your Tennis Session",
        f"**Focus:** {focus}",
        f"**Playing hand:** {hand}",
        "",
        section("Warm-up", warmup),
        "",
        section("Main session", main),
        "",
        section("Cooldown", cooldown),
        "",
        "### Coaching notes",
        "- Build quality through repetition first, then add speed and point pressure.",
    ]
    for n in safety_notes(profile.injury, profile.pain):
        txt.append(f"- {n}")
    return "\n".join(txt)


# ----------------------------
# Basketball generator
# ----------------------------
def generate_basketball_session(profile: AthleteProfile) -> str:
    focus = profile.extras["basketball_focus"]
    position = profile.extras["basketball_position"]
    mins = profile.available_minutes

    warmup = [
        "2-3 court lengths easy jog",
        "Dynamic warm-up: skips, lunges, hip openers, ankle prep",
        "2 x down-and-back defensive slides",
        "2 x down-and-back dribble warm-up (right hand / left hand)",
    ]

    if focus == "Shooting":
        main = [
            "4 full-court sprints with walk-back recovery",
            "5 min form shooting close to the basket",
            "15 min three-point shooting from 5 spots",
            "10 min free throws in sets of 10",
            "10 min catch-and-shoot or off-the-dribble game shots",
        ]
    elif focus == "Ball handling":
        main = [
            "3 x 30 sec stationary pound dribbles each hand",
            "3 x 30 sec crossover / between / behind combo work",
            "6 full-court dribble attacks alternating hands",
            "10 min cone change-of-direction dribbling",
            "10 min live dribble into finish or pull-up",
        ]
    elif focus == "Finishing":
        main = [
            "5 min footwork finishes around the rim",
            "4 x 8 layups each side using different takes",
            "4 x 6 finishing through contact or pad pressure",
            "10 min euro-step / floater / reverse finish work",
            "8 min drive-and-finish live reps",
        ]
    elif focus == "Defense + conditioning":
        main = [
            "6 x defensive slide lane-to-lane",
            "4 x closeout + contest sequences",
            "4 x full-court sprint then backpedal return",
            "10 min shell-style defensive movement or mirror drill",
            "8-10 min controlled conditioning with the ball",
        ]
    else:
        main = [
            "5 min form shooting",
            "8 min ball-handling series",
            "4 full-court sprints",
            "10 min finishing around the basket",
            "10 min three-point or midrange game shots",
            "10 min free throws and pressure makes",
        ]

    cooldown = [
        "2 min easy walk",
        "Ankles, calves, hips, and adductors mobility",
    ]

    txt = [
        "## Your Basketball Session",
        f"**Focus:** {focus}",
        f"**Position:** {position}",
        "",
        section("Warm-up", warmup),
        "",
        section("Main session", main),
        "",
        section("Cooldown", cooldown),
        "",
        "### Coaching notes",
        "- Basketball sessions were built around core skill buckets: ball handling, shooting, footwork/body control, explosiveness, and conditioning.",
        "- Track makes, not just attempts, especially in shooting sessions.",
    ]
    for n in safety_notes(profile.injury, profile.pain):
        txt.append(f"- {n}")
    return "\n".join(txt)


# ----------------------------
# Baseball generator
# ----------------------------
def generate_baseball_session(profile: AthleteProfile) -> str:
    focus = profile.extras["baseball_focus"]
    position = profile.extras["baseball_position"]
    mins = profile.available_minutes

    warmup = [
        "5 min easy jog and dynamic mobility",
        "Throwing prep: arm circles, band external rotation, scap activation",
        "Progressive throwing warm-up from short to moderate distance",
    ]

    if focus == "Hitting":
        main = [
            "10 swings dry or tee-work focusing on mechanics",
            "4 x 8 tee swings to line-drive contact",
            "4 x 6 front toss reps",
            "10 min live batting practice or machine timing work",
            "8 min situational hitting: opposite-field / gap / hit-and-run ideas",
        ]
    elif focus == "Fielding":
        main = [
            "10 min ready position and first-step reactions",
            "4 x 8 routine ground balls",
            "4 x 6 slow roller / charge plays",
            "4 x 6 fly-ball reads or route work",
            "8 min field-clean-transfer-throw sequences",
        ]
    elif focus == "Throwing / pitching":
        main = [
            "Progressive catch play",
            "6 x wrist-snap or release drills",
            "6 x rocker or step-behind throws",
            "Bullpen or flat-ground block: 15-25 controlled pitches with intent",
            "5 min pickoff / fielding position / cover responsibilities",
        ]
    elif focus == "Baserunning":
        main = [
            "6 x home-to-first runs with full effort and full recovery",
            "6 x first-step reaction starts",
            "8 min rounding first and second base efficiently",
            "8 min lead, secondary lead, and return mechanics",
            "6 min slide technique rehearsal if appropriate and supervised",
        ]
    else:
        main = [
            "8 min tee-work or front toss",
            "8 min ground ball fundamentals",
            "8 min fly-ball or route reading",
            "8 min progressive throwing",
            "6 x home-to-first acceleration runs",
        ]

    cooldown = [
        "Easy walk and breathing",
        "Shoulder, forearm, hips, and hamstring mobility",
    ]

    txt = [
        "## Your Baseball Session",
        f"**Focus:** {focus}",
        f"**Position:** {position}",
        "",
        section("Warm-up", warmup),
        "",
        section("Main session", main),
        "",
        section("Cooldown", cooldown),
        "",
        "### Coaching notes",
        "- Baseball sessions were built around the main development pillars used in youth/player development resources: hitting, throwing, fielding, and baserunning.",
        "- Keep throwing volume controlled when the arm is not fresh.",
    ]
    for n in safety_notes(profile.injury, profile.pain):
        txt.append(f"- {n}")
    return "\n".join(txt)


# ----------------------------
# Dispatcher
# ----------------------------
def generate_plan(profile: AthleteProfile) -> str:
    sport = profile.sport

    if sport == "Gym":
        return generate_gym_session(profile)
    if sport == "Running":
        return generate_running_session(profile)
    if sport == "Swimming":
        return generate_swimming_session(profile)
    if sport == "Tennis":
        return generate_tennis_session(profile)
    if sport == "Basketball":
        return generate_basketball_session(profile)
    if sport == "Baseball":
        return generate_baseball_session(profile)

    return "Sport not supported yet."


# ----------------------------
# Squat review
# ----------------------------
def calculate_angle(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c

    ba = (ax - bx, ay - by)
    bc = (cx - bx, cy - by)

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    norm_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    norm_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)

    if norm_ba == 0 or norm_bc == 0:
        return None

    cosine_angle = dot / (norm_ba * norm_bc)
    cosine_angle = max(-1.0, min(1.0, cosine_angle))
    angle = math.degrees(math.acos(cosine_angle))
    return angle


def analyze_squat_video(video_file) -> dict:
    if not CV_AVAILABLE:
        return {
            "status": "error",
            "message": "MediaPipe/OpenCV are not installed yet."
        }

    mp_pose = mp.solutions.pose
    frames = 0
    detected = 0
    knee_angles = []
    hip_depth_flags = 0

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_file.read())
        temp_path = tmp.name

    cap = cv2.VideoCapture(temp_path)

    try:
        with mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frames += 1
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)

                if not result.pose_landmarks:
                    continue

                detected += 1
                lm = result.pose_landmarks.landmark

                # Right side landmarks
                hip = (lm[24].x, lm[24].y)
                knee = (lm[26].x, lm[26].y)
                ankle = (lm[28].x, lm[28].y)
                shoulder = (lm[12].x, lm[12].y)

                angle = calculate_angle(hip, knee, ankle)
                if angle is not None:
                    knee_angles.append(angle)

                # Simple depth heuristic: hip lower than knee in image space means deeper squat
                # (y grows downward in image coordinates)
                if hip[1] > knee[1]:
                    hip_depth_flags += 1
    finally:
        cap.release()
        try:
            os.remove(temp_path)
        except Exception:
            pass

    if detected == 0:
        return {
            "status": "error",
            "message": "No pose landmarks were detected clearly enough."
        }

    avg_knee = sum(knee_angles) / len(knee_angles) if knee_angles else None
    min_knee = min(knee_angles) if knee_angles else None
    depth_ratio = hip_depth_flags / max(detected, 1)

    feedback = []
    if min_knee is not None:
        if min_knee < 75:
            feedback.append("You likely reached a deep squat position in at least some reps.")
        elif min_knee < 95:
            feedback.append("Depth looks moderate. You may be near parallel but not very deep.")
        else:
            feedback.append("Depth appears limited. You may be squatting high.")

    if depth_ratio > 0.35:
        feedback.append("Hip depth was below knee level in a meaningful portion of detected frames.")
    else:
        feedback.append("Hip depth was not consistently below knee level.")

    feedback.append("For a better review, film from the side with the full body visible and stable lighting.")

    return {
        "status": "ok",
        "frames": frames,
        "detected_frames": detected,
        "avg_knee_angle": round(avg_knee, 1) if avg_knee is not None else None,
        "min_knee_angle": round(min_knee, 1) if min_knee is not None else None,
        "feedback": feedback,
    }


# ----------------------------
# Sidebar - common questions
# ----------------------------
st.sidebar.header("Athlete profile")

sport = st.sidebar.selectbox(
    "What do you want to train?",
    ["Gym", "Running", "Swimming", "Tennis", "Basketball", "Baseball"],
)

level = st.sidebar.selectbox(
    "Training level",
    ["Beginner", "Intermediate", "Advanced"],
)

days_per_week = st.sidebar.slider(
    "How many days do you train per week?",
    min_value=1,
    max_value=7,
    value=3,
)

available_minutes = st.sidebar.slider(
    "How much time do you have for this session?",
    min_value=30,
    max_value=240,
    step=5,
    value=60,
)

injury = st.sidebar.selectbox(
    "Do you currently have any injury or limitation?",
    ["No", "Yes - mild", "Yes - moderate", "Yes - significant"],
)

pain = 0
if injury != "No":
    pain = st.sidebar.slider("Pain level today (0-10)", 0, 10, 2)

sport_goal = st.sidebar.selectbox(
    "What is your main goal for this sport right now?",
    ["Performance", "Technique", "Fitness", "Return from break", "Competition prep"],
)

extras = {}

# ----------------------------
# Sport-specific questions
# ----------------------------
st.subheader(f"{sport} questions")

if sport == "Gym":
    extras["gym_focus"] = st.selectbox(
        "Gym focus",
        ["Upper body", "Lower body", "Full body", "Sport-specific"],
    )
    extras["gym_style"] = st.selectbox(
        "Training style",
        ["Strength", "Hypertrophy", "Conditioning"],
    )
    extras["sport_specific"] = st.selectbox(
        "Do you want this gym session to be sport-specific?",
        ["No", "Yes"],
    )
    extras["target_sport"] = "General"
    if extras["sport_specific"] == "Yes":
        extras["target_sport"] = st.selectbox(
            "Which sport should the gym session support?",
            ["Tennis", "Running", "Swimming", "Basketball", "Baseball"],
        )

elif sport == "Running":
    extras["running_event"] = st.selectbox(
        "What running focus do you want?",
        ["100m dash", "5k", "10k", "Half marathon", "Marathon", "General endurance"],
    )
    extras["running_goal"] = st.selectbox(
        "What is your running goal?",
        ["Get faster", "Build endurance", "Race prep", "Return gradually", "General fitness"],
    )
    extras["surface"] = st.selectbox(
        "Main training surface",
        ["Track", "Road", "Treadmill", "Mixed"],
    )

elif sport == "Swimming":
    extras["swim_event"] = st.selectbox(
        "What event do you want to train for?",
        ["50m", "100m", "200m", "General swimming fitness"],
    )
    extras["stroke"] = st.selectbox(
        "Main stroke",
        ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Mixed"],
    )
    extras["swim_goal"] = st.selectbox(
        "What is your swimming goal?",
        ["Speed", "Technique", "Race prep", "Conditioning", "Return gradually"],
    )

elif sport == "Tennis":
    extras["tennis_focus"] = st.selectbox(
        "Main tennis focus",
        ["Baseline consistency", "Serve + first ball", "Movement", "Net play / transition"],
    )
    extras["playing_hand"] = st.selectbox(
        "Playing hand",
        ["Right-handed", "Left-handed"],
    )

elif sport == "Basketball":
    extras["basketball_focus"] = st.selectbox(
        "Main basketball focus",
        ["Shooting", "Ball handling", "Finishing", "Defense + conditioning", "All-around"],
    )
    extras["basketball_position"] = st.selectbox(
        "Main position",
        ["Guard", "Wing", "Forward", "Center", "Mixed / not sure"],
    )

elif sport == "Baseball":
    extras["baseball_focus"] = st.selectbox(
        "Main baseball focus",
        ["Hitting", "Fielding", "Throwing / pitching", "Baserunning", "All-around"],
    )
    extras["baseball_position"] = st.selectbox(
        "Main position",
        ["Pitcher", "Catcher", "Infield", "Outfield", "Mixed / not sure"],
    )

profile = AthleteProfile(
    sport=sport,
    level=level,
    days_per_week=days_per_week,
    available_minutes=available_minutes,
    injury=injury,
    pain=pain,
    sport_goal=sport_goal,
    extras=extras,
)

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Generate training session", use_container_width=True):
        plan = generate_plan(profile)
        st.session_state["generated_plan"] = plan

if "generated_plan" in st.session_state:
    st.markdown(st.session_state["generated_plan"])


# ----------------------------
# Video review section
# ----------------------------
st.divider()
st.header("Video review")
st.write("Upload a squat video for a basic form review.")

if not CV_AVAILABLE:
    st.info("MediaPipe/OpenCV not detected yet. The training generator still works normally.")

uploaded_video = st.file_uploader(
    "Upload squat video (.mp4, .mov, .avi)",
    type=["mp4", "mov", "avi"],
)

if uploaded_video is not None:
    st.video(uploaded_video)

    if st.button("Analyze squat video", use_container_width=True):
        result = analyze_squat_video(uploaded_video)

        if result["status"] == "error":
            st.error(result["message"])
        else:
            st.success("Analysis complete")
            st.write(f"Frames processed: {result['frames']}")
            st.write(f"Frames with pose detected: {result['detected_frames']}")
            st.write(f"Average knee angle: {result['avg_knee_angle']}")
            st.write(f"Deepest detected knee angle: {result['min_knee_angle']}")

            st.subheader("Feedback")
            for item in result["feedback"]:
                st.write(f"- {item}")
