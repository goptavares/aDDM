#!/usr/bin/python

"""
optimize.py
Author: Gabriela Tavares, gtavares@caltech.edu

Maximum likelihood estimation procedure for the attentional drift-diffusion
model (aDDM), using a Basinhopping algorithm to search the parameter space. Data
from all subjects is pooled such that a single set of optimal parameters is
estimated.
"""

from scipy.optimize import basinhopping

import argparse
import numpy as np

from addm import get_trial_likelihood
from util import load_data_from_csv


# Global variables.
choice = dict()
valueLeft = dict()
valueRight = dict()
fixItem = dict()
fixTime = dict()
trialsPerSubject = 0


def get_model_nll(params):
    """
    Computes the negative log likelihood of the global data set given the
    parameters of the aDDM.
    Args:
      params: list containing the 3 model parameters, in the following order: d,
          theta, sigma.
    Returns:
      The negative log likelihood for the global data set and the given model.
    """

    d = params[0]
    theta = params[1]
    sigma = params[2]

    logLikelihood = 0
    subjects = choice.keys()
    for subject in subjects:
        trials = choice[subject].keys()
        trialSet = np.random.choice(trials, trialsPerSubject, replace=False)
        for trial in trialSet:
            likelihood = get_trial_likelihood(
                choice[subject][trial], valueLeft[subject][trial],
                valueRight[subject][trial], fixItem[subject][trial],
                fixTime[subject][trial], d, theta, sigma=sigma)
            if likelihood != 0:
                logLikelihood += np.log(likelihood)
    print("NLL for " + str(params) + ": " + str(-logLikelihood))
    return -logLikelihood


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials-per-subject", type=int, default=100,
                        help="number of trials from each subject to be used in "
                        "the analysis; if smaller than 1, all trials are used")
    parser.add_argument("--num-iterations", type=int, default=100,
                        help="number of basin hopping iterations")
    parser.add_argument("--step-size", type=float, default=0.001,
                        help="step size for use in the random displacement of "
                        "the basin hopping algorithm")
    args = parser.parse_args()

    global choice
    global valueLeft
    global valueRight
    global fixItem
    global fixTime
    global trialsPerSubject

    # Load experimental data from CSV file and update global variables.
    data = load_data_from_csv("expdata.csv", "fixations.csv",
                              useAngularDists=True)
    choice = data.choice
    valueLeft = data.valueLeft
    valueRight = data.valueRight
    fixItem = data.fixItem
    fixTime = data.fixTime

    trialsPerSubject = args.trials_per_subject

    # Initial guess: d, theta, sigma.
    initialParams = [0.0002, 0.5, 0.08]

    # Search bounds.
    paramsMin = [0.00005, 0., 0.05]
    paramsMax = [0.01, 1., 0.1]
    bounds = [(lower, upper) for lower, upper in zip(paramsMin, paramsMax)]

    # Optimize using Basinhopping algorithm.
    minimizerKwargs = dict(method="L-BFGS-B", bounds=bounds)
    result = basinhopping(get_model_nll, initialParams,
                          minimizer_kwargs=minimizerKwargs,
                          niter=args.num_iterations, stepsize=args.step_size)
    print("Optimization result: " + str(result))


if __name__ == '__main__':
    main()
