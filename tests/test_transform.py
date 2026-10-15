from ravan.core.transform import (
    cycle_case,
    normalize_text,
    to_camel_case,
    to_kebab_case,
    to_snake_case,
    toggle_text_digits,
)


def test_cycle_case_transitions():
    assert cycle_case("hello") == "Hello"
    assert cycle_case("Hello") == "HELLO"
    assert cycle_case("HELLO") == "hello"

    assert cycle_case("hello world") == "Hello World"
    assert cycle_case("Hello World") == "HELLO WORLD"
    assert cycle_case("HELLO WORLD") == "hello world"


def test_cycle_case_edge_cases():
    assert cycle_case("") == ""
    assert cycle_case("12345") == "12345"
    assert cycle_case("---") == "---"


def test_casing_conversions():
    assert to_snake_case("helloWorld") == "hello_world"
    assert to_snake_case("HelloWorld") == "hello_world"
    assert to_snake_case("hello-world") == "hello_world"
    assert to_snake_case("hello world") == "hello_world"

    assert to_camel_case("hello_world") == "helloWorld"
    assert to_camel_case("hello-world") == "helloWorld"

    assert to_kebab_case("hello_world") == "hello-world"
    assert to_kebab_case("helloWorld") == "hello-world"


def test_normalize_text():
    raw = "شركت هاي  بزرگ كشور ."
    res = normalize_text(raw)
    assert "شرکت‌های" in res
    assert "کشور." in res
    assert "ك" not in res
    assert "ي" not in res


def test_toggle_text_digits():
    assert toggle_text_digits("Test 123") == "Test ۱۲۳"
    assert toggle_text_digits("Test ۱۲۳") == "Test 123"
