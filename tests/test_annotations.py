"""Tests for corpus annotations with Sparv."""

import pathlib

import pytest

import utils
from sparv.core import paths


@pytest.mark.swe
def test_standard_swe(tmp_path):
    """Run corpus standard-swe and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/standard-swe")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=[
        "csv_export:csv",
        "cwb:info",
        "cwb:vrt",
        "cwb:vrt_scrambled",
        "korp:relations_sql",
        "korp:timespan_sql",
        "stats_export:freq_list",
        "xml_export:pretty",
        "xml_export:preserved_format",
        "xml_export:scrambled",
    ])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.freeling
@pytest.mark.skipif(not utils.is_program("analyze"), reason="FreeLing is not installed")
def test_freeling_eng_slevel(tmp_path):
    """Run corpus freeling-eng-slevel and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/freeling-eng-slevel")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=[
        "csv_export:csv",
        "cwb:info",
        "cwb:vrt",
        "cwb:vrt_scrambled",
        "korp:timespan_sql",
        "stats_export:freq_list_simple",
        "xml_export:pretty",
        "xml_export:preserved_format",
    ])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.freeling
@pytest.mark.skipif(not utils.is_program("analyze"), reason="FreeLing is not installed")
def test_freeling_fra_txt(tmp_path):
    """Run corpus freeling-fra-txt and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/freeling-fra-txt")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=[
        # "korp:timespan_sql", # TODO: These are not working due to a bug
        # "cwb:info",
        "csv_export:csv",
        "cwb:vrt",
        "cwb:vrt_scrambled",
        "stats_export:freq_list_simple",
        "xml_export:pretty",
        "xml_export:preserved_format",
    ])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.treetagger
@pytest.mark.skipif(not paths.get_bin_path("treetagger").exists(), reason="Treetagger is not available")
def test_treetagger_nld(tmp_path):
    """Run corpus treetagger-nld and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/treetagger-nld")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=[
        # "korp:timespan_sql", # TODO: These are not working due to a bug
        # "cwb:info",
        "csv_export:csv",
        "cwb:vrt",
        "cwb:vrt_scrambled",
        "stats_export:freq_list_simple",
        "xml_export:pretty",
        "xml_export:preserved_format",
    ])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.stanford
@pytest.mark.skipif(not paths.get_bin_path("stanford_parser").exists(), reason="Stanford Parser is not available")
def test_stanford_eng(tmp_path):
    """Run corpus stanford-eng and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/stanford-eng")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=[
        # "korp:timespan_sql", # TODO: These are not working due to a bug
        # "cwb:info",
        "csv_export:csv",
        "cwb:vrt",
        "cwb:vrt_scrambled",
        "stats_export:freq_list_simple",
        "xml_export:pretty",
        "xml_export:preserved_format",
    ])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)