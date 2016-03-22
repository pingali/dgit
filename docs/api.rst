Dataset API
-----------

Example: 

.. code-block:: python 
   
   from dgitcore import api 
   repo = api.datasets.lookup('pingali', 'simple-regression-rawdata') 
   r = repo.get_resource('demo-input.csv') 
   df = pd.read_csv(r['localfullpath'])


.. automodule:: dgitcore.api 
   :members: 
