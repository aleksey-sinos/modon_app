from __future__ import annotations

from unittest.mock import patch

import pytest
import polars as pl
from fastapi.testclient import TestClient

from api.deps import AppState, get_state, load_state
from api.main import app


@pytest.fixture(scope="session")
def full_state() -> AppState:
    """Load and process the real pipeline data once for the entire session."""
    return load_state()


@pytest.fixture(scope="session")
def sampled_state(full_state: AppState) -> AppState:
    """Sample large DataFrames to keep each test fast while staying realistic."""
    tx = full_state.transactions
    mt = full_state.mortgages
    rn = full_state.rents
    ld = full_state.lands
    return AppState(
        projects=full_state.projects,  # 187 rows — keep all
        lands=ld.sample(n=min(1_000, ld.height), seed=42),
        transactions=tx.sample(n=min(500, tx.height), seed=42),
        mortgages=mt.sample(n=min(500, mt.height), seed=42),
        rents=rn.sample(n=min(500, rn.height), seed=42),
    )


@pytest.fixture(scope="session")
def client(sampled_state: AppState):
    """TestClient with the dependency overridden to use sampled data.

    ``api.main.load_state`` is patched so the lifespan event does not
    reload the full dataset on top of the sampled fixture.
    """
    app.dependency_overrides[get_state] = lambda: sampled_state
    with patch("api.main.load_state"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# ── Derived helpers shared across test modules ─────────────────────────────

@pytest.fixture(scope="session")
def known_developer(sampled_state: AppState) -> str:
    """A developer name that exists in the sampled transactions."""
    return (
        sampled_state.transactions["DEVELOPER_EN"]
        .drop_nulls()
        .unique()
        .sort()
        .head(1)[0]
    )


@pytest.fixture(scope="session")
def known_area(sampled_state: AppState) -> str:
    """An area name that exists in the sampled transactions."""
    return (
        sampled_state.transactions["AREA_EN"]
        .drop_nulls()
        .unique()
        .sort()
        .head(1)[0]
    )


@pytest.fixture(scope="session")
def known_prop_type(sampled_state: AppState) -> str:
    """A property type that exists in the sampled transactions."""
    return (
        sampled_state.transactions["PROP_TYPE_EN"]
        .drop_nulls()
        .unique()
        .sort()
        .head(1)[0]
    )
