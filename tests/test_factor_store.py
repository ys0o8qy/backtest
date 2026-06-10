from __future__ import annotations

from datetime import date

import pandas as pd

from akquant.factor_store import FactorStore


def test_factor_store_saves_and_loads_latest_available_snapshot(tmp_path):
    store = FactorStore(tmp_path)
    frame = pd.DataFrame({"symbol": ["000001"], "pe_ttm": [8.0]})

    store.save_snapshot(as_of_date=date(2026, 6, 10), frame=frame, metadata={"source": "test"})
    loaded, metadata = store.load_snapshot(as_of_date=date(2026, 6, 12))

    assert loaded.to_dict("records") == [{"symbol": "000001", "pe_ttm": 8.0}]
    assert metadata["source"] == "test"
    assert metadata["as_of_date"] == "2026-06-10"


def test_factor_store_roundtrips_list_quality_flags(tmp_path):
    store = FactorStore(tmp_path)
    frame = pd.DataFrame(
        {
            "symbol": ["000001"],
            "pe_ttm": [8.0],
            "data_quality_flags": [["missing_pb", "dividend_yield_from_fhps"]],
        }
    )

    store.save_snapshot(as_of_date=date(2026, 6, 10), frame=frame)
    loaded, _ = store.load_snapshot(as_of_date=date(2026, 6, 10))

    assert loaded.loc[0, "symbol"] == "000001"
    assert loaded.loc[0, "data_quality_flags"] == ["missing_pb", "dividend_yield_from_fhps"]


def test_factor_store_ignores_non_snapshot_csv_files(tmp_path):
    store = FactorStore(tmp_path)
    (tmp_path / "screen-export.csv").write_text("symbol\n000001\n", encoding="utf-8")
    store.save_snapshot(as_of_date=date(2026, 6, 10), frame=pd.DataFrame({"symbol": ["000001"]}))

    loaded, metadata = store.load_snapshot(as_of_date=date(2026, 6, 10))

    assert loaded.loc[0, "symbol"] == "000001"
    assert metadata["as_of_date"] == "2026-06-10"


def test_factor_store_decodes_legacy_plain_string_quality_flag(tmp_path):
    store = FactorStore(tmp_path)
    (tmp_path / "2026-06-10.csv").write_text(
        "symbol,data_quality_flags\n000001,missing_pb\n",
        encoding="utf-8",
    )
    (tmp_path / "2026-06-10.json").write_text('{"as_of_date": "2026-06-10"}', encoding="utf-8")

    loaded, _ = store.load_snapshot(as_of_date=date(2026, 6, 10))

    assert loaded.loc[0, "data_quality_flags"] == ["missing_pb"]
