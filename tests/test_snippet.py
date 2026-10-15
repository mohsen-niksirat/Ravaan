from ravan.core.config import Config, Snippet
from ravan.core.snippet import SnippetEngine


def test_snippet_expansion():
    cfg = Config()
    cfg.snippets.append(Snippet(trigger="@@", replacement="user@example.com"))
    engine = SnippetEngine.from_config(cfg)
    assert engine.expand("@@") == "user@example.com"
    assert engine.expand("@") is None
