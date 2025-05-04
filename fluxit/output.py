# fluxit/output.py
import logging
import sys
from pathlib import Path

from InquirerPy import inquirer

from . import fluxit


def colorize_diff(diff: str, use_color: bool = True) -> str:
    if not use_color:
        return diff
    RED = "\033[31m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    RESET = "\033[0m"
    result = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("+") and not line.startswith("+++"):
            result.append(f"{GREEN}{line}{RESET}")
        elif line.startswith("-") and not line.startswith("---"):
            result.append(f"{RED}{line}{RESET}")
        elif line.startswith("@"):
            result.append(f"{CYAN}{line}{RESET}")
        else:
            result.append(line)
    return "".join(result)


def confirm_and_save(
    output_file_path: Path,
    formatted_content: str,
    confirm: str,
    logger: logging.Logger,
    color: bool = True,
) -> None:
    """Handles the confirmation and saving logic for a single file.

    Args:
        output_file_path: The path where the file should be saved.
        formatted_content: The validated and formatted content to save.
        confirm: Confirmation mode ('always', 'never', 'if_exists').
        logger: The logger instance.
        color: Whether to use color for diff output.
    """
    proceed_to_save = True
    file_exists = output_file_path.exists()
    existing_content = fluxit.read_file_content(output_file_path) if file_exists else None

    if file_exists and existing_content == formatted_content:
        logger.info(f"Skipped (no changes): {output_file_path}")
        return

    needs_confirmation = confirm == "always" or (confirm == "if_exists" and file_exists)

    if needs_confirmation:
        print("-" * 20)
        print(f"Processing file: {output_file_path}")

        if file_exists and existing_content:
            diff = fluxit.generate_diff(
                existing_content,
                formatted_content,
                output_file_path.name,
            )

            print("Proposed changes (diff):")
            # Print diff directly as it's already a string
            print(colorize_diff(diff, use_color=color), end="")
            print("-" * 20)
        else:
            # Show full content if it's a new file or reading failed
            print("Rendered content:")
            print(formatted_content)
            print("-" * 20)

        if file_exists:
            message = f"File exists. Overwrite {output_file_path} with the changes shown above?"
        else:
            message = f"Save file {output_file_path}?"

        try:
            proceed_to_save = inquirer.confirm(
                message=message,
                default=True,
                confirm_letter="y",
                reject_letter="n",
            ).execute()

            if not proceed_to_save:
                logger.warning(f"Skipped: {output_file_path}")
                return

        # Handle ctrl+C gracefully
        except KeyboardInterrupt:
            logger.warning("\nUser interrupted. Quitting.")
            sys.exit(0)
    # When --confirm=never, it's #YOLO mode
    elif confirm == "never" and file_exists:
        logger.warning(f"Overwriting existing file due to --confirm=never: {output_file_path}")
        proceed_to_save = True

    if proceed_to_save:
        try:
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            fluxit.write_template(output_file_path, formatted_content)
            logger.info(f"Saved: {output_file_path}")
        except Exception as e:
            logger.error(f"Error saving {output_file_path}: {e}")
