"""Reusable element-masked TensorFlow loss and epoch accumulator."""
import keras
import tensorflow as tf


def masked_squared_error(y_true, y_pred, mask):
    """Select before arithmetic; false positions have exactly zero gradient."""
    mask = tf.cast(mask, tf.bool)
    tf.debugging.assert_equal(tf.shape(y_true), tf.shape(y_pred))
    tf.debugging.assert_equal(tf.shape(mask), tf.shape(y_true))
    actual = tf.boolean_mask(y_true, mask)
    predicted = tf.boolean_mask(y_pred, mask)
    tf.debugging.assert_all_finite(actual, "Non-finite eligible labels")
    tf.debugging.assert_all_finite(predicted, "Non-finite eligible predictions")
    errors = tf.cast(predicted, tf.float32)-tf.cast(actual, tf.float32)
    squared_sum = tf.reduce_sum(tf.square(errors))
    count = tf.cast(tf.size(errors), tf.float32)
    return tf.math.divide_no_nan(squared_sum, count), squared_sum, count


@keras.saving.register_keras_serializable(package="c2")
class ValidElementMSE(keras.metrics.Metric):
    """Epoch loss = total squared error / total valid elements, not batch mean."""
    def __init__(self, name="loss", dtype="float64", **kwargs):
        super().__init__(name=name, dtype=dtype, **kwargs)
        self.squared_sum = self.add_weight(name="squared_sum", initializer="zeros", dtype="float64")
        self.valid_count = self.add_weight(name="valid_count", initializer="zeros", dtype="float64")

    def update_state(self, squared_sum, count):
        self.squared_sum.assign_add(tf.cast(squared_sum, tf.float64))
        self.valid_count.assign_add(tf.cast(count, tf.float64))

    def result(self):
        return tf.math.divide_no_nan(self.squared_sum, self.valid_count)

    def reset_state(self):
        self.squared_sum.assign(0.)
        self.valid_count.assign(0.)


