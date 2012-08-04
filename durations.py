from __future__ import division
import numpy as np
import scipy.stats as stats
import scipy.special as special
from matplotlib import pyplot as plt

from abstractions import DurationDistribution, GibbsSampling

# TODO switch from scipy to numpy for basic distribution sampling

# TODO consider making hyperparameters not explicit so that methods can be more
# generic

# TODO check for np.ndarray, np.concatenate, etc. calls that are unsafe for
# masked arrays

'''
Classes representing duration distributions. Duration distributions are
supported on {1,2,...}, so pmf definitions starting at 0 must be shifted
accordingly.
'''

# TODO TODO below here:
# - capitalize class names
# - clean up statistics etc. computation, check naming conventions

class geometric(DurationDistribution, GibbsSampling, Collapsed):
    '''
    Geometric duration distribution class. Uses a conjugate Beta prior.

    Hyperparameters (following Wikipedia's notation):
        alpha, beta

    Parameters are the success probability:
        p
    '''

    def __repr__(self):
        return 'geometric(p=%0.2f)' % (self.p,)

    def __init__(self, alpha=1., beta=1., p=None):
        self.alpha = alpha
        self.beta = beta
        if p is not None:
            self.p = p
        else:
            self.resample()

    def resample(self,data=np.array([]),**kwargs):
        self.p = stats.beta.rvs(*self.posterior_hypparams(data))

    def log_pmf(self,x,p=None):
        if p is None:
            p = self.p
        x = np.array(x,ndmin=1)
        raw = (x-1.)*np.log(1.-p) + np.log(p)
        raw[x < 1] = np.log(0.)
        return raw if raw.size > 1 else raw[0]

    def pmf(self,x):
        return stats.geom.pmf(x,self.p)

    def log_sf(self,x):
        return np.log(stats.geom.sf(x,self.p))

    def rvs(self,size=[]):
        return stats.geom.rvs(self.p,size=size)

    def marginal_likelihood(self,data):
        alpha_n, beta_n = self.posterior_hypparams(data)
        return special.beta(alpha_n,beta_n)

    def predictive(self,newdata,olddata=np.array([])):
        alpha_all, beta_all = self.posterior_hypparams(combinedata((newdata,olddata)))
        alpha_old, beta_old = self.posterior_hypparams(olddata)
        return np.exp(special.betaln(alpha_all,beta_all)
                    - special.betaln(alpha_old,beta_old))

    def posterior_hypparams(self,data):
        n, tot = self._get_statistics(data)
        return self.alpha + n, self.beta + tot

    @classmethod
    def _get_statistics(cls,data):
        assert (isinstance(data,np.ndarray) and data.ndim == 1 and data.min() >= 1) or \
                (isinstance(data,list) and
                        all((isinstance(d,np.ndarray) and d.ndim == 1 and d.min() >= 1) for d in data))

        if isinstance(data,np.ndarray):
            n = data.shape[0]
            tot = data.sum() - n
        else:
            n = sum(d.shape[0] for d in data)
            tot = sum(d.sum() for d in data) - n
        return n, tot


class poisson(DurationDistribution, GibbsSampling, Collapsed):
    '''
    Poisson duration distribution class. Uses a conjugate Gamma prior.

    Hyperparameters (following Wikipedia's notation):
        alpha, theta

    Parameter is the mean/variance parameter:
        lmbda
    '''

    def __repr__(self):
        return 'poisson(lmbda=%0.2f)' % (self.lmbda,)

    def __init__(self, k, theta, lmbda=None):
        self.k = k
        self.theta = theta
        if lmbda is not None:
            self.lmbda = lmbda
        else:
            self.resample()

    def resample(self,data=np.array([]),**kwargs):
        k_n, theta_n = self.posterior_hypparams(data)
        self.lmbda = stats.gamma.rvs(k_n,loc=0,scale=theta_n)

    def log_pmf(self,x,lmbda=None):
        if lmbda is None:
            lmbda = self.lmbda
        x = np.array(x,ndmin=1)
        raw = -lmbda + (x-1.)*np.log(lmbda) - special.gammaln(x)
        raw[x < 1] = np.log(0.)
        return raw if raw.size > 1 else raw[0]

    def pmf(self,x):
        return stats.poisson.pmf(x-1.,self.lmbda)

    def log_sf(self,x):
        return np.log(stats.poisson.sf(x-1.,self.lmbda))

    def rvs(self,size=[]):
        return stats.poisson.rvs(self.lmbda,size=size,loc=1)

    def marginal_likelihood(self,data):
        k_n, theta_n = self._posterior_hypparams(data,self.k,self.theta)
        return np.exp(special.gammaln(k_n) + k_n * np.log(theta_n))

    def predictive(self,newdata,olddata):
        k_all, theta_all = self.posterior_hypparams(combinedata((olddata,newdata)))
        k_old, theta_old = self.posterior_hypparams(olddata)
        return np.exp( special.gammaln(k_all) + k_all * np.log(theta_all)
                     - special.gammaln(k_old) + k_old * np.log(theta_old) )

    def posterior_hypparams(self,data):
        n, tot = self._get_statistics(data)
        return self.k + tot, self.theta/(self.theta*n+1)

    @classmethod
    def _get_statistics(cls,data):
        assert (isinstance(data,np.ndarray) and data.ndim == 1 and data.min() >= 1) or \
                (isinstance(data,list) and
                        all((isinstance(d,np.ndarray) and d.ndim == 1 and d.min() >= 1) for d in data))

        if isinstance(data,np.ndarray):
            n = data.shape[0]
            tot = data.sum() - n
        else:
            n = sum(d.shape[0] for d in data)
            tot = sum(d.sum() for d in data) - n
        return n, tot

    @classmethod
    def test(cls,num_tests=4,k=8.,theta=5.):
        fig = plt.figure()
        fig.suptitle('pmf, log_pmf, log_sf, rvs consistency')
        for idx in range(num_tests):
            plt.subplot(num_tests,1,idx+1)
            o = cls(k=k,theta=theta)
            data = o.rvs(10000)
            plt.hist(data,np.arange(-0.5,data.max()+0.5,1),normed=True)
            t = np.arange(0,data.max())
            line1 = plt.plot(t,o.pmf(t),'-',marker='.')
            line2 = plt.plot(t,np.exp(o.log_pmf(t)),'x')
            line3 = plt.plot(t[1:],np.diff(1-np.exp(o.log_sf(t))),'k+')

        fig.legend((line1,line2,line3),('%s.pmf' % cls.__name__, 'exp(%s.log_pmf)'% cls.__name__,'diff(1-exp(%s.log_sf))' % cls.__name__), 'lower left')

        fig = plt.figure()
        for idx in range(num_tests):
            fig.suptitle('posterior sampling correctness')
            ogen = cls(k=k,theta=theta)
            data = ogen.rvs(50)
            t = np.arange(0,data.max())
            oinfer = cls(k=k,theta=theta)
            plt.subplot(num_tests,2,2*idx+1)
            plt.hist(data,np.arange(-0.5,data.max()+0.5,1),normed=True)
            line1 = plt.plot(t,oinfer.pmf(t),'r-',marker='.')
            plt.title('before resampling')
            plt.subplot(num_tests,2,2*idx+2)
            oinfer.resample(data)
            plt.hist(data,np.arange(-0.5,data.max()+0.5,1),normed=True)
            line2 = plt.plot(t,oinfer.pmf(t),'g-',marker='.')
            plt.title('after resampling')

        fig.legend((line1,line2),('before resampling','after resampling'),'lower left')

# TODO TODO stuff below here is getting cleaned...

class negative_binomial(DurationDistribution):
    '''
    Negative binomial duration distribution class. Supported on {1,2,...}
    Uses a nonconjugate discrete/Beta prior.

    Hyperparameters follow Wikipedia's notation:
    discrete (vector representation of pmf)
    alpha, beta

    Parameters are the number of geometrics and the sucess probability for each geometric:
    r, p
    only accepts positive integer r!
    '''

    # TODO do smarter resampling with gamma/poisson representation!

    def __repr__(self):
        return 'negbin(r=%d,p=%0.2f)' % (self.r,self.p)

    def __init__(self,discrete=np.ones(6)/6.,alpha=2.,beta=2.,r=None,p=None):
        self.discrete = np.array(discrete,dtype=np.float64) / discrete.sum()
        self.alpha = float(alpha)
        self.beta = float(beta)

        if sum(discrete > 0) == 1:
            assert r is None or discrete[r-1] > 0
            self.r = np.asscalar(np.where(discrete != 0)[0])+1

        if r is not None and p is not None:
            self.r = r
            self.p = p
        else:
            self.resample()

    def resample(self,data=np.array([]),numiter=10):
        if sum(self.discrete > 0) == 1:
            self.resample_fixedr(data)
        else:
            self.resample_changer(data,numiter)

    def resample_fixedr(self,data):
        if len(data) == 0:
            self.p = stats.beta.rvs(self.alpha,self.beta)
        else:
            self.p = stats.beta.rvs(self.alpha + self.r * float(len(data)), self.beta + np.sum(data-1.))

    def resample_changer(self,data,numiter):
        '''
        metropolis-(hastings) / simulated annealing version
        '''
        # TODO make another version that exploits gamma/poisson construction of
        # negbin distribution
        if len(data) == 0:
            self.r = sample_discrete(self.discrete) + 1
            self.p = stats.beta.rvs(self.alpha,self.beta)
        else:
            assert np.min(data) >= 1
            # got this general idea from web.mit.edu/~wingated/www/introductions/mcmc-gibbs-intro.pdf
            # get posterior value of current (r,p)
            current_log_prior_value = stats.beta.logpdf(self.p,self.alpha,self.beta) + np.log(self.discrete[self.r-1])
            current_log_likelihood_value = np.sum(self.log_pmf(data))
            for iter in xrange(numiter):
                # generate proposals, using prior on r and conditionally poterior on p as proposal distribution
                # it uses posterior information in proposing p
                proposal_r = sample_discrete(self.discrete)+1
                proposal_p = stats.beta.rvs(self.alpha + proposal_r * float(len(data)), self.beta + np.sum(data-1.))
                # get posterior value for proposal
                proposal_log_prior_value =  stats.beta.logpdf(proposal_p,self.alpha,self.beta) + np.log(self.discrete[self.r-1])
                proposal_log_likelihood_value = np.sum(self.log_pmf(x=data,r=proposal_r,p=proposal_p))
                # accept proposal with some probability
                accept_probability = np.exp(min(0.,proposal_log_prior_value - current_log_prior_value + proposal_log_likelihood_value - current_log_likelihood_value))
                #accept_probability = min(1, (proposal_prior_value / current_prior_value * np.exp(proposal_log_likelihood_value - current_log_likelihood_value)) )
                if sample_discrete(np.array((1.-accept_probability, accept_probability))):
                    self.r, self.p = proposal_r, proposal_p
                    current_log_prior_value = proposal_log_prior_value
                    current_log_likelihood_value = proposal_log_likelihood_value

    def log_pmf(self,x,r=None,p=None):
        if r is None:
            r = self.r
            p = self.p
        x = np.array(x,ndmin=1)
        r = float(r)
        raw = (special.gammaln(x+r-1) - special.gammaln(x) - special.gammaln(r) + r * np.log(p) + (x-1.) * np.log(1-p))
        raw[x < 1] = np.log(0.)
        if p == 1.:
            raw[np.isnan(raw)] = np.log(1.)
        return raw

    def pmf(self,x,r=None,p=None):
        return np.exp(self.log_pmf(x,r,p))

    def log_sf(self,x,r=None,p=None):
        if r is None:
            r = self.r
        if p is None:
            p = self.p
        x = np.array(x,ndmin=1)
        raw = np.log(1. - special.betainc(r,x,p))
        raw[x < 1] = np.log(1.)
        return raw

    def rvs(self,size=[]):
        return np.sum(stats.geom.rvs(self.p,size=np.concatenate(((self.r,),np.array(size,ndmin=1))),loc=-1.),axis=0)+1

class negative_binomial_fixedr(negative_binomial):
    def __init__(self,r,alpha,beta,p=None):
        self.r = r
        self.alpha = alpha
        self.beta = beta
        if p is not None:
            self.p = p
        else:
            self.resample()

    def resample(self,data=np.array([])):
        if len(data) == 0:
            self.p = stats.beta.rvs(self.alpha,self.beta)
        else:
            assert np.min(data) >= 1
            self.p = stats.beta.rvs(self.alpha + self.r*float(len(data)), self.beta + np.sum(data-1.))


class fixed_wait(DurationDistribution):
    '''
    Meta duration distribution class to offset a duration distribution by a fixed wait.
    Has wait and distn parameters. Minimum wait is zero.
    '''

    def __init__(self,wait,distn):
        self.wait = wait
        self.distn = distn

    def resample(self,data=np.array([]),**kwargs):
        if data.size > 0:
            assert np.min(data) > self.wait
        self.distn.resample(data - self.wait,**kwargs)

    def log_pmf(self,x):
        return self.distn.log_pmf(x-self.wait)

    def log_sf(self,x):
        return self.distn.log_sf(x-self.wait)

    def rvs(self,size=[]):
        return self.distn.rvs(size=size) + self.wait

    def pmf(self,x):
        return self.distn.pmf(x-self.wait)


class learned_wait(fixed_wait):
    '''
    Meta duration distribution class to learn a wait.
    The prior over waits has two components:
    MIN is a nonnegative integer that sets the minimum wait
    discrete is a vector of probabilities to represent a pmf over possible waits, offset by MIN
    '''

    def resample(self,data=np.array([]),numiter=10):
        if data.size == 0:
            # sample from prior
            self.wait = sample_discrete(self.discrete) + self.MIN
            self.distn.resample()
        else:
            assert data.ndim == 1
            # this is a pretty simplistic method
            for iter in xrange(numiter*10):
                # resample posterior wait, given fixed distn
                log_probs = np.sum(self.distn.log_pmf(np.vstack([data - (wait+self.MIN) for wait in xrange(len(self.discrete))])),axis=1)
                log_probs -= np.amax(log_probs)
                self.wait = sample_discrete( self.discrete * np.exp(log_probs) )
                # resample fixed distn given wait
                self.distn.resample(data - self.wait,numiter=numiter)

    def log_pmf(self,x):
        return self.distn.log_pmf(x-(self.wait+self.MIN))

    def log_sf(self,x):
        return self.distn.log_sf(x-(self.wait+self.MIN))

    def rvs(self,size=[]):
        return self.distn.rvs(size=size) + self.wait + self.MIN

    def pmf(self,x):
        return self.distn.pmf(x-(self.wait+self.MIN))


class discrete(DurationDistribution):
    '''
    for simple, short, nonparametric disrete distributions
    (dirichlet/multinomial based)
    '''
    def __init__(self,pseudocounts,distribution=None,dont_resample=False):
        self.pcounts = pseudocounts
        self.dont_resample = dont_resample
        if distribution is None and not dont_resample:
            self.resample()
        else:
            self.distn = distribution

    def resample(self,data=np.array([]),**kwargs):
        if self.dont_resample:
            return
        assert data.ndim == 1
        if len(data) > 0:
            counts = data + self.pcounts
        else:
            counts = self.pcounts
        self.distn = stats.gamma.rvs(counts + 1e-5)
        self.distn[counts == 0] = 0.
        self.distn /= self.distn.sum()

    def log_pmf(self,x):
        x = np.array(x,dtype=np.int32)
        ret = np.log(np.zeros(x.shape))
        valid = np.logical_and(x >= 0, x < len(self.distn))
        ret[valid] = np.log(self.distn[x[valid]])
        return ret

    def pmf(self,x):
        return np.exp(self.log_pmf(x))

    def log_sf(self,x):
        x = np.array(x,dtype=np.int32)
        s = 1. - self.distn.cumsum()
        valid = np.logical_and(x >= 0, x < len(self.distn))
        ret = np.log(np.zeros(x.shape))
        ret[x < 0] = np.log(1.)
        ret[valid] = np.log(s[x[valid]])
        return ret

    def rvs(self,size=[]):
        return sample_discrete(self.distn,size=size)

