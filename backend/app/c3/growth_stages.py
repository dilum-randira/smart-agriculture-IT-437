"""Stage 5: crop growth stages and stage-dependent settings.

FAO-56 (chapter 6, Table 11) splits a season into four stages: initial,
development, mid-season and late season. Stage lengths for Nai Miris are
NOT known yet, so they are always passed in.

Why stage-aware irrigation: Jeeatid et al. (2018), Food Chemistry
245:792-797, found in Capsicum chinense that water stress applied after
anthesis (flowering) raised capsaicinoid concentration but reduced fruit
yield, and raised capsaicinoid yield only in some cultivars. So deficit
irrigation at flowering is a pungency-versus-yield trade-off, not a free gain.
"""

STAGES = ["initial", "development", "mid", "late"]   # FAO-56 Table 11 stage names


def growth_stage_for_day(day: int, l_ini: int, l_dev: int, l_mid: int, l_late: int) -> str:
    """FAO-56 growth stage on a day of the season (1 = first day after planting).

    Days after the end of the season count as 'late'.
    """
    if day <= l_ini:
        return "initial"
    if day <= l_ini + l_dev:
        return "development"
    if day <= l_ini + l_dev + l_mid:
        return "mid"
    return "late"


def daily_values_by_stage(n_days: int, stage_lengths: dict[str, int],
                          values_by_stage: dict[str, float]) -> list[float]:
    """One value per season day, taken from the value for that day's stage.

    Example: the allowed depletion fraction or the refill fraction for each
    stage. stage_lengths and values_by_stage need all four STAGES as keys.
    """
    for name, given in (("stage_lengths", stage_lengths), ("values_by_stage", values_by_stage)):
        missing = [s for s in STAGES if s not in given]
        if missing:
            raise ValueError(f"{name} is missing stages: {missing}")
    lengths = [stage_lengths[s] for s in STAGES]
    return [values_by_stage[growth_stage_for_day(day, *lengths)] for day in range(1, n_days + 1)]
