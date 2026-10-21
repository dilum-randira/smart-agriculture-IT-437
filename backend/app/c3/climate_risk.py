"""Stage 7: daily climate risk flags for the crop.

Each function takes one value per day and returns one True/False per day
(True = risk on that day). summarise_risk counts them for a season or plan.

"Water beyond field capacity" is detected from deep percolation > 0 in the
FAO-56 water balance (Stage 4). The bucket model has no saturated state, so
this is a PROXY for waterlogged soil.
"""

# Heat: Erickson, A.N. and Markhart, A.H. (2002) Flower developmental stage and
# organ sensitivity of bell pepper to elevated temperature. Plant, Cell &
# Environment 25(1):123-130. Buds held at 33 degC for 48 h or more had reduced
# fruit set. LIMITATION: the study used sustained 33 degC; here we compare it
# with the DAILY MAXIMUM temperature, which over-states the exposure.
HEAT_TMAX_C = 33.0

# Root rot (Phytophthora capsici): UC Statewide IPM Program, "Phytophthora Root
# and Crown Rot on Peppers and Eggplant": "soil saturation for as little as 5
# to 6 hours can result in infection" and "Optimum temperature for plant
# infection is 75 to 92 degF". Converted to degC: (F - 32) x 5 / 9.
ROOT_ROT_TMIN_C = (75.0 - 32.0) * 5.0 / 9.0     # 23.9 degC
ROOT_ROT_TMAX_C = (92.0 - 32.0) * 5.0 / 9.0     # 33.3 degC


def heat_risk_days(tmax_c: list[float]) -> list[bool]:
    """True on days when Tmax >= 33 degC (Erickson and Markhart, 2002)."""
    return [t >= HEAT_TMAX_C for t in tmax_c]


def drought_risk_days(ks: list[float]) -> list[bool]:
    """True on days with water stress, Ks < 1 (depletion beyond RAW, FAO-56 Eq. 84)."""
    return [k < 1.0 for k in ks]


def wet_days(deep_percolation_mm: list[float]) -> list[bool]:
    """True on days when water went beyond field capacity (PROXY for waterlogging)."""
    return [dp > 0.0 for dp in deep_percolation_mm]


def longest_wet_run_days(deep_percolation_mm: list[float]) -> int:
    """Longest run of consecutive days with water beyond field capacity."""
    longest = current = 0
    for wet in wet_days(deep_percolation_mm):
        current = current + 1 if wet else 0
        longest = max(longest, current)
    return longest


def waterlogging_risk_days(deep_percolation_mm: list[float], max_wet_days: int) -> list[bool]:
    """True on each day that extends a wet run beyond max_wet_days in a row.

    max_wet_days has NO default on purpose: the candidate value (2 days at
    flowering, Abdulrasaq and Arslan, 2026, Russ. J. Plant Physiol. 73(2):51)
    has not been confirmed from the paper yet.
    """
    flags = []
    run = 0
    for wet in wet_days(deep_percolation_mm):
        run = run + 1 if wet else 0
        flags.append(run > max_wet_days)
    return flags


def root_rot_risk_days(deep_percolation_mm: list[float], tmean_c: list[float]) -> list[bool]:
    """True on days with water beyond field capacity AND Tmean in the
    Phytophthora optimum range (UC IPM, 23.9-33.3 degC)."""
    return [wet and ROOT_ROT_TMIN_C <= t <= ROOT_ROT_TMAX_C
            for wet, t in zip(wet_days(deep_percolation_mm), tmean_c)]


def summarise_risk(tmax_c: list[float], tmean_c: list[float], ks: list[float],
                   deep_percolation_mm: list[float]) -> dict:
    """Risk counts for one schedule over a period (all inputs one value per day).

    Waterlogging is reported as the longest wet run, not a count, until the
    threshold is confirmed.
    """
    return {
        "heat_risk_days": sum(heat_risk_days(tmax_c)),
        "drought_risk_days": sum(drought_risk_days(ks)),
        "longest_wet_run_days": longest_wet_run_days(deep_percolation_mm),
        "root_rot_risk_days": sum(root_rot_risk_days(deep_percolation_mm, tmean_c)),
    }
