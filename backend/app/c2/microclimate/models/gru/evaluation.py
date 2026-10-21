"""Held-out three-model comparison on identical original-unit target positions."""
import numpy as np
import pandas as pd

from ...common.data import EXPECTED, load_node
from ...common.paths import BACKEND, SCALED_OUTPUT as DATA
from ...preprocessing.pipeline import LABEL, TARGETS
from ..lstm.evaluation import batched_predictions, evaluate_forecasts

LSTM_OUTPUT = BACKEND / 'experiments/c2/microclimate/lstm_v1'


def assert_comparable(actual, persistence, mask, origins, reference):
    """Fail rather than compare different labels, masks, origins or references."""
    np.testing.assert_array_equal(mask, reference['target_valid_mask'])
    np.testing.assert_array_equal(origins, reference['forecast_origin_unix_ns'])
    np.testing.assert_array_equal(actual[mask], reference['actual_original_units'][mask])
    np.testing.assert_array_equal(persistence, reference['persistence_original_units'])


def evaluate_selected(model, output, scalers, batch_size=16):
    sets, lstm_sets = [], []
    for node in EXPECTED['test']:
        x, y, mask, origins = load_node('test', node)
        scaled = batched_predictions(model, x, batch_size)
        actual = scalers['target'].inverse_transform(y, TARGETS)
        predicted = scalers['target'].inverse_transform(scaled, TARGETS)
        persistence = np.repeat(scalers['input'].inverse_transform(x[:, -1:, :], TARGETS), 168, axis=1)
        with np.load(LSTM_OUTPUT/f'test_predictions_{node}.npz', allow_pickle=False) as reference:
            assert_comparable(actual, persistence, mask, origins, reference)
            lstm_sets.append(reference['predictions_original_units'].copy())
        np.savez_compressed(output/f'test_predictions_{node}.npz',
                            predictions_scaled=scaled, predictions_original_units=predicted,
                            actual_original_units=actual, persistence_original_units=persistence,
                            target_valid_mask=mask, forecast_origin_unix_ns=origins,
                            targets=np.array(TARGETS), evaluation_label=np.array(LABEL),
                            actual_placeholder_warning=np.array('mask=False values are placeholders, not ground truth'))
        sets.append((node, actual, predicted, persistence, mask, origins))
    cohorts = [(s[0], s[1], s[2], s[3], s[4], lp) for s, lp in zip(sets, lstm_sets)]
    cohorts.append(('POOLED', *[np.concatenate([s[j] for s in sets]) for j in (1, 2, 3, 4)], np.concatenate(lstm_sets)))
    rows, leads = [], []
    for node, actual, gru, persistence, mask, lstm in cohorts:
        for name, prediction in [('Persistence', persistence), ('LSTM', lstm), ('GRU', gru)]:
            r, l = evaluate_forecasts(actual, prediction, mask, name, node)
            rows.extend(r); leads.extend(l)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(output/'test_metrics.csv', index=False)
    pd.DataFrame(leads).to_csv(output/'test_lead_metrics.csv', index=False)
    keys = ['node', 'target', 'unit', 'window_hours']
    comparison = None
    for name in ('Persistence', 'LSTM', 'GRU'):
        part = metrics[metrics.model.eq(name)].drop(columns=['model'])
        part = part.rename(columns={c: f'{c}_{name.lower()}' for c in part.columns if c not in keys})
        comparison = part if comparison is None else comparison.merge(part, on=keys, validate='one_to_one')
    assert (comparison.valid_observations_persistence == comparison.valid_observations_lstm).all()
    assert (comparison.valid_observations_gru == comparison.valid_observations_lstm).all()
    comparison['evaluation_label'] = LABEL
    comparison.to_csv(output/'three_model_comparison.csv', index=False)
    reference = pd.read_csv(LSTM_OUTPUT/'test_metrics.csv')
    for row in metrics[metrics.model.ne('GRU')].itertuples():
        prior = reference[reference.model.eq(row.model) & reference.node.eq(row.node) & reference.target.eq(row.target) & reference.window_hours.eq(row.window_hours)].iloc[0]
        assert row.valid_observations == prior.valid_observations
        for key in ('MAE', 'RMSE', 'R2'):
            np.testing.assert_allclose(getattr(row, key), prior[key], rtol=0, atol=1e-9)
    return metrics, comparison, sets
