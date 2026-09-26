# steplink demo

A small made-up pytest-bdd project to try the plugin on:

```sh
cd demo
nvim garden/features/watering.feature
```

- `garden/features/` holds the scenarios, `garden/steps/` their step definitions.
- `core/steps/` holds a shared step, star-imported by `garden/conftest.py`.
- `prune_roses` in `garden/steps/common/plants.py` is used by no scenario, so
  `:StepLinkOrphans` lists it.

`demo.tape` records the README's GIF with [VHS](https://github.com/charmbracelet/vhs):
run `vhs demo.tape` from this directory.
