"""Disposable fixtures; no research model training or experiment writes."""
from pathlib import Path
import tempfile
import unittest
import inspect

import keras
import numpy as np
import tensorflow as tf

from ..model import MaskedAttentionBiLSTM,TemporalAttention
from ...lstm.model import MaskedLSTM
from ....common.masked_loss import masked_squared_error


class AttentionTests(unittest.TestCase):
    def test_architecture_shape_and_parameter_count(self):
        model=MaskedAttentionBiLSTM()
        p=model(np.zeros((2,336,3),np.float32),training=False).numpy()
        self.assertEqual(p.shape,(2,168,3));self.assertTrue(np.isfinite(p).all())
        self.assertEqual(model.forecaster.count_params(),30040)
        self.assertEqual([type(l).__name__ for l in model.forecaster.layers],['InputLayer','Bidirectional','TemporalAttention','Dense','Dense','Reshape'])
        self.assertEqual(len(model.trainable_variables),13)
        self.assertEqual(model.forecaster.get_layer('temporal_attention').count_params(),2112)

    def test_attention_formula_against_numpy(self):
        states=np.array([[[1.,0.],[0.,1.],[-1.,2.]]],np.float32)
        attention=TemporalAttention(2);attention(states)
        attention.projection.set_weights([np.eye(2,dtype=np.float32),np.zeros(2,np.float32)])
        attention.score.set_weights([np.array([[1.],[2.]],np.float32)])
        scores=(np.tanh(states)@np.array([[1.],[2.]],np.float32))[...,0]
        weights=np.exp(scores-scores.max(axis=1,keepdims=True));weights/=weights.sum(axis=1,keepdims=True)
        np.testing.assert_allclose(attention.attention_weights(states).numpy(),weights,rtol=0,atol=1e-6)
        np.testing.assert_allclose(attention(states).numpy(),(states*weights[...,None]).sum(axis=1),rtol=0,atol=1e-6)

    def test_attention_shape_nonnegative_finite_normalized(self):
        model=MaskedAttentionBiLSTM(units=2)
        x=np.random.default_rng(42).normal(size=(2,336,3)).astype('float32')
        model(x);weights=model.attention_weights(x).numpy()
        self.assertEqual(weights.shape,(2,336));self.assertTrue(np.isfinite(weights).all())
        self.assertTrue((weights>=0).all())
        np.testing.assert_allclose(weights.sum(axis=1),1.,rtol=0,atol=1e-6)

    def test_zero_score_uniform_attention_is_mean(self):
        states=np.arange(24,dtype=np.float32).reshape(2,4,3)
        attention=TemporalAttention(2);attention(states)
        attention.score.kernel.assign(tf.zeros_like(attention.score.kernel))
        np.testing.assert_allclose(attention.attention_weights(states).numpy(),.25,rtol=0,atol=1e-7)
        np.testing.assert_allclose(attention(states).numpy(),states.mean(axis=1),rtol=0,atol=1e-6)

    def test_attention_parameters_receive_finite_nonzero_gradients(self):
        states=tf.constant(np.random.default_rng(42).normal(size=(2,336,64)),tf.float32)
        attention=TemporalAttention()
        with tf.GradientTape() as tape:loss=tf.reduce_sum(tf.square(attention(states)))
        gradients=tape.gradient(loss,attention.trainable_variables)
        self.assertEqual(len(gradients),3)
        for gradient in gradients:
            self.assertIsNotNone(gradient);self.assertTrue(np.isfinite(gradient.numpy()).all())
            self.assertTrue(np.any(gradient.numpy()!=0))

    def test_full_model_gradients_are_finite(self):
        model=MaskedAttentionBiLSTM(units=2)
        x=tf.constant(np.random.default_rng(42).normal(size=(2,336,3)),tf.float32)
        with tf.GradientTape() as tape:
            p=model(x,training=True)
            loss,_,_=masked_squared_error(tf.ones_like(p),p,tf.ones_like(p,tf.bool))
        gradients=tape.gradient(loss,model.trainable_variables)
        for gradient in gradients:self.assertTrue(gradient is not None and np.isfinite(gradient.numpy()).all())

    def test_masked_labels_zero_loss_and_gradient(self):
        p=tf.Variable([1.,2.,3.]);y=tf.constant([0.,np.nan,1.]);mask=tf.constant([True,False,True])
        with tf.GradientTape() as tape:loss,_,count=masked_squared_error(y,p,mask)
        np.testing.assert_array_equal(tape.gradient(loss,p).numpy(),[1.,0.,2.])
        self.assertEqual(float(count),2);self.assertEqual(float(loss),2.5)

    def test_zero_label_batch_skips_optimizer(self):
        model=MaskedAttentionBiLSTM(units=2)
        model.compile(optimizer=keras.optimizers.Adam(.001,global_clipnorm=1.),jit_compile=False)
        x=tf.zeros((1,336,3));y=tf.ones((1,168,3));mask=tf.zeros_like(y,tf.bool)
        model(x);before=[v.numpy().copy() for v in model.trainable_variables]
        tf.function(model.train_step)((x,y,mask))
        self.assertEqual(int(model.optimizer.iterations),0)
        for a,b in zip(before,model.trainable_variables):np.testing.assert_array_equal(a,b.numpy())

    def test_validation_mask_denominator(self):
        model=MaskedAttentionBiLSTM(units=2)
        x=tf.zeros((1,336,3));y=np.ones((1,168,3),np.float32);mask=np.ones_like(y,bool)
        mask[:,0,:]=False;y[~mask]=np.nan
        result=model.test_step((x,y,mask))
        self.assertEqual(float(result['loss']),1.);self.assertEqual(int(model.loss_tracker.valid_count),501)

    def test_history_only_bidirectionality_and_no_y_input(self):
        model=MaskedAttentionBiLSTM(units=2);x=np.ones((1,336,3),np.float32)
        before=model(x,training=False).numpy()
        # Target arrays affect supervision only; forward API has no target argument.
        self.assertNotIn('y',inspect.signature(model.call).parameters)
        encoder=model.forecaster.get_layer('historical_bilstm')
        self.assertEqual(model.forecaster.input_shape,(None,336,3))
        self.assertTrue(encoder.backward_layer.go_backwards)
        self.assertTrue(encoder.forward_layer.return_sequences)
        masked_squared_error(tf.ones_like(before)*1e6,before,tf.ones_like(before,tf.bool))
        np.testing.assert_array_equal(before,model(x,training=False).numpy())

    def test_serialization_preserves_forecast_and_attention(self):
        model=MaskedAttentionBiLSTM(units=2)
        x=np.random.default_rng(42).normal(size=(2,336,3)).astype('float32')
        expected=model(x,training=False).numpy();weights=model.attention_weights(x).numpy()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.keras';model.save(path)
            restored=keras.models.load_model(path,compile=False)
            np.testing.assert_allclose(restored(x,training=False).numpy(),expected,rtol=0,atol=1e-6)
            np.testing.assert_allclose(restored.attention_weights(x).numpy(),weights,rtol=0,atol=1e-6)

    def test_shared_steps_and_registered_names(self):
        for name in ('train_step','test_step','call','build','get_config'):
            self.assertIs(getattr(MaskedAttentionBiLSTM,name),getattr(MaskedLSTM,name))
        self.assertEqual(keras.saving.get_registered_name(TemporalAttention),'c2>TemporalAttention')
        self.assertEqual(keras.saving.get_registered_name(MaskedAttentionBiLSTM),'c2>MaskedAttentionBiLSTM')


if __name__=='__main__':unittest.main(verbosity=2)
