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
