import numpy as np
import matplotlib.pyplot as plt
from application.models.LetourneauStentoft import ISD
from application.simulation.sim_gbm import GBM
from application.Longstaff_Schwartz.LSMC import LSMC
from application.utils.LSMC_fit_predict import fit_poly, pred_poly
from application.options.payoff import european_payoff
from application.binomial_model.binomial_model import binomial_tree_bs


if __name__ == '__main__':
    # Fixed parameters
    t0 = 0.0
    T = 1.0
    x0 = 40.0
    N = 100000
    M = 50
    r = 0.06
    sigma = 0.2
    K = 40.0
    seed = 1234
    deg_lsmc = 9
    deg_stentoft = 9
    option_type = 'PUT'

    # Alphas to vary
    alpha = [5, 10, 25, 50, 100]

    # Define range of test spots
    x_test = np.linspace(start=20.0, stop=60.0, num=101, endpoint=True)

    # Binomial model to test against (as "true" prices and deltas)
    binom_price = np.full_like(x_test, np.nan)
    binom_delta = np.full_like(x_test, np.nan)

    for i, x in enumerate(x_test):
        binom = binomial_tree_bs(K=K, T=T, S0=x, r=r, sigma=sigma, M=2500, payoff_func=european_payoff,
                                 option_type=option_type, eur_amr='AMR')
        binom_price[i] = binom[0]
        binom_delta[i] = binom[1]

    # Auxiliary variables
    t = np.linspace(start=t0, stop=T, num=M + 1, endpoint=True)

    # ------------------------------------- #
    # Analysis of Letourneau & Stentoft     #
    # ------------------------------------- #

    # Mean squared error (MSE)
    mse_price = np.zeros_like(alpha, dtype=np.float64)
    mse_delta = np.zeros_like(alpha, dtype=np.float64)

    # Create figures
    fig, ax = plt.subplots(nrows=len(alpha), ncols=2, sharex='col')
    ax[0, 0].set_title('Price')
    ax[0, 1].set_title('Delta')
    ax[len(alpha)-1, 0].set_xlabel('Spot')
    ax[len(alpha)-1, 1].set_xlabel('Spot')

    for i, a in enumerate(alpha):
        # Initiate spots using Initial State Dispersion (ISD)
        x_isd = ISD(N=N, x0=x0, alpha=a, seed=seed)

        # Simulate paths as GBM
        gbm = GBM(t=t, x0=x_isd, N=N, mu=r, sigma=sigma, seed=seed, use_av=True)
        gbm.sim_exact()

        # Run Longstaff-Schwarch Monte Carlo method
        lsmc = LSMC(simulator=gbm, K=K, r=r, payoff_func=european_payoff, option_type=option_type)
        lsmc.run_backwards(fit_func=fit_poly, pred_func=pred_poly, deg=deg_lsmc)

        # Extract (pathwise) payoffs
        cf = lsmc.payoff
        cf = np.sum((cf * lsmc.opt_stopping_rule), axis=0)

        # Calculate discount factor
        df = [np.exp(-r * tau) if ~np.isnan(tau) else 0.0 for tau in lsmc.pathwise_opt_stopping_time]

        # Calculate (pathwise) discounted cashflows
        cf_pv = cf * df

        # Fit polynomials for price and delta
        coef_price = fit_poly(x=x_isd - x0, y=cf_pv, deg=deg_stentoft)  # coefficients `b`
        coef_delta = np.polyder(coef_price, 1)

        # Predict price and delta
        price = pred_poly(x=x_test - x0, fit=coef_price)
        delta = pred_poly(x=x_test - x0, fit=coef_delta)

        # Calculate mse for prices and delta
        mse_price[i] = np.mean((price - binom_price)**2)
        mse_delta[i] = np.mean((delta - binom_delta) ** 2)

        # Add subplot for price
        ax[i, 0].plot(x_test, binom_price, color='red')
        ax[i, 0].scatter(x_isd[:1000], cf_pv[:1000], color='grey', alpha=0.1)
        ax[i, 0].plot(x_test, price, color='blue')
        ax[i, 0].set_ylabel('α={:.1f}'.format(a))
        ax[i, 0].set_xlim(0.8*np.min(x_test), 1.2*np.max(x_test))
        ax[i, 0].set_ylim(-0.2, 1.2*np.max(binom_price))
        ax[i, 0].text(60, (-0.2+1.2*np.max(binom_price))/2, 'MSE = {:.2E}'.format(mse_price[i]))

        # Add subplot for delta
        ax[i, 1].plot(x_test, binom_delta, color='red')
        ax[i, 1].plot(x_test, delta, color='blue')
        ax[i, 1].set_xlim(0.8*np.min(x_test), 1.2*np.max(x_test))
        ax[i, 1].set_ylim(-1.1, 0.1)
        ax[i, 1].text(60, (-1.1 + 0.1)/2, 'MSE = {:.2E}'.format(mse_delta[i]))

    plt.show()
