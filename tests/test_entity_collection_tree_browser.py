import mammos_units as u
import numpy as np
import pytest
from playwright.sync_api import Page, expect

import mammos_entity as me

pytestmark = pytest.mark.browser


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(me.M(np.arange(60.0), "A/m"), id="entity"),
        pytest.param(u.Quantity(np.arange(60.0), "A/m"), id="quantity"),
        pytest.param(np.arange(60.0), id="array"),
        pytest.param(list(range(60)), id="list"),
        pytest.param(tuple(range(60)), id="tuple"),
        pytest.param({f"k{i}": i for i in range(60)}, id="dict"),
    ],
)
def test_structured_leaf_disclosure_in_browser(page: Page, value: object) -> None:
    page.set_content(me.EntityCollection(value=value)._repr_html_())

    details = page.locator("details.lazy-leaf-details")
    summary = details.locator(":scope > summary")
    body = details.locator(":scope > .entity-expanded-details")
    plus_toggle = summary.locator(":scope > .entity-toggle").nth(0)
    minus_toggle = summary.locator(":scope > .entity-toggle").nth(1)

    expect(details).to_have_count(1)
    expect(body).to_be_hidden()
    expect(plus_toggle).to_be_visible()
    expect(minus_toggle).to_be_hidden()

    summary.click()

    expect(details).to_have_attribute("open", "")
    expect(body).to_be_visible()
    expect(body).to_contain_text("59")
    expect(plus_toggle).to_be_hidden()
    expect(minus_toggle).to_be_visible()

    summary.click()

    expect(body).to_be_hidden()
    expect(plus_toggle).to_be_visible()
    expect(minus_toggle).to_be_hidden()


def test_nested_collection_disclosure_in_browser(page: Page) -> None:
    collection = me.EntityCollection(group=me.EntityCollection(values=list(range(60))))
    page.set_content(collection._repr_html_())

    nested = page.locator("details.branch-node")
    summary = nested.locator(":scope > summary")
    children = nested.locator(":scope > .collection-children")
    structured_leaf = children.locator("details.lazy-leaf-details")

    expect(nested).to_have_count(1)
    expect(children).to_be_hidden()
    expect(structured_leaf).to_be_hidden()

    summary.click()

    expect(nested).to_have_attribute("open", "")
    expect(children).to_be_visible()
    expect(children).to_contain_text("values")
    expect(structured_leaf).to_be_visible()
    expect(structured_leaf.locator(":scope > .entity-expanded-details")).to_be_hidden()

    summary.click()

    expect(children).to_be_hidden()
    expect(structured_leaf).to_be_hidden()
