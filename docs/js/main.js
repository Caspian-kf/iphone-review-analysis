const DATA_URLS = ["../data/reviews.json", "data/reviews.json"];
const CATEGORIES = ["手机", "手表", "平板", "电脑"];
const SENTIMENTS = ["正面", "中性", "负面"];

async function loadReviews() {
  let lastError = null;

  for (const url of DATA_URLS) {
    try {
      const response = await fetch(url);

      if (response.ok) {
        return response.json();
      }

      lastError = new Error(`数据读取失败：${response.status}`);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError;
}

function countByField(reviews, field) {
  return reviews.reduce((result, item) => {
    const key = item[field] || "未知";
    result[key] = (result[key] || 0) + 1;
    return result;
  }, {});
}

function countSentimentByCategory(reviews) {
  return CATEGORIES.reduce((result, category) => {
    result[category] = SENTIMENTS.reduce((sentimentMap, sentiment) => {
      sentimentMap[sentiment] = reviews.filter(
        (item) => item.category === category && item.sentiment === sentiment
      ).length;
      return sentimentMap;
    }, {});
    return result;
  }, {});
}

function getStats(reviews) {
  const categoryCounts = countByField(reviews, "category");
  const sentimentCounts = countByField(reviews, "sentiment");
  const platformCounts = countByField(reviews, "platform");
  const keywordCounts = countByField(reviews, "keyword");
  const categorySentimentCounts = countSentimentByCategory(reviews);
  const latestCrawlTime = reviews
    .map((item) => item.crawl_time)
    .filter(Boolean)
    .sort()
    .at(-1);

  return {
    total: reviews.length,
    categoryCounts,
    sentimentCounts,
    platformCounts,
    keywordCounts,
    categorySentimentCounts,
    platformCount: Object.keys(platformCounts).length,
    latestCrawlTime: latestCrawlTime || "--",
  };
}

function setText(id, value) {
  const element = document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

function renderHome(reviews) {
  const stats = getStats(reviews);

  setText("totalReviews", stats.total);
  setText("phoneCount", stats.categoryCounts["手机"] || 0);
  setText("watchCount", stats.categoryCounts["手表"] || 0);
  setText("tabletCount", stats.categoryCounts["平板"] || 0);
  setText("computerCount", stats.categoryCounts["电脑"] || 0);
  setText("positiveReviews", stats.sentimentCounts["正面"] || 0);
  setText("neutralReviews", stats.sentimentCounts["中性"] || 0);
  setText("negativeReviews", stats.sentimentCounts["负面"] || 0);
  setText("platformCount", stats.platformCount);
  setText("latestCrawlTime", stats.latestCrawlTime);
}

function populateSelect(selectId, values) {
  const select = document.getElementById(selectId);

  if (!select) {
    return;
  }

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function getSentimentClass(sentiment) {
  if (sentiment === "正面") {
    return "sentiment-positive";
  }

  if (sentiment === "负面") {
    return "sentiment-negative";
  }

  return "sentiment-neutral";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderTable(reviews) {
  const tableBody = document.getElementById("reviewsTableBody");
  const emptyMessage = document.getElementById("emptyMessage");

  if (!tableBody || !emptyMessage) {
    return;
  }

  tableBody.innerHTML = "";
  emptyMessage.hidden = reviews.length > 0;

  reviews.forEach((review) => {
    const row = document.createElement("tr");
    const sentimentClass = getSentimentClass(review.sentiment);

    row.innerHTML = `
      <td><span class="category-pill">${escapeHtml(review.category)}</span></td>
      <td>${escapeHtml(review.platform)}</td>
      <td>${escapeHtml(review.keyword)}</td>
      <td>${escapeHtml(review.title)}</td>
      <td class="content-cell">${escapeHtml(review.content)}</td>
      <td><span class="sentiment ${sentimentClass}">${escapeHtml(review.sentiment)}</span></td>
      <td>${escapeHtml(review.publish_time)}</td>
      <td><a class="link" href="${escapeHtml(review.url)}" target="_blank" rel="noopener">查看原文</a></td>
      <td>${escapeHtml(review.crawl_time)}</td>
    `;

    tableBody.appendChild(row);
  });
}

function filterReviews(reviews) {
  const category = document.getElementById("categoryFilter")?.value || "";
  const platform = document.getElementById("platformFilter")?.value || "";
  const sentiment = document.getElementById("sentimentFilter")?.value || "";
  const keyword = document.getElementById("keywordSearch")?.value.trim().toLowerCase() || "";

  return reviews.filter((review) => {
    const categoryMatched = !category || review.category === category;
    const platformMatched = !platform || review.platform === platform;
    const sentimentMatched = !sentiment || review.sentiment === sentiment;
    const keywordMatched = [review.category, review.keyword, review.title, review.content]
      .join(" ")
      .toLowerCase()
      .includes(keyword);

    return categoryMatched && platformMatched && sentimentMatched && keywordMatched;
  });
}

function renderDataPage(reviews) {
  const platforms = Object.keys(countByField(reviews, "platform")).sort();

  populateSelect("categoryFilter", CATEGORIES);
  populateSelect("platformFilter", platforms);
  populateSelect("sentimentFilter", SENTIMENTS);
  renderTable(reviews);

  ["categoryFilter", "platformFilter", "sentimentFilter", "keywordSearch"].forEach((id) => {
    const element = document.getElementById(id);
    element?.addEventListener("input", () => renderTable(filterReviews(reviews)));
  });
}

function objectToChartData(counts) {
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

function createBarOption(title, names, values, color, rotate = 0) {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 42, right: 22, top: 32, bottom: rotate ? 92 : 48 },
    xAxis: {
      type: "category",
      data: names,
      axisLabel: { interval: 0, rotate },
    },
    yAxis: { type: "value", minInterval: 1 },
    color: [color],
    series: [
      {
        name: title,
        type: "bar",
        data: values,
        barMaxWidth: 42,
      },
    ],
  };
}

function renderCharts(reviews) {
  if (typeof echarts === "undefined") {
    return;
  }

  const stats = getStats(reviews);
  const chartElements = {
    sentiment: document.getElementById("sentimentChart"),
    category: document.getElementById("categoryChart"),
    platform: document.getElementById("platformChart"),
    keyword: document.getElementById("keywordChart"),
    categorySentiment: document.getElementById("categorySentimentChart"),
  };

  const charts = Object.values(chartElements).map((element) => echarts.init(element));
  const [sentimentChart, categoryChart, platformChart, keywordChart, categorySentimentChart] = charts;

  sentimentChart.setOption({
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    color: ["#17a36b", "#d58a00", "#e24a4a"],
    series: [
      {
        name: "情感占比",
        type: "pie",
        radius: ["42%", "68%"],
        center: ["50%", "44%"],
        data: SENTIMENTS.map((name) => ({
          name,
          value: stats.sentimentCounts[name] || 0,
        })),
        label: { formatter: "{b}: {d}%" },
      },
    ],
  });

  const categoryValues = CATEGORIES.map((category) => stats.categoryCounts[category] || 0);
  categoryChart.setOption(createBarOption("类别数据量", CATEGORIES, categoryValues, "#246bfe"));

  const platformData = objectToChartData(stats.platformCounts).sort((a, b) => b.value - a.value).slice(0, 12);
  platformChart.setOption(
    createBarOption(
      "平台数据量",
      platformData.map((item) => item.name),
      platformData.map((item) => item.value),
      "#5f6bff",
      platformData.length > 5 ? 28 : 0
    )
  );

  const keywordData = objectToChartData(stats.keywordCounts).sort((a, b) => b.value - a.value);
  keywordChart.setOption(
    createBarOption(
      "关键词数据量",
      keywordData.map((item) => item.name),
      keywordData.map((item) => item.value),
      "#17a36b",
      30
    )
  );

  categorySentimentChart.setOption({
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { left: 42, right: 22, top: 48, bottom: 42 },
    xAxis: { type: "category", data: CATEGORIES },
    yAxis: { type: "value", minInterval: 1 },
    color: ["#17a36b", "#d58a00", "#e24a4a"],
    series: SENTIMENTS.map((sentiment) => ({
      name: sentiment,
      type: "bar",
      stack: "sentiment",
      data: CATEGORIES.map((category) => stats.categorySentimentCounts[category][sentiment] || 0),
      barMaxWidth: 54,
    })),
  });

  window.addEventListener("resize", () => charts.forEach((chart) => chart.resize()));
}

function showLoadError(error) {
  console.error(error);

  setText("totalReviews", "读取失败");
  setText("phoneCount", "--");
  setText("watchCount", "--");
  setText("tabletCount", "--");
  setText("computerCount", "--");
  setText("positiveReviews", "--");
  setText("neutralReviews", "--");
  setText("negativeReviews", "--");
  setText("platformCount", "--");
  setText("latestCrawlTime", "--");

  const emptyMessage = document.getElementById("emptyMessage");
  if (emptyMessage) {
    emptyMessage.hidden = false;
    emptyMessage.textContent = "数据读取失败，请确认 data/reviews.json 文件是否存在。";
  }
}

async function initPage() {
  try {
    const reviews = await loadReviews();
    const page = document.body.dataset.page;

    if (page === "home") {
      renderHome(reviews);
    }

    if (page === "data") {
      renderDataPage(reviews);
    }

    if (page === "analysis") {
      renderCharts(reviews);
    }
  } catch (error) {
    showLoadError(error);
  }
}

initPage();
