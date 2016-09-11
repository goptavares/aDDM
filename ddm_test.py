#!/usr/bin/python

"""
ddm_test.py
Author: Gabriela Tavares, gtavares@caltech.edu

Test to check the validity of the ddm parameter estimation. Artificil data is
generated using specific parameters for the model. These parameters are then
recovered through a posterior distribution estimation procedure.
"""

import argparse

from ddm import DDMTrial, DDM


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-threads", type=int, default=9,
                        help="Size of the thread pool.")
    parser.add_argument("--trials-per-condition", type=int, default=800,
                        help="Number of artificial data trials to be "
                        "generated per trial condition.")
    parser.add_argument("--d", type=float, default=0.006,
                        help="DDM parameter for generating artificial data.")
    parser.add_argument("--sigma", type=float, default=0.08,
                        help="DDM parameter for generating artificial data.")
    parser.add_argument("--range-d", nargs="+", type=float,
                        default=[0.005, 0.006, 0.007],
                        help="Search range for parameter d.")
    parser.add_argument("--range-sigma", nargs="+", type=float,
                        default=[0.065, 0.08, 0.095],
                        help="Search range for parameter sigma.")
    parser.add_argument("--verbose", default=False, action="store_true",
                        help="Increase output verbosity.")
    args = parser.parse_args()

    # Trial conditions with format (valueLeft, valueRight). Change this
    # according to the experiment.
    trialConditions = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 1),
                       (1, 2), (1, 3), (2, 2), (2, 3)]

    # Generate artificial data.
    model = DDM(args.d, args.sigma)
    trials = list()
    for (valueLeft, valueRight) in trialConditions:
        for t in xrange(args.trials_per_condition):
            try:
                trials.append(model.simulate_trial(valueLeft, valueRight))
            except:
                print("An exception occurred while generating artificial " +
                      "trial " + str(t) + " for condition (" + str(valueLeft) +
                      ", " + str(valueRight) + ").")
                raise

    # Get likelihoods for all models and all artificial trials.
    numModels = len(args.range_d) * len(args.range_sigma)
    likelihoods = dict()
    models = list()
    posteriors = dict()
    for d in args.range_d:
        for sigma in args.range_sigma:
            model = DDM(d, sigma)
            if args.verbose:
                print("Computing likelihoods for model " +
                      str(model.params) + "...")
            try:
                likelihoods[model.params] = model.parallel_get_likelihoods(
                    trials, numThreads=args.num_threads)
            except:
                print("An exception occurred during the likelihood " +
                      "computations for model " + str(model.params) + ".")
                raise
            models.append(model)
            posteriors[model.params] = 1. / numModels

    # Compute the posteriors.
    for t in xrange(len(trials)):
        # Get the denominator for normalizing the posteriors.
        denominator = 0
        for model in models:
            denominator += (posteriors[model.params] *
                            likelihoods[model.params][t])
        if denominator == 0:
            continue

        # Calculate the posteriors after this trial.
        for model in models:
            prior = posteriors[model.params]
            posteriors[model.params] = (likelihoods[model.params][t] *
                prior / denominator)

    if args.verbose:
        for model in models:
            print("P" + str(model.params) +  " = " +
                  str(posteriors[model.params]))
        print("Sum: " + str(sum(posteriors.values())))


if __name__ == "__main__":
    main()
