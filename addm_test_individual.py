#!/usr/bin/python

"""
addm_test_individual.py
Author: Gabriela Tavares, gtavares@caltech.edu

Test to check the validity of the addm parameter estimation. Artificil data is
generated using specific parameters for the model. Fixations are sampled from
the data from a single subject. The parameters used for data generation are then
recovered through a posterior distribution estimation procedure.
"""

from multiprocessing import Pool

import argparse
import csv
import numpy as np

from addm import (get_trial_likelihood, get_empirical_distributions,
                  run_simulations)
from util import load_data_from_csv


def get_trial_likelihood_wrapper(params):
    """
    Wrapper for addm.get_trial_likelihood() which takes a single argument.
    Intended for parallel computation using a thread pool.
    Args:
      params: tuple consisting of all arguments required by
          addm.get_trial_likelihood().
    Returns:
      The output of addm.get_trial_likelihood().
    """

    return get_trial_likelihood(*params)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("subject", type=str, help="Subject name.")
    parser.add_argument("--num-threads", type=int, default=9,
                        help="Size of the thread pool.")
    parser.add_argument("--num-trials", type=int, default=200,
                        help="Number of artificial data trials to be generated "
                        "per trial condition.")
    parser.add_argument("--d", type=float, default=0.006,
                        help="aDDM parameter for generating artificial data.")
    parser.add_argument("--sigma", type=float, default=0.08,
                        help="aDDM parameter for generating artificial data.")
    parser.add_argument("--theta", type=float, default=0.5,
                        help="aDDM parameter for generating artificial data.")
    parser.add_argument("--range-d", nargs="+", type=float,
                        default=[0.005, 0.006, 0.007],
                        help="Search range for parameter d.")
    parser.add_argument("--range-sigma", nargs="+", type=float,
                        default=[0.065, 0.08, 0.095],
                        help="Search range for parameter sigma.")
    parser.add_argument("--range-theta", nargs="+", type=float,
                        default=[0.4, 0.5, 0.6],
                        help="Search range for parameter theta.")
    parser.add_argument("--expdata-file-name", type=str, default="expdata.csv",
                        help="Name of experimental data file.")
    parser.add_argument("--fixations-file-name", type=str,
                        default="fixations.csv", help="Name of fixations file.")
    parser.add_argument("--verbose", default=False, action="store_true",
                        help="Increase output verbosity.")
    args = parser.parse_args()

    pool = Pool(args.num_threads)

    valueLeft = dict()
    valueRight = dict()
    fixItem = dict()
    fixTime = dict()

    # Load experimental data from CSV file.
    try:
        data = load_data_from_csv(
            args.expdata_file_name, args.fixations_file_name,
            useAngularDists=True)
    except Exception as e:
        print("An exception occurred while loading the data: " + str(e))
        return
    valueLeft[args.subject] = data.valueLeft[args.subject]
    valueRight[args.subject] = data.valueRight[args.subject]
    fixItem[args.subject] = data.fixItem[args.subject]
    fixTime[args.subject] = data.fixTime[args.subject]

    # Get empirical distributions.
    try:
        dists = get_empirical_distributions(valueLeft, valueRight, fixItem,
                                            fixTime)
    except Exception as e:
        print("An exception occurred while getting empirical distributions: " +
              str(e))
        return
    probLeftFixFirst = dists.probLeftFixFirst
    distLatencies = dists.distLatencies
    distTransitions = dists.distTransitions
    distFixations = dists.distFixations

    # Trial conditions for artificial data generation.
    orientations = range(-15,20,5)
    trialConditions = list()
    for oLeft in orientations:
        for oRight in orientations:
            if oLeft != oRight:
                vLeft = np.absolute((np.absolute(oLeft) - 15) / 5)
                vRight = np.absolute((np.absolute(oRight) - 15) / 5)
                trialConditions.append((vLeft, vRight))

    # Generate artificial data.
    if args.verbose:
        print("Running simulations...")
    try:
        simul = run_simulations(
            probLeftFixFirst, distLatencies, distTransitions, distFixations,
            args.num_trials, trialConditions, args.d, args.theta,
            sigma=args.sigma)
    except Exception as e:
        print("An exception occurred while generating artificial data: " +
              str(e))
        return
    simulChoice = simul.choice
    simulValueLeft = simul.valueLeft
    simulValueRight = simul.valueRight
    simulFixItem = simul.fixItem
    simulFixTime = simul.fixTime

    # Grid search to recover the parameters.
    if args.verbose:
        print("Starting grid search...")
    numModels = (len(args.range_d) * len(args.range_theta) *
                 len(args.range_sigma))
    models = list()
    posteriors = dict()
    for d in args.range_d:
        for theta in args.range_theta:
            for sigma in args.range_sigma:
                model = (d, theta, sigma)
                models.append(model)
                posteriors[model] = 1. / numModels

    trials = simulChoice.keys()
    for trial in trials:
        listParams = list()
        for model in models:
            listParams.append(
                (simulChoice[trial], simulValueLeft[trial],
                simulValueRight[trial], simulFixItem[trial],
                simulFixTime[trial], model[0], model[1], model[2]))
        try:
            likelihoods = pool.map(get_trial_likelihood_wrapper, listParams)
        except Exception as e:
            print("An exception occurred during the likelihood computation for "
                  "trial " + str(trial) + ": " + str(e))
            return

        # Get the denominator for normalizing the posteriors.
        i = 0
        denominator = 0
        for model in models:
            denominator += posteriors[model] * likelihoods[i]
            i += 1
        if denominator == 0:
            continue

        # Calculate the posteriors after this trial.
        i = 0
        for model in models:
            prior = posteriors[model]
            posteriors[model] = likelihoods[i] * prior / denominator
            i += 1

        if args.verbose and trial % 200 == 0:
            for model in posteriors:
                print("P" + str(model) + " = " + str(posteriors[model]))
            print("Sum: " + str(sum(posteriors.values())))
 
    if args.verbose:
        for model in posteriors:
            print("P" + str(model) + " = " + str(posteriors[model]))
        print("Sum: " + str(sum(posteriors.values())))


if __name__ == '__main__':
    main()
