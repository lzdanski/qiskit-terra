# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name,missing-docstring
"""Equivalence tests for quantum channel methods."""

import unittest

import numpy as np

from qiskit.quantum_info.operators.channel.unitarychannel import UnitaryChannel
from qiskit.quantum_info.operators.channel.choi import Choi
from qiskit.quantum_info.operators.channel.superop import SuperOp
from qiskit.quantum_info.operators.channel.kraus import Kraus
from qiskit.quantum_info.operators.channel.stinespring import Stinespring
from qiskit.quantum_info.operators.channel.ptm import PTM
from qiskit.quantum_info.operators.channel.chi import Chi
from .base import ChannelTestCase


class TestEquivalence(ChannelTestCase):
    """Tests for channel equivalence for linear operations.

    This tests that addition, subtraction, multiplication and negatation
    work for all representations as if they were performed in the SuperOp
    representation.s equivalent to performing the same
    operations in other representations.
    """

    def _compare_add_to_superop(self, rep, dim, samples, unitary=False):
        """Test channel addition is equivalent to SuperOp"""
        for _ in range(samples):
            if unitary:
                mat1 = self.rand_matrix(dim, dim)
                mat2 = self.rand_matrix(dim, dim)
                sop1 = np.kron(np.conj(mat1), mat1)
                sop2 = np.kron(np.conj(mat2), mat2)
            else:
                sop1 = self.rand_matrix(dim * dim, dim * dim)
                sop2 = self.rand_matrix(dim * dim, dim * dim)
            targ = SuperOp(sop1 + sop2)
            channel = SuperOp(rep(SuperOp(sop1)).add(rep(SuperOp(sop2))))
            self.assertEqual(channel, targ)

    def _compare_subtract_to_superop(self, rep, dim, samples, unitary=False):
        """Test channel subtraction is equivalent to SuperOp"""
        for _ in range(samples):
            if unitary:
                mat1 = self.rand_matrix(dim, dim)
                mat2 = self.rand_matrix(dim, dim)
                sop1 = np.kron(np.conj(mat1), mat1)
                sop2 = np.kron(np.conj(mat2), mat2)
            else:
                sop1 = self.rand_matrix(dim * dim, dim * dim)
                sop2 = self.rand_matrix(dim * dim, dim * dim)
            targ = SuperOp(sop1 - sop2)
            channel = SuperOp(rep(SuperOp(sop1)).subtract(rep(SuperOp(sop2))))
            self.assertEqual(channel, targ)

    def _compare_multiply_to_superop(self, rep, dim, samples, unitary=False):
        """Test channel scalar multiplication is equivalent to SuperOp"""
        for _ in range(samples):
            if unitary:
                mat1 = self.rand_matrix(dim, dim)
                sop1 = np.kron(np.conj(mat1), mat1)
            else:
                sop1 = self.rand_matrix(dim * dim, dim * dim)
            val = 2 * (np.random.rand() - 0.5)
            targ = SuperOp(val * sop1)
            channel = SuperOp(rep(SuperOp(sop1)).multiply(val))
            self.assertEqual(channel, targ)

    def _compare_negate_to_superop(self, rep, dim, samples, unitary=False):
        """Test negative channel is equivalent to SuperOp"""
        for _ in range(samples):
            if unitary:
                mat1 = self.rand_matrix(dim, dim)
                sop1 = np.kron(np.conj(mat1), mat1)
            else:
                sop1 = self.rand_matrix(dim * dim, dim * dim)
            targ = SuperOp(-1 * sop1)
            channel = SuperOp(-rep(SuperOp(sop1)))
            self.assertEqual(channel, targ)

    def _check_add_other_reps(self, chan):
        """Check addition works for other representations"""
        current_rep = chan.__class__
        other_reps = [
            UnitaryChannel, Choi, SuperOp, Kraus, Stinespring, Chi, PTM
        ]
        for rep in other_reps:
            self.assertEqual(current_rep, chan.add(rep(chan)).__class__)

    def _check_subtract_other_reps(self, chan):
        """Check subtraction works for other representations"""
        current_rep = chan.__class__
        other_reps = [
            UnitaryChannel, Choi, SuperOp, Kraus, Stinespring, Chi, PTM
        ]
        for rep in other_reps:
            self.assertEqual(current_rep, chan.subtract(rep(chan)).__class__)

    def test_choi_add(self):
        """Test addition of Choi matrices is correct."""
        self._compare_add_to_superop(Choi, 4, 10)

    def test_kraus_add(self):
        """Test addition of Kraus matrices is correct."""
        self._compare_add_to_superop(Kraus, 4, 10)

    def test_stinespring_add(self):
        """Test addition of Stinespring matrices is correct."""
        self._compare_add_to_superop(Stinespring, 4, 10)

    def test_chi_add(self):
        """Test addition of Chi matrices is correct."""
        self._compare_add_to_superop(Chi, 4, 10)

    def test_ptm_add(self):
        """Test addition of PTM matrices is correct."""
        self._compare_add_to_superop(PTM, 4, 10)

    def test_choi_subtract(self):
        """Test subtraction of Choi matrices is correct."""
        self._compare_subtract_to_superop(Choi, 4, 10)

    def test_kraus_subtract(self):
        """Test subtraction of Kraus matrices is correct."""
        self._compare_subtract_to_superop(Kraus, 4, 10)

    def test_stinespring_subtract(self):
        """Test subtraction of Stinespring matrices is correct."""
        self._compare_subtract_to_superop(Stinespring, 4, 10)

    def test_chi_subtract(self):
        """Test subtraction of Chi matrices is correct."""
        self._compare_subtract_to_superop(Chi, 4, 10)

    def test_ptm_subtract(self):
        """Test subtraction of PTM matrices is correct."""
        self._compare_subtract_to_superop(PTM, 4, 10)

    def test_choi_multiply(self):
        """Test scalar multiplication of Choi matrices is correct."""
        self._compare_multiply_to_superop(Choi, 4, 10)

    def test_kraus_multiply(self):
        """Test scalar multiplication of Kraus matrices is correct."""
        self._compare_multiply_to_superop(Kraus, 4, 10)

    def test_stinespring_multiply(self):
        """Test scalar multiplication of Stinespring matrices is correct."""
        self._compare_multiply_to_superop(Stinespring, 4, 10)

    def test_chi_multiply(self):
        """Test scalar multiplication of Chi matrices is correct."""
        self._compare_multiply_to_superop(Chi, 4, 10)

    def test_ptm_multiply(self):
        """Test scalar multiplication of PTM matrices is correct."""
        self._compare_multiply_to_superop(PTM, 4, 10)

    def test_choi_add_other_rep(self):
        """Test addition of Choi matrices is correct."""
        chan = Choi(self.choiI)
        self._check_add_other_reps(chan)

    def test_superop_add_other_rep(self):
        """Test addition of SuperOp matrices is correct."""
        chan = SuperOp(self.sopI)
        self._check_add_other_reps(chan)

    def test_kraus_add_other_rep(self):
        """Test addition of Kraus matrices is correct."""
        chan = Kraus(self.matI)
        self._check_add_other_reps(chan)

    def test_stinespring_add_other_rep(self):
        """Test addition of Stinespring matrices is correct."""
        chan = Stinespring(self.matI)
        self._check_add_other_reps(chan)

    def test_chi_add_other_rep(self):
        """Test addition of Chi matrices is correct."""
        chan = Chi(self.chiI)
        self._check_add_other_reps(chan)

    def test_ptm_add_other_rep(self):
        """Test addition of PTM matrices is correct."""
        chan = PTM(self.ptmI)
        self._check_add_other_reps(chan)

    def test_choi_subtract_other_rep(self):
        """Test subtraction of Choi matrices is correct."""
        chan = Choi(self.choiI)
        self._check_subtract_other_reps(chan)

    def test_superop_subtract_other_rep(self):
        """Test subtraction of SuperOp matrices is correct."""
        chan = SuperOp(self.sopI)
        self._check_subtract_other_reps(chan)

    def test_kraus_subtract_other_rep(self):
        """Test subtraction of Kraus matrices is correct."""
        chan = Kraus(self.matI)
        self._check_subtract_other_reps(chan)

    def test_stinespring_subtract_other_rep(self):
        """Test subtraction of Stinespring matrices is correct."""
        chan = Stinespring(self.matI)
        self._check_subtract_other_reps(chan)

    def test_chi_subtract_other_rep(self):
        """Test subtraction of Chi matrices is correct."""
        chan = Chi(self.chiI)
        self._check_subtract_other_reps(chan)

    def test_ptm_subtract_other_rep(self):
        """Test subtraction of PTM matrices is correct."""
        chan = PTM(self.ptmI)
        self._check_subtract_other_reps(chan)


if __name__ == '__main__':
    unittest.main()
