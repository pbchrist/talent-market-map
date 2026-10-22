# Done means

A change is done only when all of these are true, and someone other than the builder checked them:

1. `pytest` passes, offline.
2. If the change touches the engine or prompt: one real JD was run through the CLI or app, and the pools are capability-based (not title synonyms) and every generated search string is balanced.
3. If the change touches `docs/`: the app was opened locally and runs the worked example. Merging publishes it.
4. It is one PR, Patrick said yes, and the PR says what was checked and how.
