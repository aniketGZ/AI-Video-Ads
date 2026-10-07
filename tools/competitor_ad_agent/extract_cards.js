() => {
  // Pass this whole file as the `function` argument of browser_evaluate on a
  // Meta Ad Library results page. Anchors on visible text ("Library ID"),
  // never on Facebook's obfuscated class names. Returns one record per card
  // currently rendered; call again after scrolling and de-dupe by library_id.
  const ID_RE = /Library ID:?\s*(\d+)/;
  const countIds = el => (el.innerText.match(/Library ID:?\s*\d+/g) || []).length;
  const clean = s => s.replace(/[​ ]/g, ' ').trim();
  const leaves = [...document.querySelectorAll('span, div')]
    .filter(e => e.childElementCount === 0 && ID_RE.test(e.textContent.trim()));

  const months = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };
  const parseDate = s => {
    if (!s) return null;
    let m = s.match(/(\d{1,2}) (\w{3})\w* (\d{4})/);              // 28 Apr 2026
    if (m) return new Date(+m[3], months[m[2].toLowerCase()], +m[1]);
    m = s.match(/(\w{3})\w* (\d{1,2}),? (\d{4})/);                 // Apr 28, 2026
    if (m) return new Date(+m[3], months[m[1].toLowerCase()], +m[2]);
    return null;
  };

  const seen = new Set();
  const out = [];
  for (const leaf of leaves) {
    let card = leaf;
    while (card.parentElement && countIds(card.parentElement) === 1) card = card.parentElement;
    const text = card.innerText;
    const library_id = (text.match(ID_RE) || [])[1];
    if (!library_id || seen.has(library_id)) continue;
    seen.add(library_id);

    const lines = text.split('\n').map(clean).filter(Boolean);
    const startedRaw = (text.match(/Started running on ([^\n·]+)/) || [])[1] || null;
    const started = parseDate(startedRaw);
    const days_running = started ? Math.max(0, Math.round((Date.now() - started) / 86400000)) : null;
    const versionsMatch = text.match(/(\d+) ads use this creative and text/);
    const versions_count = versionsMatch ? +versionsMatch[1] : (/multiple versions/i.test(text) ? 'multiple' : 1);

    // Body = everything after "Sponsored" (advertiser line sits just before it).
    const sIdx = lines.findIndex(l => l === 'Sponsored');
    const page_name = sIdx > 0 ? lines[sIdx - 1] : null;
    let body = sIdx >= 0 ? lines.slice(sIdx + 1) : [];
    body = body.filter(l => !/^\d+:\d{2} \/ \d+:\d{2}$/.test(l)); // video timer
    const CTAS = /^(Shop now|Learn more|Sign up|Order now|Buy now|Book now|Download|Install now|Get offer|Get quote|Contact us|Send message|Subscribe|Apply now|Watch more|Send WhatsApp message|Call now|See menu|Get directions|Play game|Use app|Listen now|Donate now|Request time|Get started)$/i;
    const cta_button = body.length && CTAS.test(body[body.length - 1]) ? body.pop() : null;
    const domIdx = body.findIndex(l => /^[A-Z0-9-]+(\.[A-Z0-9-]+)+(\/\S*)?$/.test(l));
    const landing_domain = domIdx >= 0 ? body[domIdx].toLowerCase() : null;
    const primary_text = (domIdx >= 0 ? body.slice(0, domIdx) : body).join('\n') || null;
    const after = domIdx >= 0 ? body.slice(domIdx + 1) : [];
    const headline = after[0] || null;
    const link_description = after.slice(1).join(' ') || null;

    const videos = [...card.querySelectorAll('video')].map(v => ({
      src: v.currentSrc || v.src || null,
      poster: v.poster || null,
      duration_s: isFinite(v.duration) ? Math.round(v.duration) : null,
    }));
    // Skip the advertiser avatar (small, ~60px) — keep creative-sized images.
    const images = [...card.querySelectorAll('img')]
      .filter(i => (i.naturalWidth || i.width) >= 150)
      .map(i => i.currentSrc || i.src)
      .filter(src => src && !videos.some(v => v.poster === src));
    const isCarousel = images.length > 1 && !videos.length;

    const platformIcons = (() => {
      const lbl = [...card.querySelectorAll('span, div')].find(e => e.childElementCount === 0 && e.textContent.trim() === 'Platforms');
      if (!lbl) return null;
      const row = lbl.parentElement && lbl.parentElement.parentElement;
      return row ? row.querySelectorAll('[style*="mask-image"]').length : null;
    })();

    out.push({
      library_id,
      status: /\bActive\b/.test(lines.slice(0, 4).join(' ')) ? 'active' : 'inactive',
      started_running: startedRaw,
      days_running,
      platforms: platformIcons !== null ? `${platformIcons} platform icon(s) — names not exposed as text` : null,
      versions_count,
      format: videos.length ? 'video' : (isCarousel ? 'carousel' : (images.length ? 'image' : 'unknown')),
      page_name,
      // "<creator> with <Brand>" = partnership / creator (UGC) ad
      is_partnership: !!(page_name && / with /.test(page_name)),
      primary_text,
      headline,
      link_description,
      cta_button,
      landing_domain,
      image_urls: images,
      video_urls: videos,
      has_see_ad_details: /See (ad|summary) details/.test(text),
    });
  }
  return { url: location.href, card_count: out.length, cards: out };
}
