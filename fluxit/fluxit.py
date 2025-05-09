"""
fluxit.py: Core logic for rendering, validating, and writing Kubernetes YAML manifests
using Jinja templates.
"""

import difflib
import logging
import pathlib
from io import StringIO
from pathlib import Path

import jinja2 as j2
from ruamel.yaml import YAML, YAMLObject

from ._defaults import defaults

logger = logging.getLogger(__name__)


def init_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Initialize logging for the application.

    Args:
        log_level (str): Logging level as a string (e.g., "INFO", "DEBUG").

    Returns:
        logging.Logger: Configured logger instance.
    """
    logging.basicConfig(
        format=defaults.log_format,
        level=logging.INFO,
    )
    logging.getLogger("fluxit").setLevel(getattr(logging, log_level.upper(), logging.INFO))

    logger = logging.getLogger(__name__)

    return logger


def get_ns(path: str) -> dict[str, YAMLObject]:
    """
    Discover and parse namespaces from a directory.

    Args:
        path (str): Path to the directory containing namespace subdirectories.

    Returns:
        dict[str, YAMLObject]: Dictionary mapping namespace names to their parsed data:
        {ns_name: parsed_data}
    """
    if pathlib.Path(path).is_dir():
        namespaces = {}
        for item in pathlib.Path(path).iterdir():
            if item.is_dir() and (item / defaults.ns_kustomize_file).exists():
                ns_ks_file: Path = item.joinpath(defaults.ns_kustomize_file)
                ns_data = parse_namespace(file=ns_ks_file)
                if ns_data:
                    ns_name = ns_data.get("namespace")
                else:
                    logger.warning(f"Parsing {ns_ks_file} did not return anything")
                    continue
                if ns_name:
                    namespaces[ns_name] = ns_data
                    logger.debug(f"Found namespace: {ns_name} in {ns_ks_file}")
                else:
                    logger.warning(f"No namespace found in {ns_ks_file}")
        return namespaces
    else:
        logger.error(f"Invalid path: {path}")
        return {}


def parse_namespace(file: pathlib.Path) -> YAMLObject | None:
    """
    Parse a namespace YAML file.

    Args:
        file (pathlib.Path): Path to the namespace YAML file.

    Returns:
        YAMLObject | None: Parsed YAML data as a dictionary, or None if parsing fails.
    """
    yaml = YAML(typ="safe")
    try:
        with open(file, "r") as f:
            data = yaml.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to parse file {file}: {e}")
        return None


def render_templates(templates_path: str, context: dict) -> dict[str, str]:
    """
    Recursively render Jinja templates in the provided path using the context dictionary.

    Args:
        templates_path (str): The path to the directory containing templates.
        context (dict): A dictionary containing context variables for rendering.

    Returns:
        dict[str, str]: A dictionary containing `{path: content}` of rendered Jinja templates.
    """
    env = j2.Environment(loader=j2.FileSystemLoader(templates_path), undefined=j2.StrictUndefined)
    rendered_templates = {}

    for path in pathlib.Path(templates_path).rglob("*.j2"):
        if path.is_file():
            relative_path = None
            try:
                relative_path = str(path.relative_to(templates_path))
                template = env.get_template(relative_path)
                rendered_content = template.render(context)
                # Skip files containing only the special keyword: '__SKIP__'
                if rendered_content.strip() == "__SKIP__":
                    continue
                rendered_templates[relative_path] = rendered_content
            except j2.UndefinedError as e:
                logger.error(f"{relative_path} -> No value provided for template var: {e}.")
                exit(1)
            except Exception as e:
                logger.error(f"Failed to render template {path}: {e}")
                exit(1)
    return rendered_templates


# TODO: fix the return types of this function, it's super confusing
def validate_and_format_yaml(content: str) -> tuple[list[object] | None, str]:
    """
    Validate and format YAML content.

    Tries to parse the input string as YAML (potentially multi-document).
    If successful, returns the parsed data and a consistently formatted YAML string.
    If parsing fails, returns None and the original content.

    Args:
        content (str): The string content to validate and format.

    Returns:
        tuple[list[object] | None, str]: List of rendered YAML documents, rendered content when
        parsing resulted in changes, and original content when no change. #fixme

    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    try:
        # Use load_all to handle multi-document YAML files
        parsed_data = list(yaml.load_all(content))
        with StringIO() as string_stream:
            yaml.dump_all(parsed_data, string_stream)
            formatted_content = string_stream.getvalue()
        # Check if any actual data was parsed (ignore empty documents like '---')
        if not any(doc for doc in parsed_data if doc is not None):
            logger.debug("YAML content resulted in empty documents after parsing.")
            # Return original content if parsing resulted in nothing meaningful
            # This handles cases like templates rendering only comments or whitespace
            return None, content
        return parsed_data, formatted_content
    except Exception as e:
        logger.warning(f"Could not parse content as YAML, proceeding with raw content. Error: {e}")
        return None, content


def write_template(output_path: pathlib.Path, content: str) -> None:
    """
    Write content to the specified file path.

    Args:
        output_path (pathlib.Path): The full path to the output file.
        content (str): The content to write to the file.
    """
    try:
        with open(output_path, "w") as f:
            f.write(content)
    except IOError as e:
        logger.error(f"Failed to write file {output_path}: {e}")


def read_file_content(file_path: pathlib.Path) -> str | None:
    """
    Safely reads the content of a file.

    Args:
        file_path (pathlib.Path): The path to the file.

    Returns:
        str | None: The file content as a string, or None if the file doesn't exist
        or cannot be read.
    """
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r") as f:
            return f.read()
    except IOError as e:
        logger.warning(f"Could not read file {file_path}: {e}")
        return None


def generate_diff(old_content: str, new_content: str, file_name: str) -> str:
    """
    Generates a unified diff string between old and new content.

    Args:
        old_content (str): The original content (e.g., existing file).
        new_content (str): The new content (e.g., template output).
        file_name (str): The name to use for the file in the diff header.

    Returns:
        str: A string containing the unified diff.
    """
    diff_lines = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{file_name}",
        tofile=f"b/{file_name}",
    )
    return "".join(diff_lines)
