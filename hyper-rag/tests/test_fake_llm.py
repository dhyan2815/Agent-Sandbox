from hyper_rag.llm import build_llm, parse_json
from hyper_rag.llm.cache import CachedLLM
from hyper_rag.prompts import INSUFFICIENT, check_prompt, generate_prompt, grade_prompt
from hyper_rag.types import Chunk

REFUNDS = Chunk(
    "refunds#0", "refunds", "Refunds", "", "A normal refund takes 5 to 7 business days."
)
UPI = Chunk("upi#0", "upi", "UPI", "", "A collect request expires after 5 minutes.")


def test_fake_answers_from_the_matching_passage(settings):
    llm = build_llm(settings)
    reply = llm.complete(
        generate_prompt("How many business days does a refund take?", [UPI, REFUNDS])
    )
    assert reply == "A normal refund takes 5 to 7 business days. [2]"


def test_fake_declines_without_support(settings):
    llm = build_llm(settings)
    assert llm.complete(generate_prompt("How do I bake bread?", [UPI, REFUNDS])) == INSUFFICIENT


def test_fake_grades_and_checks(settings):
    llm = build_llm(settings)
    graded = parse_json(
        llm.complete(grade_prompt("When does a collect request expire?", [UPI, REFUNDS]))
    )
    assert graded == {"relevant": [1]}
    assert parse_json(
        llm.complete(check_prompt("Refunds take 5 to 7 business days. [1]", [REFUNDS]))
    )["grounded"]
    assert not parse_json(llm.complete(check_prompt("Refunds are free forever. [1]", [REFUNDS])))[
        "grounded"
    ]


def test_parse_json_tolerates_wrapping():
    assert parse_json('Sure:\n```json\n{"route": "retrieve"}\n```') == {"route": "retrieve"}
    assert parse_json("no json here") == {}


def test_cache_calls_the_model_once(settings, tmp_path):
    cached = CachedLLM(build_llm(settings), tmp_path / "cache")
    prompt = generate_prompt("How many business days does a refund take?", [REFUNDS])
    assert cached.complete(prompt) == cached.complete(prompt)
    assert (cached.misses, cached.hits) == (1, 1)


def test_answers_are_normalised_to_one_citation_and_character_format():
    from hyper_rag.text import cited_numbers, contains_fact, normalise_answer

    raw = "Settled in\u202fT\u202f+\u202f2 days\u30101\u2020L9-L12\u3011\u30103\u3011, auto\u2011captured."  # noqa: E501
    clean = normalise_answer(raw)
    assert clean == "Settled in T + 2 days[1][3], auto-captured."
    assert cited_numbers(clean) == [1, 3]
    assert contains_fact(clean, "T+2") and not contains_fact(clean, "T+3")
