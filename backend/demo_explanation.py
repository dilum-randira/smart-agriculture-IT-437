"""Exact decision trace and re-scored preference scenarios; not SHAP or causal effects."""
from copy import deepcopy
from preferences import rank_preferences

def explain_decision(result):
    ranking=result['preference_ranking']
    scores={r['harvest_date']:r for r in ranking['scores']}
    trace=[]
    for r in result['scenarios']:
        score=scores.get(r['harvest_date'])
        trace.append({'date':r['harvest_date'],'eligible':r['eligibility']=='eligible',
            'exclusion_reasons':r.get('exclusion_reasons',[]),
            'yield_kg':r['harvestable_yield_kg'],'price_lkr_per_kg':r['price_lkr_per_kg'],
            'revenue_lkr':r['revenue_lkr'],'cost_lkr':r['total_selected_costs_lkr'],
            'return_lkr':r['net_return_after_selected_costs_lkr'],
            'income_contribution':score['income_score']*ranking['income_weight'] if score else None,
            'water_contribution':score['water_score']*ranking['water_weight'] if score else None,
            'total_score':score['score'] if score else None})
    alternatives=[]
    for weight in (0,50,100):
        trial=rank_preferences(deepcopy(result),weight)['preference_ranking']
        alternatives.append({'income_priority':weight,'preferred_dates':trial['preferred_dates'],'status':trial['status']})
    return {'kind':'exact decision calculation trace','rows':trace,'priority_sensitivity':alternatives,
            'limitation':'Explains arithmetic, constraints and ranking, not why the price model produced an individual prediction. Scores are not confidence. Sensitivity changes priorities only, holding all other inputs fixed.'}
