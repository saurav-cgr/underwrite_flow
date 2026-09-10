const screens = [...document.querySelectorAll("[data-screen]")];
const screenSelect = document.querySelector("#screenSelect");
const navButtons = [...document.querySelectorAll("[data-nav]")];
const profileSwitch = document.querySelector("#profileSwitch");
const roleOptions = [...document.querySelectorAll(".role-option")];
const enterDemo = document.querySelector("#enterDemo");
const toast = document.querySelector("#toast");

let selectedRole = { name: "Applicant", target: "applicant-home" };

function showScreen(name, updateHash = true) {
  if (!screens.some((screen) => screen.dataset.screen === name)) return;
  screens.forEach((screen) => screen.classList.toggle("active", screen.dataset.screen === name));
  navButtons.forEach((button) => button.classList.toggle("active", button.dataset.nav === name));
  screenSelect.value = name;
  if (updateHash) history.replaceState(null, "", `#${name}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
  document.querySelector(`[data-screen="${name}"] h1`)?.focus?.({ preventScroll: true });
}

navButtons.forEach((button) => button.addEventListener("click", () => showScreen(button.dataset.nav)));
screenSelect.addEventListener("change", (event) => showScreen(event.target.value));

roleOptions.forEach((option) => {
  option.addEventListener("click", () => {
    roleOptions.forEach((item) => item.classList.remove("selected"));
    option.classList.add("selected");
    selectedRole = { name: option.dataset.role, target: option.dataset.target };
    enterDemo.firstChild.textContent = `Continue as ${selectedRole.name} `;
  });
});

enterDemo.addEventListener("click", () => {
  const initials = selectedRole.name === "Applicant" ? "AK" : selectedRole.name === "Underwriter" ? "UD" : "AD";
  const displayName = selectedRole.name === "Applicant" ? "Asha Kumar" : `${selectedRole.name} Demo`;
  profileSwitch.querySelector(".avatar").textContent = initials;
  profileSwitch.querySelector("b").textContent = displayName;
  profileSwitch.querySelector("small").textContent = selectedRole.name;
  showScreen(selectedRole.target);
});

profileSwitch.addEventListener("click", () => showScreen("welcome"));

const productCards = [...document.querySelectorAll(".product-card")];
const selectedProduct = document.querySelector("#selectedProduct");
productCards.forEach((card) => {
  card.addEventListener("click", () => {
    productCards.forEach((item) => item.classList.remove("selected"));
    card.classList.add("selected");
    const labels = { Motor: "Private car selected", Life: "Term life selected", Health: "Health insurance selected" };
    selectedProduct.textContent = labels[card.dataset.product];
  });
});

document.querySelectorAll(".choice input").forEach((input) => {
  input.addEventListener("change", () => {
    document.querySelectorAll(".choice").forEach((choice) => choice.classList.remove("selected"));
    input.closest(".choice").classList.add("selected");
  });
});

const queueRows = [...document.querySelectorAll(".data-table tbody tr")];
document.querySelectorAll(".filter").forEach((filter) => {
  filter.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((button) => button.classList.remove("active"));
    filter.classList.add("active");
    queueRows.forEach((row) => {
      row.hidden = filter.dataset.filter !== "all" && row.dataset.product !== filter.dataset.filter;
    });
  });
});

document.querySelector("#queueSearch").addEventListener("input", (event) => {
  const query = event.target.value.trim().toLowerCase();
  queueRows.forEach((row) => { row.hidden = !row.textContent.toLowerCase().includes(query); });
});

queueRows.forEach((row) => row.addEventListener("click", () => showScreen(row.dataset.nav)));

const routeLabels = [...document.querySelectorAll(".route-options label")];
routeLabels.forEach((label) => {
  label.querySelector("input").addEventListener("change", () => {
    routeLabels.forEach((item) => item.classList.remove("selected"));
    label.classList.add("selected");
  });
});

const evidenceConfirmed = document.querySelector("#evidenceConfirmed");
const confirmRoute = document.querySelector("#confirmRoute");
evidenceConfirmed.addEventListener("change", () => { confirmRoute.disabled = !evidenceConfirmed.checked; });
confirmRoute.addEventListener("click", () => {
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3200);
});

const overrideDialog = document.querySelector("#overrideDialog");
document.querySelector("#overrideRoute").addEventListener("click", () => overrideDialog.showModal());
document.querySelector("#cancelOverride").addEventListener("click", () => overrideDialog.close("cancel"));
document.querySelector("#recordOverride").addEventListener("click", () => overrideDialog.close("confirm"));
overrideDialog.addEventListener("close", () => {
  if (overrideDialog.returnValue === "confirm") {
    toast.querySelector("span").textContent = "Override recorded with the original recommendation preserved.";
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3200);
  }
});

document.querySelector("#uploadButton").addEventListener("click", () => {
  toast.querySelector("span").textContent = "Upload interaction shown as a design state.";
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2800);
});

const initialScreen = location.hash.slice(1);
showScreen(initialScreen || "welcome", false);
