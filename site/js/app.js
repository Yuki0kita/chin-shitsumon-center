/* 日本珍質問センター フィード描画 */

const FEATURED_THRESHOLD = 40;
const FEATURED_COUNT = 8;
const PAGE_SIZE = 30;

const state = {
  items: [],
  house: "",
  shown: 0,
};

/** 官製の乾いた文体で1件分の本文を組み立てる */
function officialSentence(item) {
  let text = `第${item.session}回国会に、${item.house}議員・${item.submitter}から「${item.title}」が提出されました。`;
  if (item.has_answer) {
    text += "政府の答弁書は受領済みです。";
  } else if (!item.question_url) {
    text += "質問本文は掲載準備中です。";
  } else {
    text += "政府の答弁書は未受領です。";
  }
  return text;
}

function shareText(item) {
  return `【質問主意書】第${item.session}回国会・${item.house}「${item.title}」（提出: ${item.submitter}） #日本珍質問センター`;
}

function shareUrl(item) {
  const url = location.origin + location.pathname;
  return `https://x.com/intent/post?text=${encodeURIComponent(shareText(item))}&url=${encodeURIComponent(url)}`;
}

function renderCard(item, { withExcerpt = false } = {}) {
  const card = document.createElement("article");
  card.className = "item-card";

  const meta = document.createElement("p");
  meta.className = "item-meta";
  const metaLeft = document.createElement("span");
  metaLeft.textContent = `第${item.session}回国会 ・ ${item.house} ・ 第${item.number}号`;
  const status = document.createElement("span");
  status.className = "item-status";
  status.textContent = item.has_answer ? "答弁受領" : "答弁待ち";
  meta.append(metaLeft, status);

  const name = document.createElement("h3");
  name.className = "item-name";
  name.textContent = item.title;

  const body = document.createElement("p");
  body.className = "item-body";
  body.textContent = officialSentence(item);

  card.append(meta, name, body);

  if (withExcerpt && (item.q_excerpt || item.a_excerpt)) {
    const dl = document.createElement("dl");
    dl.className = "item-excerpt";
    if (item.q_excerpt) {
      const dt = document.createElement("dt");
      dt.textContent = "質問（抜粋）";
      const dd = document.createElement("dd");
      dd.textContent = item.q_excerpt;
      dl.append(dt, dd);
    }
    if (item.a_excerpt) {
      const dt = document.createElement("dt");
      dt.textContent = "政府答弁（抜粋）";
      const dd = document.createElement("dd");
      dd.textContent = item.a_excerpt;
      dl.append(dt, dd);
    }
    card.appendChild(dl);
  }

  const actions = document.createElement("div");
  actions.className = "item-actions";
  if (item.question_url) {
    const q = document.createElement("a");
    q.href = item.question_url;
    q.target = "_blank";
    q.rel = "noopener";
    q.textContent = "質問全文";
    actions.appendChild(q);
  }
  if (item.answer_url) {
    const a = document.createElement("a");
    a.href = item.answer_url;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = "答弁全文";
    actions.appendChild(a);
  }
  const share = document.createElement("a");
  share.href = shareUrl(item);
  share.target = "_blank";
  share.rel = "noopener";
  share.textContent = "Xで共有";
  actions.appendChild(share);

  card.appendChild(actions);
  return card;
}

function filteredItems() {
  return state.house
    ? state.items.filter((i) => i.house === state.house)
    : state.items;
}

function renderFeatured() {
  const list = document.getElementById("featured-list");
  list.textContent = "";
  const featured = state.items
    .filter((i) => i.score >= FEATURED_THRESHOLD)
    .slice(0, FEATURED_COUNT);
  if (featured.length === 0) {
    list.innerHTML = '<p class="empty-state">現在、注目の質問はありません。</p>';
    return;
  }
  featured.forEach((i) => list.appendChild(renderCard(i, { withExcerpt: true })));
}

function renderLatest({ reset = false } = {}) {
  const list = document.getElementById("latest-list");
  if (reset) {
    list.textContent = "";
    state.shown = 0;
  }
  const items = filteredItems();
  const next = items.slice(state.shown, state.shown + PAGE_SIZE);
  next.forEach((i) => list.appendChild(renderCard(i)));
  state.shown += next.length;

  if (items.length === 0) {
    list.innerHTML = '<p class="empty-state">該当する質問はありません。</p>';
  }
  document.getElementById("load-more").hidden = state.shown >= items.length;
}

async function main() {
  let payload;
  try {
    const res = await fetch("data/items.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    payload = await res.json();
  } catch (err) {
    console.error("データの読み込みに失敗しました", err);
    document.getElementById("featured-list").innerHTML =
      '<p class="empty-state">データの読み込みに失敗しました。時間をおいて再度お試しください。</p>';
    document.getElementById("latest-list").textContent = "";
    return;
  }

  state.items = payload.items || [];
  const updated = document.getElementById("updated-at");
  if (payload.updated_at) {
    updated.textContent = `最終更新: ${new Date(payload.updated_at).toLocaleString("ja-JP")}`;
  }
  const select = document.getElementById("house-select");
  select.addEventListener("change", () => {
    state.house = select.value;
    renderLatest({ reset: true });
  });
  renderFeatured();
  renderLatest({ reset: true });
  document.getElementById("load-more").addEventListener("click", () => renderLatest());
}

main();
