"""Package and CLI compatibility checks; never execute experiment runners."""
from contextlib import redirect_stdout
from importlib import import_module
import io
import unittest
from unittest.mock import patch

from ....common.paths import BACKEND, SOURCE


class RefactorTests(unittest.TestCase):
    def test_legacy_symbols_keep_identity(self):
        pairs = {
            'pipeline': ('preprocessing.pipeline', 'Config'),
            'scaling': ('preprocessing.scaling', 'Standardizer'),
            'lstm_model': ('models.lstm.model', 'MaskedLSTM'),
            'train_lstm': ('models.lstm.train', 'run'),
            'infer_lstm': ('models.lstm.inference', 'infer'),
            'lstm_evaluation': ('models.lstm.evaluation', 'metric_row'),
            'lstm_reporting': ('models.lstm.reporting', 'write_reports'),
            'verify_lstm_artifacts': ('models.lstm.verification', 'verify'),
        }
        for old, (new, symbol) in pairs.items():
            with self.subTest(module=old):
                self.assertIs(getattr(import_module('app.c2.microclimate.'+old), symbol),
                              getattr(import_module('app.c2.microclimate.'+new), symbol))

    def test_private_legacy_helpers_are_accessible(self):
        old = import_module('app.c2.microclimate.pipeline')
        new = import_module('app.c2.microclimate.preprocessing.pipeline')
        self.assertIs(old._window_arrays, new._window_arrays)

    def test_paths_still_resolve_to_existing_backend(self):
        self.assertEqual(BACKEND.name, 'backend')
        self.assertTrue((BACKEND/'app/main.py').is_file())
        self.assertTrue(SOURCE.is_file())
        from ....common.data import DATA
        self.assertTrue((DATA/'scalers.json').is_file())

    def test_legacy_and_canonical_cli_help_is_safe(self):
        pairs = {
            'run_phase1': 'preprocessing.run_phase1',
            'run_phase1_masked': 'preprocessing.run_phase1_masked',
            'run_phase1_scaled': 'preprocessing.run_phase1_scaled',
            'train_lstm': 'models.lstm.train',
            'infer_lstm': 'models.lstm.inference',
            'lstm_reporting': 'models.lstm.reporting',
            'verify_lstm_artifacts': 'models.lstm.verification',
        }
        for name in list(pairs)+list(pairs.values()):
            with self.subTest(module=name), patch('sys.argv', [name, '--help']), redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit) as status:
                    import_module('app.c2.microclimate.'+name).main()
                self.assertEqual(status.exception.code, 0)
                self.assertIn('usage:', output.getvalue())

    def test_custom_serialization_names_are_preserved(self):
        import keras
        from ..model import MaskedLSTM, ValidElementMSE, masked_squared_error
        from ....common.masked_loss import ValidElementMSE as SharedMetric
        from ....common.masked_loss import masked_squared_error as shared_loss
        self.assertIs(ValidElementMSE, SharedMetric)
        self.assertIs(masked_squared_error, shared_loss)
        self.assertEqual(keras.saving.get_registered_name(MaskedLSTM), 'c2>MaskedLSTM')
        self.assertEqual(keras.saving.get_registered_name(SharedMetric), 'c2>ValidElementMSE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
