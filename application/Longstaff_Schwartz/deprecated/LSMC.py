import numpy as np
from application.options.payoff import european_payoff
from application.simulation.sim_gbm import sim_gbm
from application.Longstaff_Schwartz.utils.fit_predict import *


def lsmc(t, X, K, r, payoff_func, type, fit_func, pred_func, *args, **kwargs):
    """
    Longstaff-Schwartz Monte Carlo method for pricing an American option.

    :param t:               Time steps
    :param X:               Simulated paths
    :param K:               Strike
    :param r:               Risk free rate
    :param payoff_func:     Payoff function to be called
    :param type:            Type of option
    :param fit_func         Function for fitting the (expected) value of value of continuation
    :param pred_func        Function for predicting the (expected) value of continuation
    :return:                Price of the american option
    """

    assert np.ndim(t) == 1, "Time steps must be a 1-dimensional array."
    assert np.ndim(X) == 2, "The passed simulations `X` mush be a 2-dimensional numpy-array."
    assert len(X) == len(t), "The length of the passed simulations `X` and time steps `t` must be of same length."

    M = len(t) - 1
    N = np.shape(X)[1]

    dt = np.diff(t)

    # Initiate
    discount_factor = np.exp(-r * dt)
    payoff = payoff_func(X, K, type)

    # formatting stopping rule and cashflow-matrix
    stopping_rule = np.full((M, N), False)
    cashflow = np.full((M, N), np.nan)

    stopping_rule[M-1:, ] = payoff[M, :] > 0
    cashflow[M-1, :] = payoff[M, :]

    for j in range(M-1, 0, -1):
        itm = payoff[j, :] > 0

        # Fit function for expected value of continuation
        fit = fit_func(X[j, itm], cashflow[j, itm] * discount_factor[j], *args, **kwargs)

        # Determine stopping rule by
        # comparing the value of exercising with the predicted (expected) value of continuation
        EV_cont = pred_func(X[j, itm], fit, *args, **kwargs)
        exercise = payoff[j, itm]

        stopping_rule[j-1, itm] = exercise > EV_cont

        # Update cash-flow matrix
        cashflow[j-1, :] = stopping_rule[j-1, :] * payoff[j, :]

    # Format stopping rule and cashflow-matrix
    stopping_rule = np.cumsum(np.cumsum(stopping_rule, axis=0), axis=0) == 1
    cashflow = stopping_rule * cashflow

    # Calculate price
    price = np.mean(cashflow.T @ np.cumprod(discount_factor))

    return price


if __name__ == '__main__':
    # Simulating with GBM
    x0 = 36
    K = 40
    r = 0.06
    t0 = 0.0
    T = 1.0
    N = 100000
    M = 50
    sigma = 0.2
    type = 'PUT'
    seed = 1234

    t = np.linspace(start=t0, stop=T, num=M + 1, endpoint=True)
    X = sim_gbm(t=t, x0=x0, N=N, mu=r, sigma=sigma, seed=seed)
    for deg in [3]:
        print('deg =', deg, ": Price with GBM simulation =", lsmc(t=t, X=X, K=K, r=r, payoff_func=european_payoff,
                                                                  type=type, fit_func=fit_laguerre_poly,
                                                                  pred_func=pred_laguerre_poly,
                                                                  deg=deg))
