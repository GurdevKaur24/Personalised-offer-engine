import pytest

from peshkash.datagen import DEFAULT_SEED, generate
from peshkash.features import customer_view


@pytest.fixture(scope="session")
def raw_customers():
    return generate(2000, DEFAULT_SEED)


@pytest.fixture(scope="session")
def customers(raw_customers):
    return [customer_view(c) for c in raw_customers]
