"""Transparent relative scoring of eligible harvest alternatives."""
from decimal import Decimal


def rank_preferences(comparison, income_priority=50):
    weight = Decimal(str(income_priority)) / 100
    if not weight.is_finite() or not 0 <= weight <= 1:
        raise ValueError("Income priority must be between 0 and 100.")
    result = {
        'status': comparison['feasibility']['status'],
        'income_weight': float(weight), 'water_weight': float(1 - weight),
        'preferred_dates': [], 'scores': [],
        'method': 'Min-max normalization among eligible options: income benefits higher returns; water benefits lower additional water. Equal values receive 1 for that criterion. Weighted score ranges from 0 to 1. Ties within 0.000000001 share first place.',
        'limitations': 'Relative preference scores are not confidence probabilities. Scores depend on the eligible options. Yield and daily irrigation are constant; inspect provenance for sample versus entered operating inputs. Losses and risk are not modeled. Returns are after selected costs, not full profit.',
    }
    if result['status'] == 'not_assessed':
        result['explanation'] = 'No preference recommendation: supply all three harvest-date and water limits first.'
    elif result['status'] == 'no_eligible_options':
        result['explanation'] = 'No eligible harvest option. Review the exclusion reasons and supplied limits; no option is recommended.'
    else:
        eligible = [r for r in comparison['scenarios'] if r['eligibility'] == 'eligible']
        returns = [Decimal(str(r['net_return_after_selected_costs_lkr'])) for r in eligible]
        waters = [Decimal(str(r['additional_irrigation_liters'])) for r in eligible]
        raw = []
        for row, value, water in zip(eligible, returns, waters):
            income = (value-min(returns))/(max(returns)-min(returns)) if max(returns) != min(returns) else Decimal(1)
            saving = (max(waters)-water)/(max(waters)-min(waters)) if max(waters) != min(waters) else Decimal(1)
            score = weight*income + (1-weight)*saving
            raw.append(score)
            result['scores'].append({'harvest_date': row['harvest_date'], 'income_score': float(income), 'water_score': float(saving), 'score': float(score)})
        best = max(raw)
        winners = [r for r, score in zip(eligible, raw) if abs(score-best) <= Decimal('0.000000001')]
        result['preferred_dates'] = [r['harvest_date'] for r in winners]
        result['status'] = 'tie' if len(winners) > 1 else 'recommended'
        details = '; '.join(f"{r['harvest_date']}: LKR {r['net_return_after_selected_costs_lkr']:,.2f} return after selected costs and {r['additional_irrigation_liters']:g} L additional water" for r in winners)
        reason = 'Only one option passes the supplied limits; priorities cannot change this choice.' if len(eligible) == 1 else ('These options tie; no unique choice is made.' if len(winners) > 1 else 'This option has the highest weighted score among eligible alternatives.')
        result['explanation'] = f"Income priority {float(weight)*100:g}%, water-saving priority {float(1-weight)*100:g}%. {reason} {details}."
    comparison['preference_ranking'] = result
    return comparison
