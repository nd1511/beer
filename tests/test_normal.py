'Test the Normal model.'



import unittest
import numpy as np
import math
import torch

import sys
sys.path.insert(0, './')

import beer
from beer import NormalGammaPrior
from beer import NormalWishartPrior


torch.manual_seed(10)


TOLPLACES = 5
TOL = 10 ** (-TOLPLACES)


class TestNormalDiagonalCovariance:

    def test_create(self):
        model = beer.NormalDiagonalCovariance(
            NormalGammaPrior(self.mean, self.prec, self.prior_count),
            NormalGammaPrior(self.mean, self.prec, self.prior_count)
        )
        m1, m2 = self.mean.numpy(), model.mean.numpy()
        self.assertTrue(np.allclose(m1, m2, atol=TOL))
        c1, c2 = (1. / self.prec.numpy()), model.cov.numpy()
        if len(c1.shape) == 1:
            c1 = np.diag(c1)
        self.assertTrue(np.allclose(c1, c2, atol=TOL))

    def test_sufficient_statistics(self):
        X =  self.X.numpy()
        s1 = np.c_[self.X**2, self.X, np.ones_like(X), np.ones_like(X)]
        s2 = beer.NormalDiagonalCovariance.sufficient_statistics(self.X)
        self.assertTrue(np.allclose(s1, s2.numpy(), atol=TOL))

    def test_sufficient_statistics_from_mean_var(self):
        mean = self.mean.view(1, -1)
        var = (1. / self.prec.view(1, -1))
        if len(var.size()) == 2:
            var = torch.diag(var)
        s1 = beer.NormalDiagonalCovariance.sufficient_statistics_from_mean_var(
            mean, var)
        mean, var = mean.numpy(), var.numpy()
        s2 = np.c_[mean**2 + var, mean, np.ones_like(mean),
                   np.ones_like(mean)]
        self.assertTrue(np.allclose(s1.numpy(), s2, atol=TOL))

    def test_exp_llh(self):
        model = beer.NormalDiagonalCovariance(
            NormalGammaPrior(self.mean, self.prec, self.prior_count),
            NormalGammaPrior(self.mean, self.prec, self.prior_count)
        )
        T = model.sufficient_statistics(self.X)
        nparams = model._mean_prec.expected_value
        exp_llh1 = T @ nparams
        exp_llh1 -= .5 * self.X.size(1) * math.log(2 * math.pi)
        exp_llh2 = model(T)
        self.assertTrue(np.allclose(exp_llh1.numpy(), exp_llh2.numpy(),
                        atol=TOL))



class TestNormalFullCovariance:

    def test_create(self):
        model = beer.NormalFullCovariance(
            NormalWishartPrior(self.mean, self.cov, self.prior_count),
            NormalWishartPrior(self.mean, self.cov, self.prior_count)
        )
        m1, m2 = self.mean.numpy(), model.mean.numpy()
        self.assertTrue(np.allclose(m1, m2))
        c1, c2 = self.cov.numpy(), model.cov.numpy()
        self.assertTrue(np.allclose(c1, c2, atol=TOL))

    def test_sufficient_statistics(self):
        X = self.X.numpy()
        s1 = np.c_[(X[:, :, None] * X[:, None, :]).reshape(len(X), -1),
            X, np.ones(len(X)), np.ones(len(X))]
        s2 = beer.NormalFullCovariance.sufficient_statistics(self.X)
        self.assertTrue(np.allclose(s1, s2.numpy(), atol=TOL))

    def test_sufficient_statistics_from_mean_var(self):
        mean = self.mean.view(1, -1)
        var = torch.diag(self.cov).view(1, -1)
        s1 = beer.NormalFullCovariance.sufficient_statistics_from_mean_var(
            mean, var)
        mean, var = mean.numpy(), var.numpy()
        idxs = np.identity(mean.shape[1]).reshape(-1) == 1
        XX = (mean[:, :, None] * mean[:, None, :]).reshape(mean.shape[0], -1)
        XX[:, idxs] += var
        s2 = np.c_[XX, mean, np.ones(len(mean)), np.ones(len(mean))]
        self.assertTrue(np.allclose(s1.numpy(), s2, atol=TOL))

    def test_exp_llh(self):
        model = beer.NormalFullCovariance(
            NormalWishartPrior(self.mean, self.cov, self.prior_count),
            NormalWishartPrior(self.mean, self.cov, self.prior_count)
        )
        T = model.sufficient_statistics(self.X)
        nparams = model._mean_prec.expected_value
        exp_llh1 = T @ nparams
        exp_llh1 -= .5 * self.X.size(1) * math.log(2 * math.pi)
        exp_llh2 = model(T)
        self.assertTrue(np.allclose(exp_llh1.numpy(), exp_llh2.numpy(),
                        atol=TOL))


class TestNormalDiagonalCovarianceSet:

    def test_create(self):
        posts = [NormalGammaPrior(self.mean, self.prec, self.prior_count)
                 for _ in range(self.ncomps)]
        model = beer.NormalDiagonalCovarianceSet(
            NormalGammaPrior(self.mean, self.prec, self.prior_count),
            posts
        )
        self.assertEqual(len(model.components), self.ncomps)
        for i in range(self.ncomps):
            m1, m2 = self.mean.numpy(), model.components[i].mean.numpy()
            self.assertTrue(np.allclose(m1, m2, atol=TOL))
            c1, c2 = (1. / self.prec.numpy()), torch.diag(model.components[i].cov).numpy()
            self.assertTrue(np.allclose(c1, c2, atol=TOL))

    def test_sufficient_statistics(self):
        s1 = beer.NormalDiagonalCovariance.sufficient_statistics(self.X)
        s2 = beer.NormalDiagonalCovarianceSet.sufficient_statistics(self.X)
        self.assertTrue(np.allclose(s1.numpy(), s2.numpy(), atol=TOL))

    def test_sufficient_statistics_from_mean_var(self):
        mean = self.mean.view(1, -1)
        var = (1. / self.prec.view(1, -1))
        s1 = beer.NormalDiagonalCovariance.sufficient_statistics_from_mean_var(
            mean, var)
        s2 = beer.NormalDiagonalCovarianceSet.sufficient_statistics_from_mean_var(
            mean, var)
        self.assertTrue(np.allclose(s1.numpy(), s2.numpy(), atol=TOL))

    def test_forward(self):
        posts = [NormalGammaPrior(self.mean, self.prec, self.prior_count)
                 for _ in range(self.ncomps)]
        model = beer.NormalDiagonalCovarianceSet(
            NormalGammaPrior(self.mean, self.prec, self.prior_count),
            posts
        )
        matrix = torch.cat([param.expected_value[None]
            for param in model.parameters], dim=0)
        T = model.sufficient_statistics(self.X)
        exp_llh1 = T @ matrix.t()
        exp_llh1 -= .5 * self.X.size(1) * math.log(2 * math.pi)
        exp_llh2 = model(T)
        self.assertTrue(np.allclose(exp_llh1.numpy(), exp_llh2.numpy()))

    def test_accumulate(self):
        posts = [NormalGammaPrior(self.mean, self.prec, self.prior_count)
                 for _ in range(self.ncomps)]
        model = beer.NormalDiagonalCovarianceSet(
            NormalGammaPrior(self.mean, self.prec, self.prior_count),
            posts
        )
        weights = torch.ones(len(self.X), self.ncomps).type(self.X.type())
        T = model.sufficient_statistics(self.X)
        acc_stats1 = list(weights.t() @ T)
        acc_stats2 = model.accumulate(T, weights)
        for s1, s2 in zip(acc_stats1, acc_stats2):
            self.assertTrue(np.allclose(s1.numpy(), s2.numpy()))


class TestNormalFullCovarianceSet:

    def test_create(self):
        posts = [NormalWishartPrior(self.mean, self.cov, self.prior_count)
                 for _ in range(self.ncomps)]
        model = beer.NormalFullCovarianceSet(
            NormalWishartPrior(self.mean, self.cov, self.prior_count),
            posts
        )
        self.assertEqual(len(model.components), self.ncomps)
        for i in range(self.ncomps):
            m1, m2 = self.mean.numpy(), model.components[i].mean.numpy()
            self.assertTrue(np.allclose(m1, m2))
            c1, c2 = self.cov.numpy(), model.components[i].cov.numpy()
            self.assertTrue(np.allclose(c1, c2, atol=TOL))

    def test_sufficient_statistics(self):
        s1 = beer.NormalFullCovariance.sufficient_statistics(self.X)
        s2 = beer.NormalFullCovarianceSet.sufficient_statistics(self.X)
        self.assertTrue(np.allclose(s1.numpy(), s2.numpy(), atol=TOL))

    def test_sufficient_statistics_from_mean_var(self):
        mean = self.mean.view(1, -1)
        var = torch.diag(self.cov).view(1, -1)
        s1 = beer.NormalFullCovariance.sufficient_statistics_from_mean_var(
            mean, var)
        s2 = beer.NormalFullCovarianceSet.sufficient_statistics_from_mean_var(
            mean, var)
        self.assertTrue(np.allclose(s1.numpy(), s2.numpy(), atol=TOL))

    def test_forward(self):
        posts = [NormalWishartPrior(self.mean, self.cov, self.prior_count)
                 for _ in range(self.ncomps)]
        model = beer.NormalFullCovarianceSet(
            NormalWishartPrior(self.mean, self.cov, self.prior_count),
            posts
        )
        matrix = torch.cat([param.expected_value[None]
            for param in model.parameters], dim=0)
        T = model.sufficient_statistics(self.X)
        exp_llh1 = T @ matrix.t()
        exp_llh1 -= .5 * self.X.size(1) * math.log(2 * math.pi)
        exp_llh2 = model(T)
        self.assertTrue(np.allclose(exp_llh1.numpy(), exp_llh2.numpy()))

    def test_accumulate(self):
        posts = [NormalWishartPrior(self.mean, self.cov, self.prior_count)
                 for _ in range(self.ncomps)]
        model = beer.NormalFullCovarianceSet(
            NormalWishartPrior(self.mean, self.cov, self.prior_count),
            posts
        )
        weights = torch.ones(len(self.X), self.ncomps).type(self.X.type())
        T = model.sufficient_statistics(self.X)
        acc_stats1 = list(weights.t() @ T)
        acc_stats2 = model.accumulate(T, weights)
        for s1, s2 in zip(acc_stats1, acc_stats2):
            self.assertTrue(np.allclose(s1.numpy(), s2.numpy()))


dataF = {
    'X': torch.randn(20, 2).float(),
    'means': torch.randn(20, 2).float(),
    'vars': torch.randn(20, 2).float() ** 2
}

dataD = {
    'X': torch.randn(20, 2).double(),
    'means': torch.randn(20, 2).double(),
    'vars': torch.randn(20, 2).double() ** 2
}

data10F = {
    'X': torch.randn(20, 10).float(),
    'means': torch.randn(20, 10).float(),
    'vars': torch.randn(20, 10).float() ** 2
}

data10D = {
    'X': torch.randn(20, 10).double(),
    'means': torch.randn(20, 10).double(),
    'vars': torch.randn(20, 2).double() ** 2
}


tests = [
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).float(),
        'prec': torch.ones(2).float(), 'prior_count': 1., **dataF}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).double(),
        'prec': torch.ones(2).double(), 'prior_count': 1., **dataD}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(10).float(), 'prec':
        torch.ones(10).float(), 'prior_count': 1., **data10F}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(10).double(), 'prec':
         torch.ones(10).double(), 'prior_count': 1., **data10D}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).float(), 'prec':
         torch.ones(2).float(), 'prior_count': 1e-3, **dataF}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).double(), 'prec':
         torch.ones(2).double(), 'prior_count': 1e-8, **dataD}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).float(), 'prec':
         torch.ones(2).float() * 1e-2, 'prior_count': 1., **dataF}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).double(), 'prec':
         torch.ones(2).double() * 1e-8, 'prior_count': 1., **dataD}),
    (TestNormalDiagonalCovariance, {'mean': torch.ones(2).float(), 'prec':
         torch.ones(2).float() * 1e2, 'prior_count': 1., **dataF}),

    (TestNormalFullCovariance, {'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1., **dataF}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1., **dataD}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).float(),
        'cov': torch.FloatTensor([[2, -1.2], [-1.2, 10.]]).float(),
        'prior_count': 1., **dataF}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).float(),
        'cov': torch.DoubleTensor([[2, -1.2], [-1.2, 10.]]).float(),
        'prior_count': 1., **dataF}),
    (TestNormalFullCovariance, {'mean': torch.ones(10).float(),
        'cov': torch.eye(10).float(), 'prior_count': 1., **data10F}),
    (TestNormalFullCovariance, {'mean': torch.ones(10).double(),
        'cov': torch.eye(10).double(), 'prior_count': 1., **data10D}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1e-3, **dataF}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1e-7, **dataD}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float() * 1e-5, 'prior_count': 1., **dataF}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1., **dataD}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float() * 1e2, 'prior_count': 1., **dataF}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double() * 1e8, 'prior_count': 1., **dataD}),
    (TestNormalFullCovariance, {'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double() * 1e8, 'prior_count': 1., **dataD}),

    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'prec': torch.ones(2).float(), 'prior_count': 1., **dataF}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(),
        'prec': torch.ones(2).double(), 'prior_count': 1., **dataD}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(10).float(), 'prec':
        torch.ones(10).float(), 'prior_count': 1., **data10F}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(10).double(), 'prec':
         torch.ones(10).double(), 'prior_count': 1., **data10D}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(), 'prec':
         torch.ones(2).float(), 'prior_count': 1e-3, **dataF}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(), 'prec':
         torch.ones(2).double(), 'prior_count': 1e-8, **dataD}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(), 'prec':
         torch.ones(2).float() * 1e-2, 'prior_count': 1., **dataF}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(), 'prec':
         torch.ones(2).double() * 1e-8, 'prior_count': 1., **dataD}),
    (TestNormalDiagonalCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(), 'prec':
         torch.ones(2).float() * 1e2, 'prior_count': 1., **dataF}),

    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1., **dataF}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1., **dataD}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'cov': torch.FloatTensor([[2, -1.2], [-1.2, 10.]]).float(),
        'prior_count': 1., **dataF}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'cov': torch.DoubleTensor([[2, -1.2], [-1.2, 10.]]).float(),
        'prior_count': 1., **dataF}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(10).float(),
        'cov': torch.eye(10).float(), 'prior_count': 1., **data10F}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(10).double(),
        'cov': torch.eye(10).double(), 'prior_count': 1., **data10D}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float(), 'prior_count': 1e-3, **dataF}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double(), 'prior_count': 1e-7, **dataD}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float() * 1e-5, 'prior_count': 1., **dataF}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double() * 1e-8, 'prior_count': 1., **dataD}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).float(),
        'cov': torch.eye(2).float() * 1e2, 'prior_count': 1., **dataF}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double() * 1e8, 'prior_count': 1., **dataD}),
    (TestNormalFullCovarianceSet, {'ncomps': 13, 'mean': torch.ones(2).double(),
        'cov': torch.eye(2).double() * 1e8, 'prior_count': 1., **dataD}),
]


module = sys.modules[__name__]
for i, test in enumerate(tests, start=1):
    name = test[0].__name__ + 'Test' + str(i)
    setattr(module, name, type(name, (unittest.TestCase, test[0]),  test[1]))

if __name__ == '__main__':
    unittest.main()
