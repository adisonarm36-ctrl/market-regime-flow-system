(function () {
  "use strict";

  const state = {
    rows: window.SAMPLE_SECURITIES.slice(),
    query: "",
    riskProfile: "balanced"
  };

  const weights = {
    balanced: { momentum: 0.32, relativeStrength: 0.28, flow: 0.3, quality: 0.1 },
    riskOn: { momentum: 0.4, relativeStrength: 0.3, flow: 0.25, quality: 0.05 },
    defensive: { momentum: 0.22, relativeStrength: 0.24, flow: 0.34, quality: 0.2 }
  };

  const els = {
    asOfDate: document.getElementById("asOfDate"),
    riskProfile: document.getElementById("riskProfile"),
    searchBox: document.getElementById("searchBox"),
    csvFile: document.getElementById("csvFile"),
    resetData: document.getElementById("resetData"),
    regimeLabel: document.getElementById("regimeLabel"),
    marketPulse: document.getElementById("marketPulse"),
    answerAssetClass: document.getElementById("answerAssetClass"),
    answerCountry: document.getElementById("answerCountry"),
    answerSector: document.getElementById("answerSector"),
    answerTheme: document.getElementById("answerTheme"),
    answerIdeas: document.getElementById("answerIdeas"),
    answerDr: document.getElementById("answerDr"),
    assetBars: document.getElementById("assetBars"),
    countryList: document.getElementById("countryList"),
    countryCount: document.getElementById("countryCount"),
    themeClusters: document.getElementById("themeClusters"),
    ideaTable: document.getElementById("ideaTable"),
    ideaCount: document.getElementById("ideaCount")
  };

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function avg(items, field) {
    if (!items.length) return 0;
    return items.reduce((sum, item) => sum + Number(item[field] || 0), 0) / items.length;
  }

  function groupBy(rows, key) {
    return rows.reduce((map, row) => {
      const value = row[key] || "Unknown";
      if (!map[value]) map[value] = [];
      map[value].push(row);
      return map;
    }, {});
  }

  function qualityScore(row) {
    const liquidity = Number(row.liquidity || 0);
    const spreadPenalty = clamp(Number(row.spreadBps || 0), 0, 80) * 0.55;
    const trackingPenalty = clamp(Number(row.trackingError || 0), 0, 10) * 4.5;
    return clamp(liquidity - spreadPenalty - trackingPenalty + 20, 0, 100);
  }

  function scoreRow(row) {
    const w = weights[state.riskProfile];
    return (
      Number(row.momentum || 0) * w.momentum +
      Number(row.relativeStrength || 0) * w.relativeStrength +
      Number(row.flow || 0) * w.flow +
      qualityScore(row) * w.quality
    );
  }

  function scoreGroup(rows) {
    return avg(rows, "momentum") * 0.28 + avg(rows, "relativeStrength") * 0.27 + avg(rows, "flow") * 0.35 + avg(rows.map((row) => ({ quality: qualityScore(row) })), "quality") * 0.1;
  }

  function topGroups(rows, key, limit) {
    return Object.entries(groupBy(rows, key))
      .map(([name, items]) => ({
        name,
        count: items.length,
        score: scoreGroup(items),
        flow: avg(items, "flow"),
        momentum: avg(items, "momentum")
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  function clusterRows(rows) {
    const clusters = {};
    rows.forEach((row) => {
      const labels = String(row.correlations || row.theme || "")
        .split(",")
        .map((label) => label.trim())
        .filter(Boolean);
      labels.forEach((label) => {
        if (!clusters[label]) clusters[label] = [];
        clusters[label].push(row);
      });
    });
    return Object.entries(clusters)
      .map(([name, items]) => ({
        name,
        count: items.length,
        score: scoreGroup(items),
        leaders: items
          .slice()
          .sort((a, b) => scoreRow(b) - scoreRow(a))
          .slice(0, 3)
      }))
      .sort((a, b) => b.score - a.score);
  }

  function diversifiedIdeas(rows, limit) {
    const sorted = rows
      .filter((row) => ["Stock", "DR"].includes(row.type))
      .map((row) => ({ ...row, score: scoreRow(row), quality: qualityScore(row) }))
      .sort((a, b) => b.score - a.score);

    const selected = [];
    const usedTheme = new Set();
    const usedIndustry = new Set();

    sorted.forEach((row) => {
      if (selected.length >= limit) return;
      const themePenalty = usedTheme.has(row.theme);
      const industryPenalty = usedIndustry.has(row.industry);
      if (themePenalty && industryPenalty) return;
      selected.push(row);
      usedTheme.add(row.theme);
      usedIndustry.add(row.industry);
    });

    return selected;
  }

  function filteredRows() {
    const q = state.query.trim().toLowerCase();
    if (!q) return state.rows;
    return state.rows.filter((row) => {
      return [row.symbol, row.name, row.type, row.country, row.sector, row.industry, row.theme, row.assetClass, row.correlations]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }

  function strengthClass(score) {
    if (score >= 75) return "strong";
    if (score >= 55) return "neutral";
    return "weak";
  }

  function formatScore(score) {
    return Math.round(score).toString();
  }

  function renderBars(groups) {
    els.assetBars.innerHTML = groups
      .map((group) => {
        const width = clamp(group.score, 8, 100);
        return `
          <div class="bar-row">
            <div class="bar-meta">
              <strong>${group.name}</strong>
              <span>${formatScore(group.score)} / flow ${formatScore(group.flow)}</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill ${strengthClass(group.score)}" style="width:${width}%"></div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function renderCountryList(groups) {
    els.countryCount.textContent = `${groups.length} markets`;
    els.countryList.innerHTML = groups
      .map((group, index) => `
        <div class="rank-item">
          <span class="rank">${index + 1}</span>
          <div>
            <strong>${group.name}</strong>
            <small>${group.count} instruments · momentum ${formatScore(group.momentum)}</small>
          </div>
          <b class="${strengthClass(group.score)}">${formatScore(group.score)}</b>
        </div>
      `)
      .join("");
  }

  function renderClusters(clusters) {
    els.themeClusters.innerHTML = clusters
      .slice(0, 8)
      .map((cluster) => `
        <article class="cluster ${strengthClass(cluster.score)}">
          <div>
            <strong>${cluster.name}</strong>
            <span>${cluster.count} linked names</span>
          </div>
          <b>${formatScore(cluster.score)}</b>
          <small>${cluster.leaders.map((row) => row.symbol).join(" · ")}</small>
        </article>
      `)
      .join("");
  }

  function renderIdeas(ideas) {
    els.ideaCount.textContent = `${ideas.length} names`;
    els.ideaTable.innerHTML = ideas
      .map((row) => `
        <tr>
          <td><strong>${row.symbol}</strong><small>${row.name}</small></td>
          <td>${row.country}<small>${row.sector}</small></td>
          <td>${row.theme}<small>${row.industry}</small></td>
          <td><b class="${strengthClass(row.score)}">${formatScore(row.score)}</b></td>
          <td>${row.type === "DR" ? `${formatScore(row.quality)}<small>${row.spreadBps} bps · TE ${row.trackingError}</small>` : "Direct"}</td>
        </tr>
      `)
      .join("");
  }

  function renderAnswers(rows, assets, countries, sectors, industries, themes, ideas, drs) {
    const topAsset = assets[0];
    const topCountry = countries[0];
    const topSector = sectors[0];
    const topIndustry = industries[0];
    const topTheme = themes[0];
    const bestDr = drs[0];

    els.answerAssetClass.textContent = topAsset ? `${topAsset.name} นำด้วย score ${formatScore(topAsset.score)} และ flow ${formatScore(topAsset.flow)}` : "ไม่มีข้อมูล";
    els.answerCountry.textContent = topCountry ? `${topCountry.name} แข็งสุดใน sample universe (${topCountry.count} instruments)` : "ไม่มีข้อมูล";
    els.answerSector.textContent = topSector && topIndustry ? `${topSector.name} / ${topIndustry.name} แข็งสุด; leader momentum ${formatScore(topIndustry.momentum)}` : "ไม่มีข้อมูล";
    els.answerTheme.textContent = topTheme ? `${topTheme.name} ถูกซื้อเด่น โดยมี ${topTheme.leaders.map((row) => row.symbol).join(", ")} เป็นตัวนำ` : "ไม่มีข้อมูล";
    els.answerIdeas.textContent = ideas.length ? ideas.map((row) => row.symbol).join(", ") : "ไม่มีข้อมูล";
    els.answerDr.textContent = bestDr ? `${bestDr.symbol} quality ${formatScore(bestDr.quality)} จาก liquidity ${bestDr.liquidity}, spread ${bestDr.spreadBps} bps, tracking error ${bestDr.trackingError}` : "ไม่มี DR ที่ผ่านเกณฑ์";

    const pulse = avg(rows.map((row) => ({ score: scoreRow(row) })), "score");
    els.marketPulse.textContent = formatScore(pulse);
    els.regimeLabel.textContent = pulse >= 72 ? "Risk-on accumulation" : pulse >= 55 ? "Mixed rotation" : "Defensive / weak tape";
  }

  function render() {
    const rows = filteredRows();
    const assets = topGroups(rows, "assetClass", 6);
    const countries = topGroups(rows.filter((row) => row.assetClass === "Equity"), "country", 8);
    const sectors = topGroups(rows.filter((row) => row.assetClass === "Equity"), "sector", 8);
    const industries = topGroups(rows.filter((row) => row.assetClass === "Equity"), "industry", 8);
    const themes = clusterRows(rows);
    const ideas = diversifiedIdeas(rows, 8);
    const drs = rows
      .filter((row) => row.type === "DR")
      .map((row) => ({ ...row, score: scoreRow(row), quality: qualityScore(row) }))
      .filter((row) => row.quality >= 45 && row.spreadBps <= 35 && row.trackingError <= 2.5)
      .sort((a, b) => b.quality - a.quality || b.score - a.score);

    renderAnswers(rows, assets, countries, sectors, industries, themes, ideas, drs);
    renderBars(assets);
    renderCountryList(countries);
    renderClusters(themes);
    renderIdeas(ideas);
  }

  function normalizeRow(row) {
    const numericFields = ["momentum", "relativeStrength", "flow", "liquidity", "spreadBps", "trackingError"];
    numericFields.forEach((field) => {
      row[field] = Number(row[field] || 0);
    });
    row.type = row.type || "Stock";
    row.assetClass = row.assetClass || "Equity";
    row.correlations = row.correlations || row.theme || "";
    return row;
  }

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = splitCsvLine(lines.shift()).map((header) => header.trim());
    return lines
      .filter(Boolean)
      .map((line) => {
        const cells = splitCsvLine(line).map((cell) => cell.trim());
        const row = {};
        headers.forEach((header, index) => {
          row[header] = cells[index] || "";
        });
        return normalizeRow(row);
      });
  }

  function splitCsvLine(line) {
    const cells = [];
    let current = "";
    let quoted = false;

    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      const next = line[index + 1];

      if (char === "\"" && quoted && next === "\"") {
        current += "\"";
        index += 1;
      } else if (char === "\"") {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        cells.push(current);
        current = "";
      } else {
        current += char;
      }
    }

    cells.push(current);
    return cells;
  }

  function setToday() {
    const today = new Date();
    const iso = today.toISOString().slice(0, 10);
    els.asOfDate.value = iso;
  }

  els.searchBox.addEventListener("input", (event) => {
    state.query = event.target.value;
    render();
  });

  els.riskProfile.addEventListener("change", (event) => {
    state.riskProfile = event.target.value;
    render();
  });

  els.csvFile.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      state.rows = parseCsv(String(reader.result));
      render();
    };
    reader.readAsText(file);
  });

  els.resetData.addEventListener("click", () => {
    state.rows = window.SAMPLE_SECURITIES.slice();
    els.searchBox.value = "";
    state.query = "";
    render();
  });

  setToday();
  render();
})();
