"""Historical-only BiLSTM encoder with learnable additive temporal attention."""
import keras
import tensorflow as tf

from ..lstm.model import MaskedLSTM
from ...common.masked_loss import ValidElementMSE


@keras.saving.register_keras_serializable(package="c2")
class TemporalAttention(keras.layers.Layer):
    """e_t=v^T tanh(W h_t+b); alpha=softmax_time(e); c=sum_t alpha_t h_t.

    One learned global scoring vector; attention projection width defaults to 32.
    Weights summarize historical encoder states, not causal effects or distinct
    per-target/per-horizon explanations. Causally forward-filled historical inputs
    are included, matching the fixed input policy of the learned baselines.
    """
    def __init__(self, attention_units=32, **kwargs):
        super().__init__(**kwargs)
        self.attention_units = attention_units
        self.projection = keras.layers.Dense(attention_units, activation="tanh", name="attention_projection")
        self.score = keras.layers.Dense(1, use_bias=False, name="attention_score")

    def build(self, input_shape):
        self.projection.build(input_shape)
        self.score.build((*input_shape[:-1], self.attention_units))
        super().build(input_shape)

    def attention_weights(self, states):
        return tf.squeeze(tf.nn.softmax(self.score(self.projection(states)), axis=1), axis=-1)

    def call(self, states):
        weights = self.attention_weights(states)
        return tf.reduce_sum(states * weights[..., None], axis=1)

    def get_config(self):
        return {**super().get_config(), "attention_units": self.attention_units}


def build_forecaster(units=32):
    inputs = keras.Input(shape=(336, 3), name="historical_microclimate")
    states = keras.layers.Bidirectional(
        keras.layers.LSTM(units, return_sequences=True), name="historical_bilstm")(inputs)
    context = TemporalAttention(attention_units=32, name="temporal_attention")(states)
    hidden = keras.layers.Dense(32, activation="relu", name="context_dense")(context)
    flat = keras.layers.Dense(168*3, name="future_three_targets")(hidden)
    outputs = keras.layers.Reshape((168, 3), name="forecast_168_hours")(flat)
    return keras.Model(inputs, outputs, name="attention_bilstm_336_to_168")


@keras.saving.register_keras_serializable(package="c2")
class MaskedAttentionBiLSTM(MaskedLSTM):
    """Reuse proven masked model steps; construct no baseline LSTM forecaster."""
    def __init__(self, units=32, **kwargs):
        keras.Model.__init__(self, **kwargs)
        self.units = units
        self.forecaster = build_forecaster(units)
        self.loss_tracker = ValidElementMSE()

    def attention_weights(self, historical_inputs):
        states = self.forecaster.get_layer("historical_bilstm")(historical_inputs, training=False)
        return self.forecaster.get_layer("temporal_attention").attention_weights(states)
