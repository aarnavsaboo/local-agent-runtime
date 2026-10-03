# Workflow shapes

The runtime is intentionally small, but a few useful application patterns fit naturally.

## Retrieval then generation

```text
retrieve -> prompt -> model
```

## Parallel retrieval branches

```text
lexical ----+
            +-> join -> model
other ------+
```

## Parallel local model comparison

```text
prompt -> small-model ---+
       -> larger-model --+-> join
```

## Preprocessing and summarization

```text
template -> model -> select
```

A workflow should stay explicit enough that the graph itself explains the application pipeline.
