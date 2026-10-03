# Runtime design

The scheduler is dependency-driven rather than list-driven.

A node becomes runnable only when all dependencies have completed successfully. Independent branches can run concurrently up to the workflow concurrency limit. When a node permanently fails, descendants are skipped while unrelated branches continue.

Each node attempt is journalled separately. Retries therefore remain visible instead of overwriting the first failure.

The runtime does not infer hidden dependencies from template strings. Dependencies must be declared explicitly in `depends_on`, which keeps the graph inspectable.
