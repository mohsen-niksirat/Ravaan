from ravan.core.calc import calculate, extract_math_expression, safe_eval


def test_safe_eval_basic():
    assert safe_eval("2 + 3") == 5
    assert safe_eval("10 - 4") == 6
    assert safe_eval("6 * 7") == 42
    assert safe_eval("20 / 4") == 5
    assert safe_eval("20 / 8") == 2.5
    assert safe_eval("7 // 2") == 3
    assert safe_eval("7 % 3") == 1
    assert safe_eval("2 ^ 3") == 8
    assert safe_eval("2 ** 4") == 16


def test_safe_eval_parentheses_and_precedence():
    assert safe_eval("(10 + 20) * 3") == 90
    assert safe_eval("10 + 20 * 3") == 70
    assert safe_eval("-5 + 15") == 10
    assert safe_eval("-(5 + 15)") == -20


def test_safe_eval_safety_and_errors():
    assert safe_eval("10 / 0") is None
    assert safe_eval("__import__('os')") is None
    assert safe_eval("eval('2+2')") is None
    assert safe_eval("open('secret.txt')") is None
    assert safe_eval("2 ** 1000") is None
    assert safe_eval("abc + def") is None


def test_calculate_formatting():
    assert calculate("1200*1.09") == "1308"
    assert calculate("(50+30)*2") == "160"
    assert calculate("10 / 4") == "2.5"
    assert calculate("1/3") == "0.333333"


def test_calculate_persian_digits():
    assert calculate("۱۲۰۰*۳") == "۳۶۰۰"
    assert calculate("۱۰ / ۴") == "۲.۵"
    assert calculate("(۵۰+۳۰)*۲") == "۱۶۰"


def test_extract_math_expression():
    assert extract_math_expression("hello 10+20*3") == "10+20*3"
    assert extract_math_expression("price: (500+250)/2") == "(500+250)/2"
    assert extract_math_expression("قیمت: ۱۲۰۰*۳") == "۱۲۰۰*۳"
    assert extract_math_expression("plain text") is None
    assert extract_math_expression("x = 5") is None
    assert extract_math_expression("(unbalanced + 5") is None
    assert extract_math_expression("") is None
