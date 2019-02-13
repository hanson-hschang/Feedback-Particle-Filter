"""
Created on Thu Jan. 31, 2019

@author: Heng-Sheng (Hanson) Chang
"""

import numpy as np
from FPF import FPF, Signal, Struct, Figure
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

def h(amp, x):
        return amp*np.cos(x)

if __name__ == "__main__":
    # N states of frequency inputs
    freq = [0.65, 1.15]
    # M-by-N amplitude matrix
    amp = [[1,1]]
    # N states of state noises
    sigma_B = [0.1,0.1]
    # M states of signal noises
    sigma_W = [0.1]

    T = 10.
    dt = 0.01
    signal = Signal(freq=freq, amp=amp, sigma_B=sigma_B, sigma_W=sigma_W, dt=dt, T=T)
    h_hat = np.zeros(signal.Y.shape)
    
    N=100
    feedback_particle_filter = FPF(number_of_particles=N, f_min=0.6, f_max=1.2, sigma_W=sigma_W, dt=dt, h=h)
    filtered_signal = feedback_particle_filter.run(signal.Y)

    fontsize = 20
    fig_property = Struct(fontsize=fontsize, show=False, \
                            plot_signal=True, plot_theta=True, plot_omega=True, plot_amp=True)
    figure = Figure(fig_property=fig_property, signal=signal, filtered_signal=filtered_signal)
    figure.plot()
    
    fig, ax = plt.subplots(1,1, figsize=(7,7))
    ax = figure.plot_sync_matrix(ax, feedback_particle_filter.particles.update_sync_matrix())
    
    fig, ax = plt.subplots(1,1, figsize=(7,7))
    ax = figure.plot_sync_particle(ax, feedback_particle_filter.particles.check_sync())

    plt.show()