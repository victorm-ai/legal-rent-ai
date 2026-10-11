"""Legal CAG corpus loading and prompt injection."""

from config.settings import Settings
from llm.chat_provider import build_chat_system_prompt
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID, build_analysis_system_prompt
from rag.cag_corpus import clear_corpus_cache, get_cag_corpus_text, resolve_corpus_path


def test_corpus_file_exists_and_loads() -> None:
    path = resolve_corpus_path()
    assert path.is_file(), f"Missing corpus: {path}"
    text = get_cag_corpus_text()
    assert "CAG Corpus v1" in text
    assert "Article 2023" in text
    assert "Article 683" in text


def test_analysis_system_prompt_includes_corpus() -> None:
    clear_corpus_cache()
    prompt = build_analysis_system_prompt()
    assert "AUTHORIZED LEGAL CORPUS" in prompt
    assert "Article 2041" in prompt
    assert CONTRACT_ANALYSIS_PROMPT_ID == "contract-analysis-v3-cag"


def test_chat_system_prompt_includes_corpus() -> None:
    clear_corpus_cache()
    prompt = build_chat_system_prompt()
    assert "AUTHORIZED LEGAL CORPUS" in prompt
    assert "Mexican lease contracts" in prompt


def test_corpus_disabled() -> None:
    clear_corpus_cache()
    settings = Settings(legal_cag_enabled=False)
    assert get_cag_corpus_text(settings) == ""
    clear_corpus_cache()


if __name__ == "__main__":
    test_corpus_file_exists_and_loads()
    test_analysis_system_prompt_includes_corpus()
    test_chat_system_prompt_includes_corpus()
    test_corpus_disabled()
    print("CAG corpus tests: PASSED")
