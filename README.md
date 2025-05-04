# fluxit

A CLI tool for bootstrapping Kubernetes application manifests using Jinja templates, designed for compatibility with Flux GitOps workflows losely following the the [onedr0p/cluster-template](https://github.com/onedr0p/cluster-template) setup.

![fluxit usage demo](assets/demo.gif)

## Features

- Supports multiple jinja application templates, including directory structure and conditional file creation
- Accepts template values via cli options and interactive UI prompts
- Jinja2 templating for consistent, reusable YAML
- Colorized diff and confirmation before overwriting existing files

### TODO

- Implement support for LoadBalancer and NodeIP Service Types
- Implement non-http ingress support
- Possible integration with [kubesearch.dev](https://kubesearch.dev/) would be cool

## Installation

### Using pip/pipx

TBD

## References

- Original cluster template: [onedr0p/cluster-template](https://github.com/onedr0p/cluster-template)
- Geekifier's k8s-at-home repo: [geekifier/k8s-home-gitops](https://github.com/geekifier/k8s-home-gitops)

## Development

This project's Python dependencies are managed by [uv](https://docs.astral.sh/uv/), and there is also a [mise](https://mise.jdx.dev/) config provided.

If you have `mise` installed, simply run `mise trust` and `mise install`. Otherwise, run `uv sync` directly.

### Executing the program for testing

`uv run fluxit`

Optionally, you an specify the working directory that you want to execute the tool against:

`uv run --directory ~/somedir/my-kube-cluster-repo fluxit`

## License

See [LICENSE](./LICENSE)
