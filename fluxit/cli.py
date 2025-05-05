import sys
from pathlib import Path

import click

from . import fluxit
from ._defaults import defaults
from .cli_logic import (
    PARAM_T_APP_NAME,
    IngressHostValidator,
    InquirerOption,
    PromptMeta,
    fancy_option,
    get_ns_choices,
    param_ingress_host_callback,
)
from .output import confirm_and_save


@click.command()
@click.option(
    "--k8s-app-dir",
    cls=InquirerOption,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    prompt_meta=PromptMeta(
        prompt_type="filepath",
        message="Path to the Kubernetes apps directory:",
    ),
    help="Path to the Kubernetes apps directory.",
    show_default=True,
    is_eager=True,
    default=defaults.k8s_app_dir,
)
@click.option(
    "--template-dir",
    cls=InquirerOption,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    prompt_meta=PromptMeta(
        prompt_type="filepath",
        message="Path to the base directory containing templates:",
    ),
    help="Path to the base directory containing templates.",
    show_default=True,
    default=defaults.template_dir,
)
@click.option(
    "--template",
    cls=InquirerOption,
    prompt_meta=PromptMeta(
        prompt_type="filepath",
        message="Name of the template within the template directory:",
    ),
    type=str,
    help="Name of the template subdirectory within the template directory.",
    show_default=True,
    default=defaults.template,
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=defaults.log_level,
    help="Logging verbosity.",
)
@click.option(
    "--confirm",
    #   prompt_message="When to ask for confirmation before saving/overwriting files:",
    type=click.Choice(["always", "never", "if_exists"], case_sensitive=False),
    default=defaults.confirm,
    help="When to ask for confirmation before saving/overwriting files.",
    show_default=True,
)
@click.option(
    "--color/--no-color",
    default=defaults.color,
    show_default=True,
    help="Enable or disable colorized diff output in confirmation prompts.",
)
@fancy_option(
    "--ns",
    prompt_type="fuzzy",
    message="Target Namespace:",
    choices=get_ns_choices,
    help="Name of the namespace where deployment scaffold will be created.",
)
@fancy_option(
    "--app-name",
    prompt_type="text",
    message="Application name:",
    type=PARAM_T_APP_NAME,
    help="Name of the application.",
)
@fancy_option(
    "--ingress",
    type=click.Choice(["disabled", "http"]),
    prompt_type="select",
    message="Ingress type:",
    help="Ingress type to be used by the app.",
)
@fancy_option(
    "--ingress-host",
    # default=ingress_host_default,
    validate=IngressHostValidator(),
    callback=param_ingress_host_callback,
    # prompt_with_default=True,
    # required_if=ingress_host_required,
    prompt_type="text",
    message="Ingress host:",
    help="Hostname for the ingress resources.",
)
@click.option(
    "--service-port",
    #   prompt_message="Service port number:",
    type=int,
    default=defaults.service_port,
    #   always_prompt=True,
    help="Port number for the service."
    "Currently assumes TCP protocol and identical source and target ports.",
    show_default=True,
)
@click.option(
    "--image-repo",
    #   prompt_message="Container Image repository:",
    type=str,
    help="Container Image repository",
)
@click.option(
    "--image-tag",
    #    prompt_message="Container Image Tag:",
    type=str,
    help="Container Image Tag",
)
@click.option(
    "--deployment-strategy",
    cls=InquirerOption,
    prompt_meta=PromptMeta(
        prompt_type="select",
        message="Pod Deployment strategy:",
        prompt_with_default=True,
    ),
    type=click.Choice(["Recreate", "RollingUpdate"]),
    default=defaults.deployment_strategy,
    show_default=True,
    help="Pod Deployment strategy.",
)
@click.option(
    "--replicas",
    #    prompt_message="Number of pod replicas:",
    type=int,
    default=defaults.replicas,
    #    always_prompt=True,
    show_default=True,
    help="Number of replicas for the deployment.",
)
@click.option(
    "--include-cm/--no-include-cm",
    #    prompt_message="Include a ConfigMap template?",
    is_flag=True,
    help="Whether to include a ConfigMap template.",
)
@click.option(
    "--include-secret/--no-include-secret",
    #    prompt_message="Include a Secret template?",
    is_flag=True,
    help="Whether to include a Secret template.",
)
def main(
    k8s_app_dir: Path,
    template_dir: Path,
    template: str,
    ns: str,
    app_name: str,
    log_level: str,
    ingress: str,
    service_port: int,
    replicas: int,
    ingress_host: str,
    image_repo: str,
    image_tag: str,
    confirm: str = "if_exists",
    deployment_strategy: str = "RollingUpdate",
    color: bool = True,
    include_cm: bool = False,
    include_secret: bool = False,
) -> None:
    """Generates Kubernetes application manifests using templates."""
    logger = fluxit.init_logging(log_level)
    logger.info("Starting 🧪 fluxit")

    template_full_path = template_dir / template
    logger.info(f"Using template path: {template_full_path}")
    if not template_full_path.exists() or not template_full_path.is_dir():
        logger.error(f"Template path does not exist or is not a directory: {template_full_path}")
        sys.exit(1)

    template_context = {
        "app_name": app_name,
        "namespace": ns,
        "ingress_type": ingress,
        "ingress_host": ingress_host,
        "image_repo": image_repo,
        "image_tag": image_tag,
        "deployment_strategy": deployment_strategy,
        "replicas": replicas,
        "include_cm": include_cm,
        "include_secret": include_secret,
        "service_port": service_port,
    }

    try:
        rendered_templates = fluxit.render_templates(
            str(template_full_path),
            template_context,
        )
    except Exception as e:
        logger.error(f"Failed during template rendering: {e}")
        sys.exit(1)
    # Apparenty this is an accepted Python practice, since these are Path objects,
    # it's OK to just join them like this.
    output_base_dir = k8s_app_dir / ns / app_name
    logger.info(f"Target directory: {output_base_dir}")

    for relative_path_j2, raw_content in rendered_templates.items():
        # Preserve subdirectory structure and strip only the .j2 extension
        relative_output_path = Path(relative_path_j2).with_suffix("")
        output_file_path = output_base_dir / relative_output_path

        try:
            is_valid, formatted_content = fluxit.validate_and_format_yaml(raw_content)
            if not is_valid:
                logger.warning(f"Skipping invalid YAML file: {relative_path_j2}")
                continue

            confirm_and_save(output_file_path, formatted_content, confirm, logger, color=color)

        except Exception as e:
            logger.error(f"Error processing file {relative_path_j2}: {e}")
            continue

    logger.info("Fluxit finished ✨.")


if __name__ == "__main__":
    main()
