from pathlib import Path

_DIR = Path(__file__).parent / "templates"


def render(name: str, **kwargs) -> str:
    """Load a template and substitute {{variable}} placeholders."""
    text = (_DIR / name).read_text(encoding="utf-8")
    for key, value in kwargs.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text
