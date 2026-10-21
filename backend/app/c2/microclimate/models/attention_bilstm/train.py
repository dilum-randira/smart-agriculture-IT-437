"""Single fixed Attention BiLSTM configuration; full frozen datasets, CPU only."""
import argparse
from pathlib import Path
import numpy as np
import tensorflow as tf

from ...common.experiment import run_experiment
from ...common.paths import BACKEND
from ...common.masked_loss import masked_squared_error
from ...preprocessing.pipeline import LABEL,TARGETS
from .model import MaskedAttentionBiLSTM
from .evaluation import evaluate_selected
from .reporting import plots,write_reports

DEFAULT_OUTPUT=BACKEND/'experiments/c2/microclimate/attention_bilstm_v1'


def sanity_check(model,train):
    x,y,mask=(v[:2] for v in train)
    with tf.GradientTape() as tape:
        prediction=model(x,training=True)
        loss,_,count=masked_squared_error(y,prediction,mask)
    gradients=tape.gradient(loss,model.trainable_variables)
    assert all(g is not None and np.isfinite(g.numpy()).all() for g in gradients)
    assert all(np.any(g.numpy()!=0) for g,v in zip(gradients,model.trainable_variables) if 'attention_score' in v.path)
    weights=model.attention_weights(x).numpy()
    assert weights.shape==(2,336) and np.isfinite(weights).all() and (weights>=0).all()
    np.testing.assert_allclose(weights.sum(axis=1),1.,rtol=0,atol=1e-6)
    return dict(output_shape=list(prediction.shape),attention_shape=list(weights.shape),
                attention_sum_max_error=float(np.max(np.abs(weights.sum(axis=1)-1))),
                all_gradients_finite=True,attention_score_gradient_nonzero=True,
                valid_supervision_elements=int(count),masked_loss=float(loss),
                input_contract='Historical X only; no y or future observations enter encoder')


def run(output=DEFAULT_OUTPUT):
    config=dict(seed=42,units=32,lookback=336,horizon=168,features=list(TARGETS),batch_size=16,
                learning_rate=.001,optimizer='Adam',global_clipnorm=1.,maximum_epochs=100,patience=10,
                restore_best_weights=True,shuffle_buffer=1024,drop_remainder=False,intra_op_threads=6,
                inter_op_threads=1,steps_per_execution=16,jit_compile=False,training_samples=11137,
                validation_samples=1622,test_samples=1622,model='AttentionBiLSTM',attention_units=32,
                attention_formulation='e_t=v^T tanh(W h_t+b); alpha=softmax_time(e); c=sum_t alpha_t h_t',
                attention_interpretation='Descriptive, not causal',evaluation_label=LABEL)
    return run_experiment(output,config,lambda:MaskedAttentionBiLSTM(name='c2_attention_bilstm'),30040,
                          'attention_bilstm_best.keras',evaluate_selected,plots,write_reports,sanity_check)


def main():
    parser=argparse.ArgumentParser(description=LABEL)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    run(parser.parse_args().output)


if __name__=='__main__':
    main()
