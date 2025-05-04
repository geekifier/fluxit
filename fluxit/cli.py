import sys
from pathlib import Path

import click

from . import fluxit
from ._defaults import defaults
from .cli_logic import (
    BoolInquirerPromptOption,
    InquirerChoice,
    InquirerPromptOption,
    require_if_ingress_enabled,
    validate_app_name,
)
from .output import confirm_and_save


@click.command()
@click.option(
    "--k8s-app-dir",
    cls=InquirerPromptOption,
    prompt_message="Path to the Kubernetes apps directory:",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=defaults.k8s_app_dir,
    help="Path to the Kubernetes apps directory.",
    show_default=True,
)
@click.option(
    "--template-dir",
    cls=InquirerPromptOption,
    prompt_message="Path to the base directory containing templates:",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=defaults.template_dir,
    help="Path to the base directory containing templates.",
    show_default=True,
)
@click.option(
    "--template",
    cls=InquirerPromptOption,
    prompt_message="Name of the template subdirectory within the template directory:",
    type=str,
    default=defaults.template,
    help="Name of the template subdirectory within the template directory.",
    show_default=True,
)
@click.option(
    "--ns",
    cls=InquirerChoice,
    choices_func=lambda ctx: sorted(fluxit.get_ns(ctx.params["k8s_app_dir"]).keys()),
    fuzzy=True,
    help="Name of the namespace where deployment scaffold will be created.",
)
@click.option(
    "--app-name",
    cls=InquirerPromptOption,
    prompt_message="Application name:",
    type=str,
    callback=validate_app_name,
    help="Name of the application.",
)
@click.option(
    "--ingress",
    cls=InquirerChoice,
    choices=["disabled", "http"],
    help="Ingress type to be used by the app.",
)
@click.option(
    "--ingress-host",
    type=str,
    callback=require_if_ingress_enabled,
    help="Hostname for the ingress resources.",
)
@click.option(
    "--image-repo",
    cls=InquirerPromptOption,
    prompt_message="Container Image repository:",
    type=str,
    help="Container Image repository",
)
@click.option(
    "--image-tag",
    cls=InquirerPromptOption,
    prompt_message="Container Image Tag:",
    type=str,
    help="Container Image Tag",
)
@click.option(
    "--log-level",
    cls=InquirerPromptOption,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=defaults.log_level,
    help="Logging verbosity.",
)
@click.option(
    "--confirm",
    cls=InquirerPromptOption,
    prompt_message="When to ask for confirmation before saving/overwriting files:",
    type=click.Choice(["always", "never", "if_exists"], case_sensitive=False),
    default=defaults.confirm,
    help="When to ask for confirmation before saving/overwriting files.",
    show_default=True,
)
@click.option(
    "--deployment-strategy",
    cls=InquirerChoice,
    choices=["RollingUpdate", "Recreate"],
    prompt="Pod Deployment strategy:",
    default=defaults.deployment_strategy,
    show_default=True,
    help="Pod Deployment strategy.",
)
@click.option(
    "--replicas",
    cls=InquirerPromptOption,
    prompt_message="Number of pod replicas:",
    value_type=int,
    default=defaults.replicas,
    show_default=True,
    help="Number of replicas for the deployment.",
)
@click.option(
    "--color/--no-color",
    default=defaults.color,
    show_default=True,
    help="Enable or disable colorized diff output in confirmation prompts.",
)
@click.option(
    "--include-cm/--no-include-cm",
    cls=BoolInquirerPromptOption,
    prompt_message="Include a ConfigMap template?",
    is_flag=True,
    help="Whether to include a ConfigMap template.",
)
@click.option(
    "--include-secret/--no-include-secret",
    cls=BoolInquirerPromptOption,
    prompt_message="Include a Secret template?",
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
    ingress_host: str = None,
    image_repo: str = None,
    image_tag: str = None,
    confirm: str = "if_exists",
    deployment_strategy: str = "RollingUpdate",
    replicas: int = 1,
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
