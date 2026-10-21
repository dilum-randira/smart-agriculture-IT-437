"""Standard encoder/decoder LSTM and explicitly element-masked optimization."""
import keras
import tensorflow as tf


from ...common.masked_loss import masked_squared_error, ValidElementMSE


def build_forecaster(units=32):
    inputs = keras.Input(shape=(336,3), name="historical_microclimate")
    x = keras.layers.LSTM(units, name="encoder_lstm")(inputs)
    x = keras.layers.RepeatVector(168, name="repeat_168_hours")(x)
    x = keras.layers.LSTM(units, return_sequences=True, name="decoder_lstm")(x)
    outputs = keras.layers.TimeDistributed(keras.layers.Dense(3), name="three_targets")(x)
    return keras.Model(inputs, outputs, name="standard_lstm_336_to_168")


@keras.saving.register_keras_serializable(package="c2")
class MaskedLSTM(keras.Model):
    def __init__(self, units=32, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.forecaster = build_forecaster(units)
        self.loss_tracker = ValidElementMSE()

    def build(self, input_shape):
        self.forecaster.build(input_shape)
        super().build(input_shape)

    def call(self, inputs, training=False):
        # Only historical X enters the network. Target masks are supervision.
        return self.forecaster(inputs, training=training)

    @property
    def metrics(self):
        return [self.loss_tracker]

    def train_step(self, data):
        x, y, mask = keras.utils.unpack_x_y_sample_weight(data)
        if mask is None:
            raise ValueError("target_valid_mask is required for training")
        with tf.GradientTape() as tape:
            prediction = self(x, training=True)
            loss, squared_sum, count = masked_squared_error(y, prediction, mask)
        gradients = tape.gradient(loss, self.trainable_variables)
        pairs = [(g,v) for g,v in zip(gradients,self.trainable_variables) if g is not None]
        for g,_ in pairs:
            tf.debugging.assert_all_finite(g, "Non-finite masked gradient")
        if not self.optimizer.built:
            self.optimizer.build(self.trainable_variables)

        def update():
            self.optimizer.apply_gradients(pairs)
            return tf.constant(1)

        # No optimizer/momentum update for an empty supervision batch.
        tf.cond(count > 0, update, lambda: tf.constant(0))
        self.loss_tracker.update_state(squared_sum, count)
        return {"loss": self.loss_tracker.result()}

    def test_step(self, data):
        x, y, mask = keras.utils.unpack_x_y_sample_weight(data)
        if mask is None:
            raise ValueError("target_valid_mask is required for validation")
        _, squared_sum, count = masked_squared_error(y, self(x, training=False), mask)
        self.loss_tracker.update_state(squared_sum, count)
        return {"loss": self.loss_tracker.result()}

    def get_config(self):
        return {**super().get_config(), "units": self.units}
