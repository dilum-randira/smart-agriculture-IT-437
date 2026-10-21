"""Multi-model physical-unit forecast and training plots for frozen experiments."""
import numpy as np
import pandas as pd
from ..preprocessing.pipeline import LABEL,TARGETS,UNITS

PLOT_NAMES=('Soil moisture','Air temperature','Relative humidity')
PLOT_UNITS=('INDEX; not VWC','°C','% RH')


def plot_experiment(output,history,predictions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fig,ax=plt.subplots(figsize=(10,5))
    ax.plot(history.epoch,history.loss,label='Training masked MSE')
    ax.plot(history.epoch,history.val_loss,label='Validation masked MSE')
    ax.axvline(history.loc[history.val_loss.idxmin(),'epoch'],linestyle=':',color='gray',label='Validation-selected epoch')
    ax.set(xlabel='Completed epoch',ylabel='MSE in standardized target space',title=LABEL)
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(output/'loss_curves.png',dpi=140);plt.close(fig)
    for s in predictions:
        dates=pd.date_range(pd.Timestamp(int(s['origins'][0]),tz='UTC').tz_convert('Asia/Colombo')+pd.Timedelta(hours=1),periods=168,freq='h')
        fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
        for j,ax in enumerate(axes):
            ax.plot(dates,np.where(s['mask'][0,:,j],s['actual'][0,:,j],np.nan),label='Eligible synthetic actual',linewidth=1.6)
            for name,values in s['forecasts'].items():
                ax.plot(dates,values[0,:,j],label=name,alpha=.85,linestyle='--' if name=='Persistence' else '-')
            ax.set_ylabel(f'{PLOT_NAMES[j]}\n({PLOT_UNITS[j]})');ax.legend(fontsize=7);ax.grid(alpha=.2)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M',tz=dates.tz))
        axes[-1].set_xlabel('Target timestamp — Asia/Colombo (UTC+05:30)')
        fig.suptitle(f"{LABEL}\n{s['node']}: first chronological held-out origin")
        fig.tight_layout(rect=(0,0,1,.94));fig.savefig(output/f"forecast_{s['node']}.png",dpi=140);plt.close(fig)
