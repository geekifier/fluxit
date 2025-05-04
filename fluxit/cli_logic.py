import logging
import re

import click
from InquirerPy import inquirer

logger = logging.getLogger(__name__)


class InquirerChoice(click.Option):
    """A click.Option subclass that uses InquirerPy for interactive choices."""

    def __init__(self, *args, choices_func=None, choices=None, fuzzy=False, **kwargs):
        if choices_func and choices:
            raise ValueError("Cannot provide both 'choices' and 'choices_func'.")
        self._choices_func = choices_func
        self._static_choices = choices
        self._fuzzy = fuzzy
        self._default = kwargs.get("default", None)
        kwargs.pop("choices", None)
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.name not in opts or opts[self.name] is None:
            choices = None
            if self._choices_func:
                try:
                    choices = self._choices_func(ctx)
                except Exception as e:
                    logger.error(f"Failed to retrieve dynamic choices for '{self.name}': {e}")
                    raise click.exceptions.Abort(f"Error getting choices for {self.name}.")
            elif self._static_choices is not None:
                choices = self._static_choices
            if not choices:
                logger.error(f"No choices available for '{self.name}'.")
                raise click.exceptions.Abort(f"No choices available for {self.name}.")
            # If default is set and present in choices, pre-select it
            default = self._default if self._default in choices else None
            prompt_msg = self.help or f"Choose {self.name.replace('_', ' ')}:"
            if self._fuzzy:
                selected = inquirer.fuzzy(
                    message=prompt_msg, choices=choices, info=False, default=default
                ).execute()
            else:
                selected = inquirer.select(
                    message=prompt_msg, choices=choices, default=default
                ).execute()
            if not selected:
                raise click.exceptions.Abort(f"Selection aborted for {self.name}.")
            opts[self.name] = selected
        return super().handle_parse_result(ctx, opts, args)


class InquirerPromptOption(click.Option):
    """A click.Option subclass that uses InquirerPy for text/number prompts."""

    def __init__(self, *args, prompt_message=None, always_prompt=False, **kwargs):
        self._prompt_message = prompt_message
        self._always_prompt = always_prompt
        self._default = kwargs.get("default", None)
        kwargs.pop("prompt", None)
        kwargs.pop("prompt_required", None)
        super().__init__(*args, **kwargs)

    def get_default(self, ctx, *args, **kwargs):
        if callable(self._default):
            return self._default(ctx)
        return self._default

    def handle_parse_result(self, ctx, opts, args):
        click_type = getattr(self, "type", None)

        if self.name not in opts or opts[self.name] is None:
            default = self.get_default(ctx)
            # Check for none to avoid interfering with False
            if default is not None:
                opts[self.name] = default
                if not self._always_prompt:
                    return super().handle_parse_result(ctx, opts, args)
            prompt_msg = (
                self._prompt_message or self.help or f"Enter {self.name.replace('_', ' ')}:"
            )
            if isinstance(click_type, click.types.IntParamType):
                value = inquirer.number(message=prompt_msg, default=default).execute()
            elif isinstance(click_type, click.types.FloatParamType):
                value = inquirer.text(message=prompt_msg, default=default).execute()
                try:
                    value = float(value)
                except Exception:
                    raise click.BadParameter(f"{self.name} must be a float.")
            else:
                value = inquirer.text(message=prompt_msg, default=default).execute()
            if value is None or value == "":
                raise click.exceptions.Abort(f"Prompt aborted for {self.name}.")
            if isinstance(click_type, click.types.IntParamType):
                try:
                    value = int(value)
                except Exception:
                    raise click.BadParameter(f"{self.name} must be an integer.")
            opts[self.name] = value
        return super().handle_parse_result(ctx, opts, args)


class BoolInquirerPromptOption(click.Option):
    """A click.Option subclass that uses InquirerPy for boolean (Y/n) prompts."""

    def __init__(self, *args, prompt_message=None, **kwargs):
        self._prompt_message = prompt_message
        self._default = kwargs.get("default", False)
        kwargs.pop("prompt", None)
        kwargs.pop("prompt_required", None)
        super().__init__(*args, **kwargs)

    def get_default(self, ctx, *args, **kwargs):
        if callable(self._default):
            return self._default(ctx)
        return self._default

    def handle_parse_result(self, ctx, opts, args):
        if self.name not in opts or opts[self.name] is None:
            default = self.get_default(ctx)
            prompt_msg = (
                self._prompt_message or self.help or f"Include {self.name.replace('_', ' ')}?"
            )
            value = inquirer.confirm(message=prompt_msg, default=default).execute()
            if value is None:
                raise click.exceptions.Abort(f"Prompt aborted for {self.name}.")
            opts[self.name] = value
        return super().handle_parse_result(ctx, opts, args)


def require_if_ingress_enabled(ctx, param, value):
    """Click callback to require a value if ingress is not 'disabled'."""
    ingress = ctx.params.get("ingress")
    if ingress == "disabled" or value:
        return value
    app_name = ctx.params.get("app_name", "")
    default_host = app_name.replace("_", "-") if app_name else "unknown-app-ingress"
    value = inquirer.text(
        message="App Ingress Hostname:",
        default=default_host,  # Always pass the computed default
    ).execute()
    if not value:
        raise click.UsageError(
            f"--{param.name.replace('_', '-')} is required when --ingress is not 'disabled'"
        )
    return value


def validate_app_name(ctx, param, value):
    """Validate that the application name contains only allowed characters."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise click.BadParameter("Only letters, numbers, dashes, and underscores are allowed.")
    return value
