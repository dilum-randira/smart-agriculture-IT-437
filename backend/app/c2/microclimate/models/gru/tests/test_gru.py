"""GRU-specific fixtures; no research dataset or artifact mutation."""
from pathlib import Path
import tempfile
import unittest

import keras
import numpy as np
import tensorflow as tf

from ..model import MaskedGRU
from ..evaluation import assert_comparable
from ...lstm.model import MaskedLSTM
from ...lstm.evaluation import metric_row
from ....common.masked_loss import masked_squared_error


class GRUTests(unittest.TestCase):
    def test_fixed_architecture_and_shape(self):
        model=MaskedGRU()
        output=model(np.zeros((2,336,3),np.float32),training=False).numpy()
        self.assertEqual(output.shape,(2,168,3))
        self.assertTrue(np.isfinite(output).all())
        self.assertEqual(model.forecaster.count_params(),9987)
        self.assertEqual([type(l).__name__ for l in model.forecaster.layers],['InputLayer','GRU','RepeatVector','GRU','TimeDistributed'])
        self.assertEqual(len(model.trainable_variables),8)
        self.assertTrue(model.forecaster.layers[1].reset_after)
        self.assertTrue(model.forecaster.layers[3].return_sequences)

    def test_shared_optimization_identity(self):
        for name in ('train_step','test_step','build','call','get_config'):
            self.assertIs(getattr(MaskedGRU,name),getattr(MaskedLSTM,name))
        self.assertEqual(keras.saving.get_registered_name(MaskedGRU),'c2>MaskedGRU')

    def test_excluded_labels_have_zero_gradient(self):
        p=tf.Variable([1.,2.,3.]);y=tf.constant([0.,np.nan,1.]);mask=tf.constant([True,False,True])
        with tf.GradientTape() as tape:loss,_,count=masked_squared_error(y,p,mask)
        gradient=tape.gradient(loss,p).numpy()
        self.assertEqual(float(count),2);self.assertEqual(float(loss),2.5)
        np.testing.assert_array_equal(gradient,[1.,0.,2.])

    def test_masked_metric_denominator(self):
        row=metric_row(np.array([[1.,np.nan,3.]]),np.array([[2.,1e20,5.]]),np.array([[True,False,True]]))
        self.assertEqual(row['valid_observations'],2)
        self.assertEqual(row['MAE'],1.5)
        self.assertAlmostEqual(row['RMSE'],np.sqrt(2.5))
        self.assertEqual(row['R2'],-1.5)

    def test_empty_batch_skip_and_finite_optimizer_update(self):
        model=MaskedGRU(units=2);model.compile(optimizer=keras.optimizers.Adam(.001,global_clipnorm=1.),jit_compile=False)
        x=tf.zeros((1,336,3));y=tf.ones((1,168,3));mask=tf.zeros((1,168,3),tf.bool)
        model(x);before=[v.numpy().copy() for v in model.trainable_variables]
        step=tf.function(model.train_step);step((x,y,mask))
        self.assertEqual(int(model.optimizer.iterations),0)
        for a,b in zip(before,model.trainable_variables):np.testing.assert_array_equal(a,b.numpy())
        result=step((x,y,tf.ones_like(mask)))
        self.assertEqual(int(model.optimizer.iterations),1)
        self.assertTrue(np.isfinite(float(result['loss'])))

    def test_validation_mask_count(self):
        model=MaskedGRU(units=2)
        x=tf.zeros((1,336,3));y=np.ones((1,168,3),np.float32);mask=np.ones_like(y,bool)
        mask[:,0,:]=False;y[~mask]=np.nan
        result=model.test_step((x,y,mask))
        self.assertEqual(float(result['loss']),1.)
        self.assertEqual(int(model.loss_tracker.valid_count),501)

    def test_save_reload_roundtrip(self):
        model=MaskedGRU(units=2)
        x=np.random.default_rng(42).normal(size=(2,336,3)).astype('float32')
        expected=model(x,training=False).numpy()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'fixture.keras';model.save(p)
            restored=keras.models.load_model(p,compile=False)
            self.assertIsInstance(restored,MaskedGRU)
            np.testing.assert_allclose(restored(x,training=False).numpy(),expected,rtol=0,atol=1e-6)

    def test_comparison_rejects_different_masks_or_origins(self):
        actual=np.ones((2,168,3));mask=np.ones_like(actual,bool);origins=np.array([1,2])
        reference=dict(actual_original_units=actual.copy(),persistence_original_units=actual.copy(),target_valid_mask=mask.copy(),forecast_origin_unix_ns=origins.copy())
        assert_comparable(actual,actual,mask,origins,reference)
        with self.assertRaises(AssertionError):assert_comparable(actual,actual,mask,origins+1,reference)
        bad=mask.copy();bad[0,0,0]=False
        with self.assertRaises(AssertionError):assert_comparable(actual,actual,bad,origins,reference)


if __name__=='__main__':
    unittest.main(verbosity=2)
