# fluxit

A CLI tool for bootstrapping Kubernetes application manifests using Jinja templates, designed for compatibility with Flux GitOps workflows losely following the the [onedr0p/cluster-template](https://github.com/onedr0p/cluster-template) setup.

## Description

fluxit helps you generate Kustomization, HelmRelease, and other Kubernetes manifests in the format expected by Flux. It uses Jinja2 templates and YAML validation to ensure your manifests are ready for GitOps automation. The tool is tailored for k8s-at-home and cluster-template repositories, making it easy to add new applications or update existing ones in a way that Flux can automatically reconcile and deploy to your cluster.

-   Interactive CLI for generating K8s manifests
-   Jinja2 templating for consistent, reusable YAML
-   YAML validation and formatting (ruamel-yaml)
-   Diff and confirmation before overwriting files
-   Output is ready to be committed to your GitOps repo for Flux to apply

## Installation

### Using pip/pipx

```sh
pipx install fluxit
fluxit help
```

## References

-   Original cluster template: [onedr0p/cluster-template](https://github.com/onedr0p/cluster-template)
-   Geekifier's k8s-at-home repo: [geekifier/k8s-home-gitops](https://github.com/geekifier/k8s-home-gitops)

## Usage

```sh
pipx install fluxit
fluxit --help
```

## License

See [License.md](./License.md)
