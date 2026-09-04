const docsIndex = [
  { title: "Get started", description: "Set up UseAgent and run your first supervisor-to-worker handover.", href: "getting-started.html" },
  { title: "Runtime roster", description: "Connect Codex, Claude Code, Antigravity or another compatible runtime.", href: "getting-started.html#runtimes" },
  { title: "Architecture", description: "Understand the knowledge ledger, registry, mailbox and production gate.", href: "architecture.html" },
  { title: "Worker loop", description: "Pull one task, implement in scope, report checks and continue the cycle.", href: "operations.html#worker-loop" },
  { title: "Autopilot cycle", description: "Run bounded cycles with QA, checkpoints and explicit stop conditions.", href: "operations.html#cycle" },
  { title: "Hướng dẫn tiếng Việt", description: "Thiết lập supervisor, worker và chu trình report bằng tiếng Việt.", href: "vi.html" },
];

const menuButton = document.querySelector(".menu-toggle");
const primaryNav = document.querySelector(".primary-nav");
if (menuButton && primaryNav) {
  menuButton.addEventListener("click", () => {
    const open = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!open));
    primaryNav.classList.toggle("open", !open);
  });
}

const searchForm = document.querySelector(".search-form");
const searchInput = document.querySelector("#doc-search");
const searchResults = document.querySelector("#search-results");
function renderResults(query) {
  if (!searchResults || !searchInput) return;
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    searchResults.hidden = true;
    searchInput.setAttribute("aria-expanded", "false");
    searchResults.replaceChildren();
    return;
  }
  const matches = docsIndex.filter((item) => `${item.title} ${item.description}`.toLowerCase().includes(normalized));
  searchResults.replaceChildren();
  if (matches.length === 0) {
    const empty = document.createElement("p");
    empty.className = "search-empty";
    empty.textContent = "No exact match yet. Try “worker”, “runtime” or “production gate”.";
    searchResults.append(empty);
  } else {
    matches.forEach((item) => {
      const link = document.createElement("a");
      link.className = "search-result";
      link.href = item.href;
      const title = document.createElement("strong");
      title.textContent = item.title;
      const description = document.createElement("small");
      description.textContent = item.description;
      link.append(title, description);
      searchResults.append(link);
    });
  }
  searchResults.hidden = false;
  searchInput.setAttribute("aria-expanded", "true");
}
if (searchInput) searchInput.addEventListener("input", () => renderResults(searchInput.value));
if (searchForm) {
  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const match = docsIndex.find((item) => `${item.title} ${item.description}`.toLowerCase().includes(query));
    if (match && query) window.location.href = match.href;
    else renderResults(query);
  });
}
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k" && searchInput) {
    event.preventDefault();
    searchInput.focus();
  }
});
