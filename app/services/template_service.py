from jinja2 import StrictUndefined, TemplateError, meta
from jinja2.sandbox import SandboxedEnvironment

from app.services.errors import InvalidRequest

env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)


def extract_variables(subject: str, body: str) -> list[str]:
    names: set[str] = set()
    for source in (subject, body):
        try:
            names |= meta.find_undeclared_variables(env.parse(source))
        except TemplateError as exc:
            raise InvalidRequest(f"bad template: {exc}") from exc
    return sorted(names)


def render(subject: str, body: str, context: dict) -> tuple[str, str]:
    try:
        return env.from_string(subject).render(context), env.from_string(body).render(context)
    except TemplateError as exc:
        raise InvalidRequest(f"could not render template: {exc}") from exc
