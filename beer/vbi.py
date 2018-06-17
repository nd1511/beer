
'Variational Bayes Inference.'


import torch


def add_acc_stats(acc_stats1, acc_stats2):
    '''Add two ditionary of accumulated statistics. Both dictionaries
    may have different set of keys. The elements in the dictionary
    should implement the sum operation.

    Args:
        acc_stats1 (dict): First set of accumulated statistics.
        acc_stats2 (dict): Second set of accumulated statistics.

    Returns:
        dict: `acc_stats1` + `acc_stats2`

    '''
    keys1, keys2 = set(acc_stats1.keys()), set(acc_stats2.keys())
    new_stats = {}
    for key in keys1.intersection(keys2):
        new_stats[key] = acc_stats1[key] + acc_stats2[key]

    for key in keys1.difference(keys2):
        new_stats[key] = acc_stats1[key]

    for key in keys2.difference(keys1):
        new_stats[key] = acc_stats2[key]

    return new_stats


class EvidenceLowerBoundInstance:
    '''Evidence Lower Bound of a data set given a model.

    Note:
        This object should not be created directly.

    '''

    def __init__(self, expected_llh, local_kl_div, global_kl_div,
                model_parameters, acc_stats, scale):
        self._exp_llh = expected_llh
        self._global_kl_div = global_kl_div
        self._local_kl_div = local_kl_div
        self._elbo = scale * (self._exp_llh.sum() - \
            self._local_kl_div.sum()) - self._global_kl_div
        self._model_parameters = model_parameters
        self._acc_stats = acc_stats
        self._scale = scale

    def __str__(self):
        return str(self._elbo)

    def __float__(self):
        return float(self._elbo)

    @property
    def kl_div(self):
        'KL divergence term of the ELBO'
        return self._global_kl_div + torch.sum(
            torch.tensor(self._local_kl_div))

    @property
    def expected_llh(self):
        'Expected log-likelihood of the ELBO'
        return self._exp_llh.sum()

    def per_frame(self):
        'ELBO per-frame as a ``torch.Tensor``'
        return self._exp_llh - self._local_kl_div - \
            self._global_kl_div

    def backward(self):
        '''Compute the gradient of the loss w.r.t. to standard
        ``pytorch`` parameters.
        '''
        # Pytorch minimizes the loss ! We change the sign of the ELBO
        # just before to compute the gradient.
        (-self._elbo).backward()

    def natural_backward(self):
        '''Compute the natural gradient of the loss w.r.t. to all the
        :any:`BayesianParameter`.
        '''
        for parameter in self._model_parameters:
            try:
                acc_stats = self._acc_stats[parameter]
                parameter.natural_grad += parameter.prior.natural_hparams +  \
                    self._scale * acc_stats - \
                    parameter.posterior.natural_hparams
            except KeyError:
                pass


class EvidenceLowerBound:
    '''Evidence Lower Bound function.

    Args:
        model (:any:`BayesianModel`): The Bayesian model with which to
            compute the ELBO.
        data (``torch.Tensor``): The data set on which to evaluate the
            ELBO.
        latent_variables (object): Provide latent_variables to the model
            when computing the ELBO.

    Returns:
        ``EvidenceLowerBoundInstance``


    Example:
        >>> # Assume X is our data set and "model" is the model to be
        >>> # trained.
        >>> elbo_fn = beer.EvidenceLowerBound(len(X))
        >>> elbo = elbo_fn(model, X)
        ...
        >>> # Compute gradient of the Baysian parameters.
        >>> elbo.natural_backward()
        ...
        >>> # Compute gradient of standard pytorch parameters.
        >>> elbo.backward()
        ...
        >>> round(float(elbo), 3)
        >>> -10.983


    Note:
        Practically speaking, ``beer`` implements a stochastic version
        of the traditional ELBO. This allows to do stochastic training
        of the models with small batches. It is therefore necessary
        to provide the total length (in frames) of the data when
        creating the loss function as it will scale the natural
        gradient accordingly.

    '''

    def __init__(self, datasize):
        self.datasize = datasize

    def __call__(self, model, data, latent_variables=None):
        s_stats = model.sufficient_statistics(data)
        return EvidenceLowerBoundInstance(
            expected_llh=model(s_stats, latent_variables),
            local_kl_div=model.local_kl_div_posterior_prior(),
            global_kl_div=model.kl_div_posterior_prior(),
            model_parameters=model.parameters,
            acc_stats=model.accumulate(s_stats),
            scale=self.datasize / float(len(data))
        )


class BayesianModelOptimizer:
    '''Generic optimizer for :any:`BayesianModel` subclasses.

    Args:
        parameters (list): List of :any:`BayesianParameter`.
        lrate (float): Learning rate for the :any:`BayesianParameter`.
        std_optim (``torch.Optimizer``): pytorch optimizer.

    Note:
        For models that require some standard gradient descent (for
        instance Variational AutoEncoder), it is possible to combined
        natural and standard gradient descent by providing a pytorch
        optimizer through the keyword argument ``std_optim``.

    Example:
        >>> # Assume "model" is a BayesianModel to be trained and X is
        >>> # the dataset.
        >>> elbo_fn = beer.EvidenceLowerBound(len(X))
        >>> optim = beer.BayesianModelOptimizer(model.parameters)
        >>> for epoch in range(10):
        >>>     optim.zero_grad()
        >>>     elbo = elbo_fn(model, X)
        >>>     elbo.natural_backward()
        >>>     optim.step()

    '''

    def __init__(self, parameters, lrate=1., std_optim=None):
        '''
        Args:
            parameters (list): List of ``BayesianParameters``.
            lrate (float): learning rate.
            std_optim (``torch.optim.Optimizer``): Optimizer for
                non-Bayesian parameters (i.e. standard ``pytorch``
                parameters)
        '''
        self._parameters = parameters
        self._lrate = lrate
        self._std_optim = std_optim

    def zero_grad(self):
        'Set all the standard/Bayesian parameters gradient to zero.'
        if self._std_optim is not None:
            self._std_optim.zero_grad()
        for parameter in self._parameters:
            parameter.zero_natural_grad()

    def step(self):
        'Update all the standard/Bayesian parameters.'
        if self._std_optim is not None:
            self._std_optim.step()
        for parameter in self._parameters:
            parameter.posterior.natural_hparams = torch.tensor(
                parameter.posterior.natural_hparams + \
                self._lrate * parameter.natural_grad,
                requires_grad=True
            )


class BayesianModelCoordinateAscentOptimizer(BayesianModelOptimizer):
    '''Optimizer that update iteratively groups of parameters. This
    optimizer is suited for model like PPCA which cannot estimate the
    gradient of all its paramaters at once.


    Example:
        >>> # Assume "model" is a BayesianModel to be trained and X is
        >>> # the dataset.
        >>> elbo_fn = beer.EvidenceLowerBound(len(X))
        >>> optim = beer.BayesianModelCoordinateAscentOptimizer(model.parameters)
        >>> for epoch in range(10):
        >>>     optim.zero_grad()
        >>>     elbo = elbo_fn(model, X)
        >>>     elbo.natural_backward()
        >>>     optim.step()

    '''

    def __init__(self, *groups, lrate=1., std_optim=None):
        '''
        Args:
            ... (list): N List of ``BayesianParameter``.
                to be updated separately.
            lrate (float): learning rate.
            std_optim (``torch.optim.Optimizer``): Optimizer for
                non-Bayesian parameters (i.e. standard ``pytorch``
                parameters)
        '''
        parameters = []
        for group in groups:
            parameters += group
        super().__init__(parameters, lrate=lrate, std_optim=std_optim)
        self._groups = groups
        self._update_count = 0

    def step(self):
        'Update one group the standard/Bayesian parameters.'
        if self._std_optim is not None:
            self._std_optim.step()
        if self._update_count >= len(self._groups):
            self._update_count = 0
        for parameter in self._groups[self._update_count]:
            parameter.posterior.natural_hparams = torch.tensor(
                parameter.posterior.natural_hparams + \
                self._lrate * parameter.natural_grad,
                requires_grad=True
            )
        self._update_count += 1


__all__ = ['EvidenceLowerBound', 'BayesianModelOptimizer',
           'BayesianModelCoordinateAscentOptimizer']
