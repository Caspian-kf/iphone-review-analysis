const DATA_URLS = ["../data/reviews.json", "data/reviews.json"];
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

function getStats(reviews) {
  const sentimentCounts = countByField(reviews, "sentiment");
  const platformCounts = countByField(reviews, "platform");
  const keywordCounts = countByField(reviews, "keyword");
  const latestCrawlTime = reviews
    .map((item) => item.crawl_time)
    .filter(Boolean)
    .sort()
    .at(-1);

  return {
    total: reviews.length,
    positive: sentimentCounts["正面"] || 0,
    neutral: sentimentCounts["中性"] || 0,
    negative: sentimentCounts["负面"] || 0,
    platformCount: Object.keys(platformCounts).length,
    latestCrawlTime: latestCrawlTime || "--",
    sentimentCounts,
    platformCounts,
    keywordCounts,
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
  setText("positiveReviews", stats.positive);
  setText("neutralReviews", stats.neutral);
  setText("negativeReviews", stats.negative);
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
      <td>${review.platform}</td>
      <td>${review.keyword}</td>
      <td>${review.title}</td>
      <td class="content-cell">${review.content}</td>
      <td><span class="sentiment ${sentimentClass}">${review.sentiment}</span></td>
      <td>${review.publish_time}</td>
      <td><a class="link" href="${review.url}" target="_blank" rel="noopener">查看原文</a></td>
      <td>${review.crawl_time}</td>
    `;

    tableBody.appendChild(row);
  });
}

function filterReviews(reviews) {
  const keyword = document.getElementById("keywordSearch")?.value.trim().toLowerCase() || "";
  const sentiment = document.getElementById("sentimentFilter")?.value || "";
  const platform = document.getElementById("platformFilter")?.value || "";

  return reviews.filter((review) => {
    const keywordMatched = [review.keyword, review.title, review.content]
      .join(" ")
      .toLowerCase()
      .includes(keyword);
    const sentimentMatched = !sentiment || review.sentiment === sentiment;
    const platformMatched = !platform || review.platform === platform;

    return keywordMatched && sentimentMatched && platformMatched;
  });
}

function renderDataPage(reviews) {
  const platforms = Object.keys(countByField(reviews, "platform")).sort();

  populateSelect("sentimentFilter", SENTIMENTS);
  populateSelect("platformFilter", platforms);
  renderTable(reviews);

  ["keywordSearch", "sentimentFilter", "platformFilter"].forEach((id) => {
    const element = document.getElementById(id);
    element?.addEventListener("input", () => renderTable(filterReviews(reviews)));
  });
}

function objectToChartData(counts) {
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

function renderCharts(reviews) {
  if (typeof echarts === "undefined") {
    return;
  }

  const stats = getStats(reviews);
  const sentimentChart = echarts.init(document.getElementById("sentimentChart"));
  const platformChart = echarts.init(document.getElementById("platformChart"));
  const keywordChart = echarts.init(document.getElementById("keywordChart"));

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
        label: {
          formatter: "{b}: {d}%",
        },
      },
    ],
  });

  platformChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 20, top: 32, bottom: 42 },
    xAxis: {
      type: "category",
      data: Object.keys(stats.platformCounts),
      axisLabel: { interval: 0 },
    },
    yAxis: { type: "value", minInterval: 1 },
    color: ["#246bfe"],
    series: [
      {
        name: "评论数量",
        type: "bar",
        data: Object.values(stats.platformCounts),
        barMaxWidth: 42,
      },
    ],
  });

  const keywordData = objectToChartData(stats.keywordCounts).sort((a, b) => b.value - a.value);

  keywordChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 20, top: 32, bottom: 86 },
    xAxis: {
      type: "category",
      data: keywordData.map((item) => item.name),
      axisLabel: { interval: 0, rotate: 28 },
    },
    yAxis: { type: "value", minInterval: 1 },
    color: ["#17a36b"],
    series: [
      {
        name: "关键词数量",
        type: "bar",
        data: keywordData.map((item) => item.value),
        barMaxWidth: 40,
      },
    ],
  });

  window.addEventListener("resize", () => {
    sentimentChart.resize();
    platformChart.resize();
    keywordChart.resize();
  });
}

function showLoadError(error) {
  console.error(error);

  setText("totalReviews", "读取失败");
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
