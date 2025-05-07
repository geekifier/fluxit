import functools
import logging
import re
from collections.abc import Sequence
from logging import Logger
from typing import Any, Callable, Literal, ParamSpec, TypeVar, cast, final, override

import click
from InquirerPy import inquirer
from InquirerPy.validator import ValidationError, Validator

from .fluxit import get_ns

logger: Logger = logging.getLogger(__name__)


@final
class PromptMeta:
    """Metadata for configuring :class:`InquirerOption`prompts in custom Click options.

    :param prompt_type: The type of InquirerPy prompt to display (e.g., 'text', 'fuzzy', 'select').
    :param message: The message to display to the user when prompting.
    :param default: (Any, optional)
             The default value to use if the user provides no input.
             If not provided, it will be derived from the Click option's default value if available.
    :param choices: A callable that returns a sequence of choices. Note: if :class:`click.Choice`
                    is used as the type, choices will be derived from it instead.
    :param validate: Validator, optional
        A validation function or object to validate user input.
    :param prompt_with_default: Whether to show the default value in the prompt. Defaults to False.
    :param prompt_when_missing: Whether to prompt only when the option is missing. Defaults to True.
    **kwargs: Additional keyword arguments forwarded to Click.
    """

    def __init__(
        self,
        *,
        prompt_type: str = "text",
        message: str,
        default: str | int | Callable[..., Any] | None = None,
        choices: Callable[[click.Context], Sequence[Any]] | Sequence[Any] | None = None,
        validate: Validator | None = None,
        # Whether to prompt the user even if a default is provided, but no cli argument is given
        prompt_with_default: bool = False,
        # Whether to prompt the user when both the default and the CLI arg are missing
        prompt_when_missing: bool = True,
    ):
        self.prompt_type = prompt_type
        self.message = message
        self.default = default
        self.choices = choices
        self.validate = validate
        self.prompt_with_default = prompt_with_default
        self.prompt_when_missing = prompt_when_missing


class InquirerOption(click.Option):
    def __init__(self, *args: Any, prompt_meta: PromptMeta, **kwargs: Any):
        self.prompt_meta: PromptMeta = prompt_meta

        # set default on prompt_meta from click.Option if not already set
        if self.prompt_meta.default is None and "default" in kwargs:
            self.prompt_meta.default = kwargs["default"]

        # only tell Click to _consider_ prompting if we really want to
        if self.prompt_meta.prompt_with_default or (
            self.prompt_meta.default is None
            and self.prompt_meta.prompt_when_missing
            # don't prompt if callback is provided, let it handle the logic
            and not kwargs.get("callback")
        ):
            kwargs.setdefault("prompt", True)
        super().__init__(*args, **kwargs)

    @override
    def prompt_for_value(self, ctx: click.Context) -> Any:
        param_name: str = cast(str, self.name)
        existing = ctx.params.get(param_name)

        # 1) CLI override always wins
        if existing is not None:
            return existing

        # 2) if a default is set and we’re not prompting with default, return it;
        # otherwise (no default or prompt_with_default=True) continue to prompt
        if self.prompt_meta.default is not None and not self.prompt_meta.prompt_with_default:
            return self.prompt_meta.default

        # 3) Alternate Syntax: call the inquirer prompt class directly
        prompt_fn = getattr(inquirer, self.prompt_meta.prompt_type)
        prompt_kwargs: dict[str, Any] = {"message": self.prompt_meta.message}

        if self.prompt_meta.prompt_type == "fuzzy":
            prompt_kwargs["info"] = False

        # Derive default: static or ctx-aware callable
        default = self.prompt_meta.default
        if callable(default):
            default = default(ctx)

        if default is not None:
            # InqiuirerPy's prompt expects default to be a string despite the type hint
            # This won't affect the final value type from Click
            prompt_kwargs["default"] = str(default)

        # Derive choices: allow static list, callable, or fall back to click.Choice
        choices = None
        if self.prompt_meta.choices is not None:
            fn = self.prompt_meta.choices
            if callable(fn):
                choices = fn(ctx)
            else:
                choices = fn
        elif isinstance(self.type, click.Choice):
            choices = list(self.type.choices)
        if choices is not None:
            prompt_kwargs["choices"] = choices

        if self.prompt_meta.validate:
            prompt_kwargs["validate"] = self.prompt_meta.validate

        # Looping until a valid answer is provided - accomodates custom validators
        while True:
            answer = prompt_fn(**prompt_kwargs).execute()
            try:
                return self.type.convert(answer, self, ctx)
            except click.BadParameter as e:
                click.echo(e.format_message(), err=True)
                continue


class AppNameParamType(click.ParamType):
    name: str = "app-name"

    @override
    def convert(self, value, param, ctx):
        v = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]+", v):
            self.fail(
                "Only letters, numbers, dash and underscore are allowed.",
                param,
                ctx,
            )
        return v


PARAM_T_APP_NAME = AppNameParamType()


F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")


def fancy_option(
    *param_decls,
    prompt_type: Literal["text", "fuzzy", "filepath", "select", "confirm"] = "text",
    message: str,
    default: Any = None,
    choices: Callable[[click.Context], Sequence[Any]] | None = None,
    validate: Validator | None = None,
    prompt_with_default: bool = False,
    prompt_when_missing: bool = True,
    **kwargs,
) -> Callable[[F], F]:
    """
    Metadata for configuring InquirerPy prompts in custom Click options.

    :param prompt_type: The type of InquirerPy prompt to display (e.g., 'text', 'fuzzy', 'select').
    :param message: The message to display to the user when prompting.
    :param default: (Any, optional)
             The default value to use if the user provides no input.
             If not provided, it will be derived from the Click option's default value if available.
    :param choices: A callable that returns a sequence of choices. Note: if :class:`click.Choice`
                    is used as the type, choices will be derived from it instead.
    :param validate: Validator, optional
        A validation function or object to validate user input.
    :param prompt_with_default: Whether to show the default value in the prompt. Defaults to False.
    :param prompt_when_missing: Whether to prompt only when the option is missing. Defaults to True.
    **kwargs: Additional keyword arguments forwarded to Click.
    """

    def decorator(f: F) -> F:
        meta: PromptMeta = PromptMeta(
            prompt_type=prompt_type,
            message=message,
            default=default,
            choices=choices,
            validate=validate,
            prompt_with_default=prompt_with_default,
            prompt_when_missing=prompt_when_missing,
        )
        wrapped = click.option(
            *param_decls,
            cls=InquirerOption,
            prompt_meta=meta,
            default=default,
            **kwargs,
        )(f)
        return cast(F, functools.wraps(f)(wrapped))

    return decorator


def get_param(ctx: click.Context, name: str, default=None):
    """Get a param from ctx, falling back to default if needed."""
    value = ctx.params.get(name)
    if value is None:
        # Try to get from defaults if provided
        value = default
    return value


def get_ns_choices(ctx: click.Context) -> list[str]:
    """Get a list of namespaces from the k8s_app_dir, robustly and idiomatically."""
    k8s_app_dir = ctx.params.get("k8s_app_dir")
    if not k8s_app_dir:
        raise click.UsageError("--k8s-app-dir must be set before selecting a namespace.")
    try:
        ns_dict = get_ns(k8s_app_dir)
        choices = sorted(ns_dict.keys())
        if not choices:
            raise click.UsageError(f"No namespaces found in {k8s_app_dir}.")
        return choices
    except Exception as e:
        raise click.UsageError(f"Error fetching namespaces: {e}")


def param_ingress_host_callback(ctx: click.Context, param: click.ParamType, value: str) -> str:
    """Click callback to require a value if option ingress != 'disabled'.
    It also sets the default value for the InquirerPy prompt based on the app_name option.

    :return: `str` value of user's prompt input, or the default from app_name option,
    """
    ingress = ctx.params.get("ingress")
    if ingress == "disabled" or value:
        return value
    app_name = ctx.params.get("app_name", "")
    default_host = app_name.replace("_", "-")
    value = inquirer.text(
        message="App Ingress Hostname:",
        default=default_host,  # Always pass the computed default
    ).execute()
    if not value:
        raise click.UsageError(
            f"--{param.name.replace('_', '-')} is required when --ingress is not 'disabled'"
        )
    return value


class IngressHostValidator(Validator):
    @override
    def validate(self, document) -> None:
        value: str = document.text
        if not re.fullmatch(r"[a-z0-9-]+", value):
            raise ValidationError(
                message="Ingress host must only contain lowercase letters, numbers, and dashes."
            )
