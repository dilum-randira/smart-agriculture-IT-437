from datetime import date
from decimal import Decimal


def assess_feasibility(comparison, earliest=None, latest=None, water=None):
    supplied = [value is not None for value in (earliest, latest, water)]
    if any(supplied) and not all(supplied):
        raise ValueError("Supply earliest_harvest_date, latest_harvest_date and available_water_liters together.")
    if all(supplied):
        if earliest > latest:
            raise ValueError("Earliest harvest date must be on or before the latest harvest date.")
        water = Decimal(str(water))
        if not water.is_finite() or water < 0:
            raise ValueError("Available water must be a finite non-negative number.")
    for scenario in comparison['scenarios']:
        reasons = []
        harvest_date = date.fromisoformat(scenario['harvest_date'])
        if all(supplied):
            if harvest_date < earliest:
                reasons.append(f"Before the supplied harvest-ready date ({earliest.isoformat()}).")
            if harvest_date > latest:
                reasons.append(f"After the latest acceptable harvest date ({latest.isoformat()}).")
            if Decimal(str(scenario['additional_irrigation_liters'])) > water:
                reasons.append(f"Needs {scenario['additional_irrigation_liters']:g} L of additional irrigation; only {water} L is available.")
        scenario['eligibility'] = 'not_assessed' if not any(supplied) else ('excluded' if reasons else 'eligible')
        scenario['exclusion_reasons'] = reasons
    eligible = [s for s in comparison['scenarios'] if s['eligibility'] == 'eligible']
    comparison['feasibility'] = {
        'status': 'not_assessed' if not any(supplied) else ('eligible_options' if eligible else 'no_eligible_options'),
        'eligible_count': len(eligible) if any(supplied) else None,
        'constraints': {'earliest_harvest_date': earliest.isoformat() if earliest else None,
                        'latest_harvest_date': latest.isoformat() if latest else None,
                        'available_water_liters': float(water) if water is not None else None},
        'scope': 'Checks only supplied readiness date, deadline and total additional irrigation water. Dates and water equality are allowed. Readiness is user supplied, not a crop-maturity prediction. Missing constraints mean not assessed, never unlimited.',
    }
    return comparison
