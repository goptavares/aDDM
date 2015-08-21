#!/usr/bin/python

"""
ddm.py
Author: Gabriela Tavares, gtavares@caltech.edu

Implementation of the traditional drift-diffusion model (DDM), as described by
Ratcliff et al. (1998).
"""

import matplotlib
matplotlib.use('Agg')

from scipy.stats import norm

import collections
import matplotlib.pyplot as plt
import numpy as np


def get_trial_likelihood(RT, choice, valueLeft, valueRight, d, sigma,
                         timeStep=10, stateStep=0.1, barrier=1,
                         plotResults=False):
    """
    Computes the likelihood of the data from a single trial given a set of DDM
    parameters.
    Args:
      RT: reaction time in miliseconds.
      choice: integer, either -1 (for left item) or +1 (for right item).
      valueLeft: integer, value of the left item.
      valueRight: integer, value of the right item.
      d: float, parameter of the model which controls the speed of integration
          of the signal.
      sigma: float, parameter of the model, standard deviation for the normal
          distribution.
      timeStep: integer, value in miliseconds to be used for binning the time
          axis.
      stateStep: float, to be used for binning the RDV axis.
      barrier: positive number, magnitude of the signal thresholds.
      plotResults: boolean, flag that determines whether the algorithm evolution
          for the trial should be plotted.
    Returns:
      The likelihood obtained for the given trial and model.
    """

    # Get the total time for this trial.
    maxTime = int(RT // timeStep)

    # The values of the barriers can change over time.
    decay = 0  # decay = 0 means barriers are constant.
    barrierUp = barrier * np.ones(maxTime)
    barrierDown = -barrier * np.ones(maxTime)
    for t in xrange(1, maxTime):
        barrierUp[t] = float(barrier) / float(1 + (decay * t))
        barrierDown[t] = float(-barrier) / float(1 + (decay * t))

    # The vertical axis (RDV space) is divided into states.
    states = np.arange(-barrier, barrier + stateStep, stateStep)
    states[(states < 0.001) & (states > -0.001)] = 0

    # Initial probability for all states is zero, except for the zero state,
    # which has initial probability equal to one.
    prStates = np.zeros(states.size)
    prStates[states == 0] = 1
    prStates[(states > barrierUp[0]) | (states < barrierDown[0])] = 0

    # The probability of crossing each barrier over the time of the trial.
    probUpCrossing = np.zeros(maxTime)
    probDownCrossing = np.zeros(maxTime)

    # Create matrix of traces to keep track of the RDV position probabilities.
    if plotResults:
        traces = np.zeros((states.size, maxTime))
        traces[:, 0] = prStates

    # We use a normal distribution to model changes in RDV stochastically.
    # The mean of the distribution (the change most likely to occur) is
    # calculated from the model parameter d and from the item values.
    mean = d * (valueLeft - valueRight)

    changeMatrix = np.subtract(states.reshape(states.size, 1), states)
    changeUp = np.subtract(barrierUp, states.reshape(states.size, 1))
    changeDown = np.subtract(barrierDown, states.reshape(states.size, 1))

    # Iterate over the time of this trial.
    for time in xrange(1, maxTime):
        # Update the probability of the states that remain inside the
        # barriers. The probability of being in state B is the sum, over all
        # states A, of the probability of being in A at the previous timestep
        # times the probability of changing from A to B. We multiply the
        # probability by the stateStep to ensure that the area under the curves
        # for the probability distributions probUpCrossing and probDownCrossing
        # add up to 1.
        prStatesNew = (stateStep *
                       np.dot(norm.pdf(changeMatrix, mean, sigma), prStates))
        prStatesNew[(states >= barrierUp[time]) |
                    (states <= barrierDown[time])] = 0

        # Calculate the probabilities of crossing the up barrier and the
        # down barrier. This is given by the sum, over all states A, of the
        # probability of being in A at the previous timestep times the
        # probability of crossing the barrier if A is the previous state.
        tempUpCross = np.dot(
            prStates, (1 - norm.cdf(changeUp[:, time], mean, sigma)))
        tempDownCross = np.dot(
            prStates, norm.cdf(changeDown[:, time], mean, sigma))

        # Renormalize to cope with numerical approximations.
        sumIn = np.sum(prStates)
        sumCurrent = np.sum(prStatesNew) + tempUpCross + tempDownCross
        prStatesNew = (prStatesNew * float(sumIn)) / float(sumCurrent)
        tempUpCross = (tempUpCross * float(sumIn)) / float(sumCurrent)
        tempDownCross = (tempDownCross * float(sumIn)) / float(sumCurrent)

        # Update the probabilities of each state and the probabilities of
        # crossing each barrier at this timestep.
        prStates = prStatesNew
        probUpCrossing[time] = tempUpCross
        probDownCrossing[time] = tempDownCross

        # Update traces matrix.
        if plotResults:
            traces[:,time] = prStates

    # Compute the likelihood contribution of this trial based on the final
    # choice.
    likelihood = 0
    if choice == -1:  # Choice was left.
        if probUpCrossing[-1] > 0:
            likelihood = probUpCrossing[-1]
    elif choice == 1:  # Choice was right.
        if probDownCrossing[-1] > 0:
            likelihood = probDownCrossing[-1]

    if plotResults:
        fig1 = plt.figure()
        xAxis = np.arange(0, maxTime * timeStep, timeStep)
        yAxis = np.arange(initialBarrierDown, initialBarrierUp + stateStep,
                          stateStep)
        heatmap = plt.pcolor(xAxis, yAxis, np.flipud(traces))
        plt.xlim(0, maxTime * timeStep - timeStep)
        plt.xlabel('Time')
        plt.ylabel('RDV')
        plt.colorbar(heatmap)

        fig2 = plt.figure()
        plt.plot(range(0, len(probUpCrossing) * timeStep, timeStep),
                 probUpCrossing, label='Up')
        plt.plot(range(0, len(probDownCrossing) * timeStep, timeStep),
                 probDownCrossing, label='Down')
        plt.xlabel('Time')
        plt.ylabel('P(crossing)')
        plt.legend()
        plt.show()

    return likelihood


def run_simulations(numTrials, trialConditions, d, sigma, timeStep=10,
                    barrier=1):
    """
    Generates DDM simulations given the model parameters.
    Args:
      numTrials: integer, number of simulations to be generated for each trial
          condition.
      trialConditions: list of tuples, where each entry is a pair (valueLeft,
          valueRight), containing the values of the two items.
      d: float, parameter of the model which controls the speed of integration
          of the signal.
      sigma: float, parameter of the model, standard deviation for the normal
          distribution.
      timeStep: integer, value in miliseconds to be used for binning the time
          axis.
      barrier: positive number, magnitude of the signal thresholds.
    Returns:
      A named tuple containing the following fields:
        RT: dict indexed by trial number, where each entry corresponds to the
            reaction time in miliseconds.
        choice: dict indexed by trial number, where each entry is either -1
            (for left item) or +1 (for right item).
        valueLeft: dict indexed by trial number, where each entry corresponds to
            the value of the left item.
        valueRight: dict indexed by trial number, where each entry corresponds
            to the value of the right item.
    """

    # Simulation data to be returned.
    RT = dict()
    choice = dict()
    valueLeft = dict()
    valueRight = dict()

    trialCount = 0

    for trialCondition in trialConditions:
        vLeft = trialCondition[0]
        vRight = trialCondition[1]
        mean = d * (vLeft - vRight)

        for trial in xrange(numTrials):
            RDV = 0
            time = 0
            while True:
                # If the RDV hit one of the barriers, the trial is over.
                if RDV >= barrier or RDV <= -barrier:
                    RT[trialCount] = time * timeStep
                    valueLeft[trialCount] = vLeft
                    valueRight[trialCount] = vRight
                    if RDV >= barrier:
                        choice[trialCount] = -1
                    elif RDV <= -barrier:
                        choice[trialCount] = 1
                    break

                # Sample the change in RDV from the distribution.
                RDV += np.random.normal(mean, sigma)

                time += 1

            # Move on to the next trial.
            trialCount += 1

    simul = collections.namedtuple('Simul', ['RT', 'choice', 'valueLeft',
                                   'valueRight'])
    return simul(RT, choice, valueLeft, valueRight)
