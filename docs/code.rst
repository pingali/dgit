Code
====

Repo Manager
---------------

dgit supports multiple ways to store datasets. It could be git itself,
local filesystem (possibly, with s3 backend). We expect to support
Instabase in future .

.. autoclass:: dgitcore.plugins.repomanager.RepoManagerBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.repomanagers.gitmanager.GitRepoManager
    :members: 
    :undoc-members: update
    :show-inheritance:


Backends
--------

dgit is designed to support multiple backends. Intially local
filesystem and s3 are supported. We plan to support more in future.

.. autoclass:: dgitcore.plugins.backend.BackendBase
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.backends.s3.S3Backend
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.backends.local.LocalBackend
    :members: 
    :undoc-members: 
    :show-inheritance:

Instrumentation
---------------

Various plugins that can be used to instrument any process of
generation of the dataset.

.. autoclass:: dgitcore.plugins.instrumentation.InstrumentationBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.instrumentations.content.ContentInstrumentation
    :members: 
    :undoc-members: update
    :show-inheritance:

.. autoclass:: plugins.instrumentations.platform.PlatformInstrumentation
    :members: 
    :undoc-members: update
    :show-inheritance:

.. autoclass:: plugins.instrumentations.executable.ExecutableInstrumentation
    :members: 
    :undoc-members: update
    :show-inheritance:

Metadata
--------

dgit supports posting metadata to simple API servers to enable search,
lineage computation, and sharing. A minimal posting client is
supported for now.

.. autoclass:: dgitcore.plugins.metadata.MetadataBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.metadata.default.BasicMetadata
    :members: 
    :undoc-members: 
    :show-inheritance:

Validation
--------

.. autoclass:: dgitcore.plugins.validator.ValidatorBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.validators.metadata_validator.MetadataValidator
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.validators.regression_quality.RegressionQualityValidator
    :members: 
    :undoc-members: 
    :show-inheritance:

Generator
---------

.. autoclass:: dgitcore.plugins.generator.GeneratorBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

