function findLazyNode(root, lazyId) {
  if (root.dataset.lazyId === lazyId) {
    return root;
  }
  return Array.from(root.querySelectorAll("[data-lazy-id]")).find(
    (element) => element.dataset.lazyId === lazyId,
  ) ?? null;
}

function hasClass(node, className) {
  return typeof node.className === "string" && node.className.split(/\s+/).includes(className);
}

function directChildByClass(node, className) {
  return Array.from(node.children).find((child) => hasClass(child, className)) ?? null;
}

function childrenContainer(node) {
  return directChildByClass(node, "collection-children");
}

function footerContainer(node) {
  return directChildByClass(node, "collection-footer");
}

function eventTargetElement(target) {
  if (target instanceof HTMLElement) {
    return target;
  }
  if (target && typeof target === "object" && "parentElement" in target) {
    return target.parentElement;
  }
  return null;
}

function requestLazyNode(model, root, lazyId, options = {}) {
  const node = findLazyNode(root, lazyId);
  if (!node) {
    return;
  }
  if (node instanceof HTMLDetailsElement && !node.open) {
    return;
  }
  if (options.force !== true && node.dataset.lazyLoaded === "true") {
    return;
  }
  if (node.dataset.lazyLoading === "true" || node.dataset.lazyDone === "true") {
    return;
  }
  node.dataset.lazyLoading = "true";
  const cursor = Number(node.dataset.lazyCursor || "0");
  model.send({
    kind: "render-lazy",
    lazy_id: lazyId,
    cursor,
    load_all: options.loadAll === true,
  });
}

function resetCollectionNode(node) {
  const container = childrenContainer(node);
  if (container) {
    container.innerHTML = node.dataset.initialChildrenHtml ?? "";
  }
  const footer = footerContainer(node);
  if (footer) {
    footer.innerHTML = "";
  }
  node.dataset.hasControls = "false";
  node.dataset.lazyCursor = "0";
  node.dataset.lazyDone = "false";
  node.dataset.lazyLoading = "false";
  node.dataset.lazyLoaded = "false";
}

function appendChildren(node, htmlText) {
  if (!htmlText) {
    return;
  }
  const container = childrenContainer(node);
  if (!container) {
    return;
  }
  const template = document.createElement("template");
  template.innerHTML = htmlText;
  container.append(template.content);
}

function replaceControls(node, htmlText) {
  const footer = footerContainer(node);
  if (!footer) {
    return;
  }
  footer.innerHTML = htmlText ?? "";
  node.dataset.hasControls = htmlText ? "true" : "false";
}

function installRoot(model, el) {
  el.innerHTML = model.get("root_html");
  const root = el.querySelector(".mammos-entity-collection");
  if (!root) {
    return null;
  }
  requestLazyNode(model, root, root.dataset.lazyId, { force: true });
  return root;
}

export function render({ model, el }) {
  let root = installRoot(model, el);

  const handleCollectionControl = (event) => {
    const target = eventTargetElement(event.target);
    if (!(target instanceof HTMLElement) || !root) {
      return;
    }
    const button = target.closest(".collection-control");
    if (!(button instanceof HTMLElement)) {
      return;
    }
    event.preventDefault();
    const lazyId = button.dataset.lazyTargetId;
    if (!lazyId) {
      return;
    }
    requestLazyNode(model, root, lazyId, {
      force: true,
      loadAll: button.dataset.lazyAction === "all",
    });
  };

  const handleToggle = (event) => {
    const target = event.target;
    if (!(target instanceof HTMLDetailsElement)) {
      return;
    }
    if (!target.open) {
      if (target.dataset.lazyPatch === "append-children") {
        resetCollectionNode(target);
      }
      return;
    }
    if (root) {
      requestLazyNode(model, root, target.dataset.lazyId);
    }
  };

  const handleMessage = (message) => {
    if (!root || typeof message !== "object" || message === null) {
      return;
    }
    if (message.kind === "lazy-rendered") {
      const node = findLazyNode(root, message.lazy_id);
      if (!node) {
        return;
      }
      if (message.patch === "replace-self") {
        const template = document.createElement("template");
        template.innerHTML = message.html ?? "";
        const replacement = template.content.firstElementChild;
        if (replacement) {
          node.replaceWith(replacement);
        }
        return;
      }
      appendChildren(node, message.html);
      replaceControls(node, message.controls_html);
      node.dataset.lazyLoading = "false";
      node.dataset.lazyCursor = String(message.next_cursor ?? 0);
      node.dataset.lazyDone = message.done ? "true" : "false";
      node.dataset.lazyLoaded = "true";
      return;
    }
    if (message.kind === "lazy-error") {
      const node = findLazyNode(root, message.lazy_id);
      if (node) {
        node.dataset.lazyLoading = "false";
      }
      console.error(message.message || "Unable to render lazy node.");
    }
  };

  const rerender = () => {
    root = installRoot(model, el);
  };

  el.addEventListener("toggle", handleToggle, true);
  el.addEventListener("click", handleCollectionControl);
  model.on("msg:custom", handleMessage);
  model.on("change:root_html", rerender);

  return () => {
    el.removeEventListener("toggle", handleToggle, true);
    el.removeEventListener("click", handleCollectionControl);
    model.off("msg:custom", handleMessage);
    model.off("change:root_html", rerender);
  };
}
