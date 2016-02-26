Code
====

Repo Manager
---------------

dgit supports multiple ways to store datasets. It could be git itself,
local filesystem (possibly, with s3 backend). We expect to support
Instabase in future .

.. autoclass:: dgitcore.repomanager.RepoManagerBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.repomanagers.base.git.GitRepoManager
    :members: 
    :undoc-members: update
    :show-inheritance:

.. autoclass:: plugins.repomanagers.base.filesystem.FilesystemRepoManager
    :members: 
    :undoc-members: update
    :show-inheritance:


Backends
--------

dgit is designed to support multiple backends. Intially local
filesystem and s3 are supported. We plan to support more in future.

.. autoclass:: dgitcore.backend.BackendBase
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.backends.base.s3.S3Backend
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.backends.base.local.LocalBackend
    :members: 
    :undoc-members: 
    :show-inheritance:

Instrumentation
---------------

Various plugins that can be used to instrument any process of
generation of the dataset.

.. autoclass:: dgitcore.instrumentation.InstrumentationBase 
    :members: 
    :undoc-members: 
    :show-inheritance:

.. autoclass:: plugins.instrumentations.base.content.ContentInstrumentation
    :members: 
    :undoc-members: update
    :show-inheritance:

.. autoclass:: plugins.instrumentations.base.platform.PlatformInstrumentation
    :members: 
    :undoc-members: update
    :show-inheritance:
