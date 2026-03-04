const API = "http://localhost:8000";

function showNotice(msg) {
  document.getElementById("notice").textContent = msg;
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }
  return response.json();
}

function statCard(name, value) {
  return `<div class="stat"><strong>${name}</strong><div>${value}</div></div>`;
}

async function loadFarmers() {
  const farmers = await api("/farmers");
  const select = document.getElementById("farmerId");
  select.innerHTML = farmers
    .map((f) => `<option value="${f.farmer_id}">${f.farmer_id} - ${f.name} (${f.village})</option>`)
    .join("");
}

async function refreshDashboard() {
  const dashboard = await api("/dashboard");
  const m = dashboard.metrics;
  document.getElementById("stats").innerHTML = [
    statCard("Farmers", m.registered_farmers),
    statCard("Collections", m.collections_recorded),
    statCard("Batches", m.processing_batches),
    statCard("Inventory Lots", m.inventory_lots),
    statCard("Sales", m.sales_transactions),
    statCard("Green Leaf (kg)", m.total_green_leaf_collected_kg),
    statCard("Made Tea (kg)", m.expected_made_tea_kg),
    statCard("Revenue (USD)", m.auction_revenue_usd),
    statCard("Compliance %", m.quality_compliance_rate_percent),
  ].join("");
}

async function refreshLists() {
  const [collections, processing, quality, inventory, sales, traceability] = await Promise.all([
    api("/collections"),
    api("/processing"),
    api("/quality-assessments"),
    api("/inventory"),
    api("/auction-sales"),
    api("/traceability"),
  ]);
  document.getElementById("collections").textContent = JSON.stringify(collections, null, 2);
  document.getElementById("processing").textContent = JSON.stringify(processing, null, 2);
  document.getElementById("quality").textContent = JSON.stringify(quality, null, 2);
  document.getElementById("inventory").textContent = JSON.stringify({ inventory, sales }, null, 2);
  document.getElementById("traceability").textContent = JSON.stringify(traceability, null, 2);
}

async function submitCollection() {
  try {
    await api("/collections", {
      method: "POST",
      body: JSON.stringify({
        farmer_id: document.getElementById("farmerId").value,
        kilograms: Number(document.getElementById("kilograms").value),
        leaf_temperature_c: Number(document.getElementById("leafTemp").value),
        moisture_percent: Number(document.getElementById("leafMoisture").value),
      }),
    });
    showNotice("Collection recorded successfully.");
    await syncAll();
  } catch (err) {
    showNotice(`Collection failed: ${err.message}`);
  }
}

async function submitProcessing() {
  try {
    await api("/processing", {
      method: "POST",
      body: JSON.stringify({
        collection_ids: document.getElementById("collectionIds").value.split(",").map((x) => x.trim()).filter(Boolean),
        stage: document.getElementById("stage").value,
        machine_line: document.getElementById("machineLine").value,
        stage_temperature_c: Number(document.getElementById("stageTemp").value),
        duration_minutes: Number(document.getElementById("duration").value),
      }),
    });
    showNotice("Processing batch created.");
    await syncAll();
  } catch (err) {
    showNotice(`Processing failed: ${err.message}`);
  }
}

async function submitQuality() {
  try {
    await api("/quality-assessments", {
      method: "POST",
      body: JSON.stringify({
        batch_id: document.getElementById("qaBatchId").value,
        liquor_color_score: Number(document.getElementById("qaColor").value),
        aroma_score: Number(document.getElementById("qaAroma").value),
        moisture_percent: Number(document.getElementById("qaMoisture").value),
        particle_uniformity_percent: Number(document.getElementById("qaUniformity").value),
        contamination_incidents: Number(document.getElementById("qaContamination").value),
      }),
    });
    showNotice("Quality assessment submitted.");
    await syncAll();
  } catch (err) {
    showNotice(`Quality check failed: ${err.message}`);
  }
}

async function submitSale() {
  try {
    await api("/auction-sales", {
      method: "POST",
      body: JSON.stringify({
        lot_id: document.getElementById("saleLotId").value,
        buyer_name: document.getElementById("buyer").value,
        grade: document.getElementById("grade").value,
        kilograms: Number(document.getElementById("saleKg").value),
        price_per_kg_usd: Number(document.getElementById("pricePerKg").value),
      }),
    });
    showNotice("Auction sale recorded.");
    await syncAll();
  } catch (err) {
    showNotice(`Sale failed: ${err.message}`);
  }
}

async function syncAll() {
  await refreshDashboard();
  await refreshLists();
}

(async function init() {
  try {
    await loadFarmers();
    await syncAll();
    showNotice("System ready.");
  } catch (err) {
    showNotice(`Failed to reach API (${API}). Start backend first.`);
  }
})();
