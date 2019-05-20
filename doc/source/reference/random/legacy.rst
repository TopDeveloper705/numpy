Legacy Random Generation
------------------------
The :class:`~legacy.LegacyGenerator` provides access to 
legacy generators.  These all depend on Box-Muller normals or
inverse CDF exponentials or gammas. This class should only be used 
if it is essential to have randoms that are identical to what
would have been produced by NumPy. 

:class:`~legacy.LegacyGenerator` add additional information
to the state which is required when using Box-Muller normals since these
are produced in pairs. It is important to use 
:attr:`~legacy.LegacyGenerator.state` 
when accessing the state so that these extra values are saved. 

.. warning::

  :class:`~randomgen.legacy.LegacyGenerator` only contains functions
  that have changed.  Since it does not contain other functions, it 
  is not direclty possible to replace :class:`~numpy.random.RandomState`.
  In order to full replace :class:`~numpy.random.RandomState`, it is
  necessary to use both :class:`~randomgen.legacy.LegacyGenerator`
  and :class:`~randomgen.generator.RandomGenerator` both driven
  by the same basic RNG. Methods present in :class:`~randomgen.legacy.LegacyGenerator`
  must be called from :class:`~randomgen.legacy.LegacyGenerator`.  Other Methods
  should be called from :class:`~randomgen.generator.RandomGenerator`.


.. code-block:: python
  
   from numpy.random import MT19937
   from numpy.random.legacy import LegacyGenerator
   from numpy.random import RandomState
      # Use same seed
   rs = RandomState(12345)
   mt19937 = MT19937(12345)
   rg = RandomGenerator(mt19937)
   lg = LegacyGenerator(mt19937)

   # Identical output
   rs.standard_normal()
   lg.standard_normal()

   rs.random_sample()
   rg.random_sample()

   rs.standard_exponential()
   lg.standard_exponential()
   

.. currentmodule:: numpy.random.legacy

.. autoclass:: LegacyGenerator
	:exclude-members:

Seeding and State
=================

.. autosummary::
   :toctree: generated/

   ~LegacyGenerator.get_state
   ~LegacyGenerator.set_state
   
Simple random data
==================
.. autosummary::
   :toctree: generated/

   ~LegacyGenerator.randn
   ~LegacyGenerator.randint
   ~LegacyGenerator.random_integers
   ~LegacyGenerator.random_sample
   ~LegacyGenerator.choice
   ~LegacyGenerator.bytes

Permutations
============
.. autosummary::
   :toctree: generated/

   ~LegacyGenerator.shuffle
   ~LegacyGenerator.permutation

Distributions
=============
.. autosummary::
   :toctree: generated/

   ~LegacyGenerator.beta
   ~LegacyGenerator.chisquare
   ~LegacyGenerator.dirichlet
   ~LegacyGenerator.exponential
   ~LegacyGenerator.f
   ~LegacyGenerator.gamma
   ~LegacyGenerator.lognormal
   ~LegacyGenerator.multivariate_normal
   ~LegacyGenerator.negative_binomial
   ~LegacyGenerator.noncentral_chisquare
   ~LegacyGenerator.noncentral_f
   ~LegacyGenerator.normal
   ~LegacyGenerator.pareto
   ~LegacyGenerator.power
   ~LegacyGenerator.standard_cauchy
   ~LegacyGenerator.standard_exponential
   ~LegacyGenerator.standard_gamma
   ~LegacyGenerator.standard_normal
   ~LegacyGenerator.standard_t
   ~LegacyGenerator.wald
   ~LegacyGenerator.weibull
   ~LegacyGenerator.zipf
