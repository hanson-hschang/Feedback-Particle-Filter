"""
Created on Thu Jun. 20, 2019

@author: Heng-Sheng (Hanson) Chang
"""

from __future__ import division
from __future__ import print_function

import numpy as np
import sympy

from Tool import Struct
from Signal import Signal, Sinusoids
from System import LTI
from FPF import FPF, Model, Galerkin, Figure

class Model_Oscillator(Model):
    def __init__(self, freq_range, amp_range, sigma_freq, sigma_amp, sigma_W, tolerance):
        d = 2*len(amp_range)
        states = ['theta'] * d
        states_label = [r'$\theta$'] * d
        
        self.freq_min = freq_range[0]
        self.freq_max = freq_range[1]
        X0_range = [[0,2*np.pi]] * d
        sigma_V = [sigma_freq] * d
        
        for m in range(len(amp_range)):
            if m == 0:
                states[1] = 'a{}'.format(1)
                states_label[1] = r'$a_{}$'.format(1)
                X0_range[1] = amp_range[0]
                sigma_V[1] = sigma_amp[0]
            else:
                states[2*m] = 'a{}'.format(m+1)
                states[2*m+1] = 'b{}'.format(m+1)
                states_label[2*m] = r'$a_{}$'.format(m+1)
                states_label[2*m+1] = r'$b_{}$'.format(m+1)
                X0_range[2*m] = amp_range[m]
                X0_range[2*m+1] = amp_range[m]
                sigma_V[2*m] = sigma_amp[m]
                sigma_V[2*m+1] = sigma_amp[m]
        self.tolerance = tolerance
        Model.__init__(self, m=len(amp_range), d=d, X0_range=X0_range, 
                        states=states, states_label=states_label, 
                        sigma_V=sigma_V, sigma_W=sigma_W)
    
    def states_constraints(self, X):
        X[:,0] = np.mod(X[:,0], 2*np.pi)
        X[X[:,1]<-self.tolerance,0] += np.pi
        X[X[:,1]<-self.tolerance,1] = -X[X[:,1]<-self.tolerance,1]
        for m in range(self.m):
            X[(X[:,2*m]<-self.tolerance) & (X[:,2*m+1]<-self.tolerance),0] += np.pi
            X[(X[:,2*m]<-self.tolerance) & (X[:,2*m+1]<-self.tolerance),2*m:2*m+2] = \
                -X[(X[:,2*m]<-self.tolerance) & (X[:,2*m+1]<-self.tolerance),2*m:2*m+2]
            X[X[:,2*m]<-self.tolerance,0] = np.pi-X[X[:,2*m]<-self.tolerance,0]
            X[X[:,2*m]<-self.tolerance,2*m] = -X[X[:,2*m]<-self.tolerance,2*m]
            X[X[:,2*m+1]<-self.tolerance,0] = -X[X[:,2*m+1]<-self.tolerance,0]
            X[X[:,2*m+1]<-self.tolerance,2*m+1] = -X[X[:,2*m+1]<-self.tolerance,2*m+1]
        X[:,0] = np.mod(X[:,0], 2*np.pi)
        return X

    def f(self, X):
        dXdt = np.zeros(X.shape)
        dXdt[:,0] = np.linspace(self.freq_min*2*np.pi, self.freq_max*2*np.pi, X.shape[0])
        return dXdt

    def h(self, X):
        Y = np.zeros((X.shape[0], self.m))
        Y[:,0] = X[:,1] * np.cos(X[:,0])
        Y[:,1:] = np.einsum('im,i->im', X[:,2::2], np.cos(X[:,0])) + np.einsum('im,i->im', X[:,3::2], np.sin(X[:,0]))
        # Y = np.einsum('im,i->im', np.square(X[:,1::2]), np.cos(X[:,0])) + np.einsum('im,i->im', np.square(X[:,2::2]), np.sin(X[:,0]))
        return Y

class Galerkin_Oscillator(Galerkin):
    """Galerkin_Oscillator: An approximation in finite element method:
            states: [ theta, a1, a2, b2, ..., am, bm]
            base functions: [ a1*cos(theta), a1*sin(theta), a2*cos(theta), b2*sin(theta), ..., am*cos(theta), bm*sin(theta)] 
        Initialize = Galerkin_Oscillator(states, m)
            states: 1D list of string with length d, name of each state
            m: int, number of observations
        Members = 
            result: temporary memory location of the result of exec()
            psi_list: 1D list of string with length L, sympy expression of each base function
            grad_psi_list: 2D list of string with length L-by-d, sympy expression of gradient of psi function
            grad_grad_psi_list: 3D list of string with length L-by-d-by-d, sympy expression of gradient of gradient of psi function
            psi_string: string, executable 1D list of numpy array with length L
            grad_psi_string: string, executable 2D list of numpy array with length L-by-d
            grad_grad_psi_string: string, executable 3D list of numpy array with length L-by-d-by-d
        Methods = 
            sympy_executable_result(self): return sympy executable string
    """
    def __init__(self, states, m):
        Galerkin.__init__(self, states, m, 2*m)
        
        self.result = ''

        self.psi_list = [None for l in range(self.L)]
        self.grad_psi_list = [[None for d in range(self.d)] for l in range(self.L)]
        self.grad_grad_psi_list = [[[None for d2 in range(self.d)] for d1 in range(self.d)] for l in range(self.L)]  

        # initialize psi
        self.psi_string = '['
        for m in range(self.m):
            self.psi_list[2*m] = 'self.a{}*sympy.cos(self.theta)'.format(m+1)
            if m==0:
                self.psi_list[2*m+1] = 'self.a{}*sympy.sin(self.theta)'.format(m+1)
            else:
                self.psi_list[2*m+1] = 'self.b{}*sympy.sin(self.theta)'.format(m+1)
        self.psi_string += (', '.join(self.psi_list)).replace('sympy','np')
        self.psi_string += ']'
        
        # initialize symbols
        exec(', '.join(self.states)+' = sympy.symbols("'+', '.join(self.states)+'")')
        
        # calculate grad_psi and grad_grad_psi
        self.grad_psi_string = '['
        self.grad_grad_psi_string = '['
        for l in range(self.L):
            self.grad_psi_string += '['
            self.grad_grad_psi_string += '['
            for d1 in range(self.d):
                exec('self.result = sympy.diff('+self.psi_list[l]+','+self.states[d1]+')')
                self.grad_psi_list[l][d1] = self.sympy_executable_result()
                
                self.grad_grad_psi_string += '['
                for d2 in range(self.d):
                    exec('self.result = sympy.diff('+self.grad_psi_list[l][d1]+','+self.states[d2]+')')
                    self.grad_grad_psi_list[l][d1][d2] = self.sympy_executable_result()
                self.grad_grad_psi_string += ((', ').join(self.grad_grad_psi_list[l][d1])).replace('sympy','np')
                self.grad_grad_psi_string += '], '
            
            self.grad_psi_string += ((', ').join(self.grad_psi_list[l])).replace('sympy','np')
            self.grad_psi_string += '], '
            self.grad_grad_psi_string = self.grad_grad_psi_string[:-2] + '], '

        self.grad_psi_string = self.grad_psi_string[:-2]+']'
        self.grad_grad_psi_string = self.grad_grad_psi_string[:-2]+']'
        return

    def sympy_executable_result(self):
        self.result = str(self.result)
        if 'cos' in self.result:
            self.result = self.result.replace('cos','sympy.cos')
        if 'sin' in self.result:
            self.result = self.result.replace('sin','sympy.sin')
        return self.result

    def psi(self, X):
        self.split(X)
        exec("self.result = "+self.psi_string)
        trial_functions = self.result
        return np.array(trial_functions)
        
    def grad_psi(self, X):
        self.split(X)
        exec("self.result = "+self.grad_psi_string)
        grad_trial_functions = np.zeros([self.L, self.d, X.shape[0]])
        for l in range(self.L):
            for d in range(self.d):
                grad_trial_functions[l,d,:] = self.result[l][d]
        return grad_trial_functions

    def grad_grad_psi(self, X):
        self.split(X)
        exec("self.result = "+self.grad_grad_psi_string)
        grad_grad_trial_functions = np.zeros([self.L, self.d, self.d, X.shape[0]])
        for l in range(self.L):
            for d1 in range(self.d):
                for d2 in range(self.d):
                    grad_grad_trial_functions[l,d1,d2,:] = self.result[l][d1][d2]
        return grad_grad_trial_functions

class OFPF(FPF):
    def __init__(self, number_of_particles, freq_range, amp_range, sigma_amp, sigma_W, dt, sigma_freq=0, tolerance=0):
        assert len(amp_range)==len(sigma_amp)==len(sigma_W),  \
            "length of amp_range ({}), length of sigma_amp ({}) and length of sigma_W ({}) do not match (should all be m)".format(
                len(amp_range), len(sigma_amp), len(sigma_W))
        model = Model_Oscillator(freq_range, amp_range, sigma_freq=sigma_freq, sigma_amp=sigma_amp, sigma_W=sigma_W, tolerance=tolerance)
        galerkin = Galerkin_Oscillator(model.states, model.m)
        FPF.__init__(self, number_of_particles, model, galerkin, dt)
    
    def get_gain(self):
        gain = np.zeros(self.m, dtype=complex)
        for m in range(self.m):
            theta_0 = -np.arctan(-np.mean(self.particles.X[:,1]*np.sin(self.particles.X[:,0]))/np.mean(self.particles.X[:,1]*np.cos(self.particles.X[:,0])))
            if m==0:
                a_1 = np.mean(self.particles.X[:,1]*np.cos(self.particles.X[:,0]-theta_0))
                gain[0] = complex(a_1, 0)
            else:
                a_m = np.mean(self.particles.X[:,2*m]*np.cos(self.particles.X[:,0]-theta_0)) + \
                        np.mean(self.particles.X[:,2*m+1]*np.sin(self.particles.X[:,0]-theta_0))
                b_m = -np.mean(self.particles.X[:,2*m]*np.sin(self.particles.X[:,0]-theta_0)) + \
                        np.mean(self.particles.X[:,2*m+1]*np.cos(self.particles.X[:,0]-theta_0))
                gain[m] = complex(a_m, -b_m)
            # gain[m] = complex(np.mean(np.square(self.particles.X[:,2*m+1])),-np.mean(np.square(self.particles.X[:,2*m+2])))
        return gain

if __name__ == "__main__":
    T = 5.5
    sampling_rate = 100 # Hz
    dt = 1./sampling_rate

    sigma_V = [0.1]
    signal_type = Sinusoids(dt, amp=[[1]], freq=[1], theta0=[[np.pi/2]], sigma_V=sigma_V, SNR=[20])
    Y, _ = Signal.create(signal_type=signal_type, T=T)
    
    Np = 1000
    ofpf = OFPF(number_of_particles=Np, freq_range=[0.9, 1.1], amp_range=[[0.9,1.1]],\
                sigma_amp=[0], sigma_W=[0.1], dt=dt, sigma_freq=0.1, tolerance=0)
    filtered_signal = ofpf.run(Y.value, show_time=False)

    fontsize = 20
    fig_property = Struct(fontsize=fontsize, plot_signal=True, plot_X=True, plot_c=True)
    figure = Figure(fig_property=fig_property, Y=Y, filtered_signal=filtered_signal)
    figure.plot_figures(show=True)