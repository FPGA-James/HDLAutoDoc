"""The text helpers the extractors share live in one module."""

import extract_block
import extract_cdc
import extract_fsm
import extract_reset
import hdl_text


def test_vhdl_line_comments_are_removed_and_code_stays():
    assert hdl_text.strip_vhdl_comments("a <= b; -- note\nc <= d;") == "a <= b; \nc <= d;"


def test_sv_line_and_block_comments_are_removed():
    text = "assign a = b; // note\n/* block\n   spans lines */ assign c = d;"
    assert hdl_text.strip_sv_comments(text) == "assign a = b; \n assign c = d;"


def test_safe_id_replaces_anything_that_is_not_a_word_character():
    assert hdl_text.safe_id("u_fifo.rd-clk[0]") == "u_fifo_rd_clk_0_"


def test_title_underlines_to_the_text_length_and_leaves_a_blank_line():
    assert hdl_text.title("Clock Domains") == ["Clock Domains", "=============", ""]


def test_the_extractors_use_the_shared_helpers_not_copies():
    for module in (extract_cdc, extract_fsm, extract_reset):
        assert module.strip_vhdl_comments is hdl_text.strip_vhdl_comments
        assert module.strip_sv_comments is hdl_text.strip_sv_comments
    for module in (extract_cdc, extract_reset, extract_block):
        assert module._safe is hdl_text.safe_id
    for module in (extract_cdc, extract_reset):
        assert module._title is hdl_text.title


def test_blanked_comments_keep_every_position_and_newline():
    vhdl = "a <= b; -- note\nc <= d;\n"
    assert hdl_text.blank_vhdl_comments(vhdl) == "a <= b;        \nc <= d;\n"
    sv = "x; // line\n/* block\n   two */ y;\n"
    out = hdl_text.blank_sv_comments(sv)
    assert len(out) == len(sv) and out.count("\n") == sv.count("\n")
    assert "line" not in out and "block" not in out and out.startswith("x;") and out.rstrip().endswith("y;")


def test_blanking_leaves_code_that_merely_resembles_a_comment_start_in_a_string_alone_for_now():
    # Documented limit shared with strip_*: no string-literal awareness.
    assert hdl_text.blank_sv_comments('a = "x"; // c\n') == 'a = "x";     \n'


def test_split_lines_breaks_only_on_newline_and_crlf():
    assert hdl_text.split_lines("a\nb\r\nc\n") == ["a", "b", "c"]
    assert hdl_text.split_lines("a\fb c\x85d\nz") == ["a\fb c\x85d", "z"]
    assert hdl_text.split_lines("") == [] and hdl_text.split_lines("\n") == [""]
    assert hdl_text.split_lines("a\n\nb") == ["a", "", "b"]


def test_split_lines_agrees_with_splitlines_on_ordinary_text():
    for text in ("x", "x\n", "x\ny\n\n", "\n\nx", "a\r\nb\r\n"):
        assert hdl_text.split_lines(text) == text.splitlines(), repr(text)
