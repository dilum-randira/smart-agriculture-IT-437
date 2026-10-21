"""Fixed standard GRU baseline using the established masked training protocol."""
import keras

from ..lstm.model import MaskedLSTM
from ...common.masked_loss import ValidElementMSE


def build_forecaster(units=32):
    inputs = keras.Input(shape=(336, 3), name="historical_microclimate")
    encoded = keras.layers.GRU(units, name="encoder_gru")(inputs)
    repeated = keras.layers.RepeatVector(168, name="repeat_168_hours")(encoded)
    decoded = keras.layers.GRU(units, return_sequences=True, name="decoder_gru")(repeated)
    outputs = keras.layers.TimeDistributed(keras.layers.Dense(3), name="three_targets")(decoded)
    return keras.Model(inputs, outputs, name="standard_gru_336_to_168")


@keras.saving.register_keras_serializable(package="c2")
class MaskedGRU(MaskedLSTM):
    """Reuse masked steps/build/call/config; instantiate only GRU layers.

    Initialize keras.Model directly to avoid creating/tracking an unused LSTM
    forecaster. The inherited methods operate only on forecaster/loss_tracker.
    No LSTM implementation or checkpoint is modified.
    """

    def __init__(self, units=32, **kwargs):
        keras.Model.__init__(self, **kwargs)
        self.units = units
        self.forecaster = build_forecaster(units)
        self.loss_tracker = ValidElementMSE()
