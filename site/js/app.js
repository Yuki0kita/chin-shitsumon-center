/* 日本珍質問センター フィード描画（会話吹き出し版） */

const FEATURED_THRESHOLD = 40;
const FEATURED_COUNT = 8;
const PAGE_SIZE = 30;
const SNIPPET_LEN = 60;

const state = {
  items: [],
  house: "",
  shown: 0,
};

/** 件名の定型末尾を外して「お題」にする */
function titleCore(title) {
  const core = title.replace(/(等)?に(関|係)する(再)?質問主意書$/, "");
  return core || title;
}

/** 議員側の吹き出し文 */
function questionLine(item) {
  return `${titleCore(item.title)}について、教えてください！`;
}

/** 政府側の吹き出し文 */
function answerLine(item) {
  if (item.reply) return item.reply;
  if (item.a_excerpt) {
    return item.a_excerpt.length > SNIPPET_LEN
      ? item.a_excerpt.slice(0, SNIPPET_LEN) + "…"
      : item.a_excerpt;
  }
  if (item.has_answer) return "（答弁書あり。全文はリンクからどうぞ）";
  if (!item.question_url) return "（質問はまだ公開準備中）";
  return "（返事はまだ来ていません）";
}

/** チップの表示名と色クラス。色は返事の種類ごとに変える */
const CHIP_CLASSES = {
  "質問返し": "chip-dodge",
  "回答困難": "chip-dodge",
  "ノーコメント": "chip-mute",
  "未把握": "chip-mute",
  "反論": "chip-rebut",
  "予定なし": "chip-rebut",
  "検討中": "chip-forward",
  "継続": "chip-forward",
};

function replyChip(item) {
  if (item.reply_tag) {
    return { text: item.reply_tag, cls: CHIP_CLASSES[item.reply_tag] || "chip-answer" };
  }
  if (item.has_answer) return { text: "回答あり", cls: "chip-answer" };
  return { text: "返事待ち", cls: "chip-wait" };
}

function shareText(item) {
  const gov = item.reply ? `→ 政府「${item.reply}」` : "";
  return `【実在する国会質問】議員「${titleCore(item.title)}について教えて」${gov} #日本珍質問センター`;
}

function shareUrl(item) {
  const url = location.origin + location.pathname;
  return `https://x.com/intent/post?text=${encodeURIComponent(shareText(item))}&url=${encodeURIComponent(url)}`;
}

function bubbleRow({ side, face, name, text }) {
  const row = document.createElement("div");
  row.className = `chat-row ${side}`;
  const faceEl = document.createElement("span");
  faceEl.className = "chat-face";
  faceEl.textContent = face;
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";
  const nameEl = document.createElement("span");
  nameEl.className = "chat-name";
  nameEl.textContent = name;
  bubble.append(nameEl, document.createTextNode(text));
  row.append(faceEl, bubble);
  return row;
}

function renderCard(item, { withSource = false } = {}) {
  const card = document.createElement("article");
  card.className = "item-card";

  const meta = document.createElement("p");
  meta.className = "item-meta";
  const metaLeft = document.createElement("span");
  metaLeft.textContent = `第${item.session}回国会 ・ ${item.house} ・ 第${item.number}号`;
  const chipInfo = replyChip(item);
  const chip = document.createElement("span");
  chip.className = `reply-chip ${chipInfo.cls}`;
  chip.textContent = chipInfo.text;
  meta.append(metaLeft, chip);

  const name = document.createElement("h3");
  name.className = "item-name";
  name.textContent = titleCore(item.title);

  const chat = document.createElement("div");
  chat.className = "chat";
  chat.appendChild(
    bubbleRow({
      side: "giin",
      face: "議",
      name: `${item.submitter}（${item.house}）`,
      text: questionLine(item),
    })
  );
  chat.appendChild(
    bubbleRow({
      side: "gov",
      face: "政",
      name: "政府",
      text: answerLine(item),
    })
  );

  card.append(meta, name, chat);

  if (withSource && (item.q_excerpt || item.a_excerpt)) {
    const details = document.createElement("details");
    details.className = "item-source";
    const summary = document.createElement("summary");
    summary.textContent = "原文を読む（抜粋）";
    details.appendChild(summary);
    const dl = document.createElement("dl");
    if (item.q_excerpt) {
      const dt = document.createElement("dt");
      dt.textContent = "質問（原文抜粋）";
      const dd = document.createElement("dd");
      dd.textContent = item.q_excerpt;
      dl.append(dt, dd);
    }
    if (item.a_excerpt) {
      const dt = document.createElement("dt");
      dt.textContent = "政府答弁（原文抜粋）";
      const dd = document.createElement("dd");
      dd.textContent = item.a_excerpt;
      dl.append(dt, dd);
    }
    details.appendChild(dl);
    card.appendChild(details);
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
  featured.forEach((i) => list.appendChild(renderCard(i, { withSource: true })));
}

function renderLatest({ reset = false } = {}) {
  const list = document.getElementById("latest-list");
  if (reset) {
    list.textContent = "";
    state.shown = 0;
  }
  const items = filteredItems();
  const next = items.slice(state.shown, state.shown + PAGE_SIZE);
  next.forEach((i) => list.appendChild(renderCard(i, { withSource: true })));
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
