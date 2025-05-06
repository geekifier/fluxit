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
- Add newly created kustomizations to the namespace manifests

## Installation

### Using pip/pipx

TBD

## Usage

**WARNING: this is pre-release software. Use at your own risk.**

By default, the program will look for templates inside of `.templates/fluxit`, relative to the current workdir.

Generally, you would execute `fluxit` in the root of your cluster's gitops repo. By default, namespace configurations are expected in the `./kubernetes/apps` directory.

See `fluxit --help` for the list of options you can use to override the defaults.

```
Usage: fluxit [OPTIONS]

  fluxit CLI tool for rendering Kubernetes templates.

Options:
  --k8s-app-dir DIRECTORY         Path to the Kubernetes apps directory.
                                  [default: kubernetes/apps]
  --template-dir DIRECTORY        Path to the base directory containing
                                  templates.  [default: .templates/fluxit]
  --template TEXT                 Name of the template subdirectory within the
                                  template directory.  [default: app_template]
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  Logging verbosity.
  --confirm [always|never|if_exists]
                                  When to ask for confirmation before
                                  saving/overwriting files: `always`: Always
                                  ask for confirmation, `never`: Never ask for
                                  confirmation, `if_exists`: Ask for
                                  confirmation only if the file already
                                  exists.  [default: if_exists]
  --color / --no-color            Enable or disable colorized diff output in
                                  confirmation prompts. Currently does not
                                  apply to other output.  [default: color]
  -h, --help                      Show this message and exit.
  -v, --version                   Show the version and exit.
  --ns TEXT                       Name of the namespace where deployment
                                  scaffold will be created.
  --app-name APP-NAME             Name of the application.
  --ingress [disabled|http]       Ingress type to be used by the app.
  --ingress-host TEXT             Hostname for the ingress resources.
  --service-port INTEGER          Port number for the service.Currently
                                  assumes TCP protocol and identical source
                                  and target ports.  [default: 80]
  --image-repo TEXT               Container Image repository
  --image-tag TEXT                Container Image Tag
  --deployment-strategy [Recreate|RollingUpdate]
                                  Pod Deployment strategy.  [default:
                                  Recreate]
  --replicas INTEGER              Number of replicas for the deployment.
                                  [default: 1]
  --include-cm / --no-include-cm  Whether to include a ConfigMap template.
  --include-secret / --no-include-secret
                                  Whether to include a Secret template.
```

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
