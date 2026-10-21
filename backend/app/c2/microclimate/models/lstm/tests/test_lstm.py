"""Small fixtures verify optimization semantics, not research performance."""
import tempfile
import unittest
from pathlib import Path

import keras
import numpy as np
import tensorflow as tf

from ..model import MaskedLSTM, ValidElementMSE, masked_squared_error
from ..evaluation import metric_row, evaluate_forecasts, batched_predictions


class LSTMTests(unittest.TestCase):
    def test_exact_architecture_and_finite_shape(self):
        model=MaskedLSTM()
        prediction=model(tf.zeros((2,336,3)),training=False)
        self.assertEqual(tuple(prediction.shape),(2,168,3))
        self.assertEqual(model.forecaster.count_params(),13027)
        self.assertEqual([l.__class__.__name__ for l in model.forecaster.layers],
                         ['InputLayer','LSTM','RepeatVector','LSTM','TimeDistributed'])
        self.assertTrue(bool(tf.reduce_all(tf.math.is_finite(prediction))))

    def test_masked_labels_and_exact_gradient(self):
        prediction=tf.Variable([[[1.,2.,3.],[4.,5.,6.]]])
        actual=tf.constant([[[0.,np.nan,0.],[np.nan,0.,np.nan]]])
        mask=tf.constant([[[True,False,True],[False,True,False]]])
        with tf.GradientTape() as tape:
            loss,sse,count=masked_squared_error(actual,prediction,mask)
        gradient=tape.gradient(loss,prediction).numpy()
        self.assertEqual(float(count),3); self.assertAlmostEqual(float(sse),35)
        self.assertAlmostEqual(float(loss),35/3,places=5)
        np.testing.assert_array_equal(gradient[~mask.numpy()],0)
        np.testing.assert_allclose(gradient[mask.numpy()],2*prediction.numpy()[mask.numpy()]/3)
        changed=tf.where(mask,actual,tf.constant(1e30))
        self.assertEqual(float(masked_squared_error(changed,prediction,mask)[0]),float(loss))

    def test_epoch_loss_uses_valid_element_weighting(self):
        tracker=ValidElementMSE()
        tracker.update_state(10.,2.);tracker.update_state(18.,3.)
        self.assertAlmostEqual(float(tracker.result()),28/5)
        tracker.reset_state();self.assertEqual(float(tracker.result()),0)

    def test_zero_valid_batch_skips_optimizer_and_finite_update(self):
        # Width-2 fixture tests the optimizer branch; full experiment always uses width 32.
        model=MaskedLSTM(units=2)
        model.compile(optimizer=keras.optimizers.Adam(.001,global_clipnorm=1.0),jit_compile=False)
        x=tf.zeros((1,336,3));y=tf.ones((1,168,3));mask=tf.zeros((1,168,3),tf.bool)
        model(x)
        original=[w.numpy().copy() for w in model.trainable_variables]
        step=tf.function(model.train_step)
        step((x,y,mask))
        self.assertEqual(int(model.optimizer.iterations),0)
        for a,b in zip(original,model.trainable_variables):np.testing.assert_array_equal(a,b.numpy())
        result=step((x,y,tf.ones_like(mask)))
        self.assertEqual(int(model.optimizer.iterations),1)
        self.assertTrue(np.isfinite(float(result['loss'])))

    def test_validation_uses_same_mask_weighted_tracker(self):
        model=MaskedLSTM(units=2)
        model.compile(optimizer='adam',jit_compile=False)
        x=tf.zeros((1,336,3)); y=tf.ones((1,168,3));m=tf.ones((1,168,3),tf.bool)
        result=model.test_step((x,y,m))
        self.assertAlmostEqual(float(result['loss']),1.)

    def test_save_reload_consistency_without_retraining(self):
        model=MaskedLSTM(units=2)
        x=np.random.default_rng(42).normal(size=(2,336,3)).astype('float32')
        expected=model(x,training=False).numpy()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.keras';model.save(path)
            restored=keras.models.load_model(path,compile=False)
            np.testing.assert_allclose(restored(x,training=False).numpy(),expected,rtol=0,atol=1e-6)

    def test_batched_inference(self):
        model=MaskedLSTM(units=2)
        x=np.zeros((3,336,3),np.float32)
        output=batched_predictions(model,x,batch_size=2)
        self.assertEqual(output.shape,(3,168,3));self.assertTrue(np.isfinite(output).all())

    def test_evaluation_denominators_r2_and_mask_exclusion(self):
        actual=np.array([[1.,np.nan,3.],[5.,7.,np.nan]])
        predicted=np.array([[2.,1e30,4.],[6.,8.,1e30]])
        m=np.isfinite(actual)
        row=metric_row(actual,predicted,m)
        self.assertEqual(row['valid_observations'],4)
        self.assertEqual(row['MAE'],1);self.assertEqual(row['RMSE'],1)
        self.assertAlmostEqual(row['R2'],1-4/20)
        empty=metric_row(actual,predicted,np.zeros_like(m))
        self.assertIsNone(empty['MAE']);self.assertIsNone(empty['R2'])

    def test_pooled_errors_not_average_rmse(self):
        a=np.zeros((3,1));p=np.array([[1.],[1.],[5.]])
        self.assertEqual(metric_row(a,p,np.ones_like(a,bool))['RMSE'],3.)

    def test_cumulative_horizons_and_lead_counts(self):
        a=np.zeros((2,168,3));p=np.ones_like(a);m=np.ones_like(a,bool)
        p[:,24:]=3;m[0,0,0]=False
        rows,leads=evaluate_forecasts(a,p,m,'fixture','NODE_01')
        self.assertEqual(rows[0]['valid_observations'],47)
        self.assertEqual(rows[0]['MAE'],1)
        self.assertAlmostEqual(rows[1]['MAE'],(47+96*3)/143)
        self.assertEqual(len(rows),9);self.assertEqual(len(leads),504)


if __name__=='__main__':
    unittest.main(verbosity=2)
