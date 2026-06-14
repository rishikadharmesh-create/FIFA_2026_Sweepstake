"""
2026 FIFA World Cup format:
- 48 teams, 12 groups of 4 (A-L)
- Top 2 from each group + 8 best third-placed teams = 32 advance to Round of 32
- Single-elimination knockout from Round of 32 -> Final

NOTE: The actual group draw takes place in December 2025. This file contains
a PLACEHOLDER draw structure using the teams relevant to our 16 participants
plus filler teams to complete groups of 4, so the simulator can run end-to-end.

>>> REPLACE `GROUPS` BELOW WITH THE REAL DRAW once announced (Dec 2025). <<<
The simulation engine itself (bracket logic, Monte Carlo) does not need to change.
"""

# All 48 teams expected to be in the tournament (32 confirmed/likely qualifiers
# shown; remainder are placeholders "TBD_x" until qualification completes).
# Teams from our participants' assignments are included explicitly.

PARTICIPANT_TEAMS = [
    "Brazil", "Qatar", "Panama", "Argentina", "Sweden", "Iraq",
    "France", "Uruguay", "Tunisia", "England", "Ecuador", "Jordan",
    "Spain", "Morocco", "Bosnia and Herzegovina", "Portugal", "Japan", "South Africa",
    "Germany", "Colombia", "Haiti", "Netherlands", "Saudi Arabia", "Czechia",
    "Belgium", "Senegal", "Curacao", "Mexico", "Norway", "Algeria",
    "USA", "Ghana", "Switzerland", "Canada", "Croatia", "Uzbekistan",
    "Australia", "Egypt", "Paraguay", "Austria", "Korea Republic", "Cabo Verde",
    "Turkiye", "DR Congo", "New Zealand", "Iran", "Cote d'Ivoire", "Scotland",
]

# Placeholder group draw: simple seeding by Elo into 12 groups of 4.
# This will be overwritten by the real draw in December 2025.
def generate_placeholder_groups(elo_lookup):
    teams_sorted = sorted(PARTICIPANT_TEAMS, key=lambda t: -elo_lookup(t))
    groups = {chr(65 + i): [] for i in range(12)}  # Groups A-L
    # Snake draft into groups to balance strength
    for idx, team in enumerate(teams_sorted):
        group_idx = idx % 12
        groups[chr(65 + group_idx)].append(team)
    return groups


# Round of 32 bracket pairing template (by group position).
# Format follows FIFA's published 2026 bracket logic (R32 -> R16 -> QF -> SF -> Final)
# Using placeholder pairing: group winners/runners-up cross-paired, third-place
# teams fill remaining slots. This is simplified; real bracket will be confirmed
# closer to the tournament and slotted in here.
R32_PAIRING_TEMPLATE = [
    ("A1", "C3"), ("B2", "F1"), ("E1", "I3"), ("D2", "H1"),
    ("G1", "B3"), ("A2", "E3"), ("C1", "G3"), ("F2", "D1"),
    ("K1", "D3"), ("L2", "I1"), ("J1", "G2"), ("H2", "L1"),
    ("I2", "K3"), ("C2", "J3"), ("F3", "L3"), ("K2", "J2"),
]
