/* OMIM draft review page. Vanilla JS, no dependencies.
   All data comes from the JSON block #report-data; every string from it is inserted with
   textContent / setAttribute through h(), never as HTML. */
(function () {
  'use strict';

  // ------------------------------------------------------------------ data
  let DATA;
  try { DATA = JSON.parse(document.getElementById('report-data').textContent || '{}'); }
  catch (e) { DATA = {}; }
  const ENTRIES = Array.isArray(DATA.entries) ? DATA.entries : [];
  const RUN = String(DATA.run || 'run');

  const STRATEGY = {
    kg: { label: 'Evidence-graph draft', short: 'Evidence graph',
      about: 'Facts were first extracted from each paper together with verbatim supporting quotes, then the entry was written from those facts.' },
    direct: { label: 'Direct draft (baseline)', short: 'Direct (baseline)',
      about: 'The model wrote the entry straight from the paper text, without the fact-extraction step. Kept as a baseline for comparison.' },
  };
  const stratLabel = (s) => (STRATEGY[s] ? STRATEGY[s].label : 'Draft “' + s + '”');
  const stratShort = (s) => (STRATEGY[s] ? STRATEGY[s].short : s);

  const STATUS = {
    flagged: { cls: 'bad', icon: '✗', label: 'Flagged', help: 'At least one claim was found unsupported or contradicted by the cited paper.' },
    partial: { cls: 'warn', icon: '~', label: 'Partly supported', help: 'At least one claim is only partly supported by the cited paper.' },
    supported: { cls: 'ok', icon: '✓', label: 'Supported', help: 'Every audited claim is supported by the cited paper.' },
    unverified: { cls: 'none', icon: '○', label: 'Not audited', help: 'The audit did not check this paragraph.' },
  };
  const VERDICT = {
    supported: { cls: 'ok', icon: '✓', label: 'Supported' },
    partially_supported: { cls: 'warn', icon: '~', label: 'Partly supported' },
    unsupported: { cls: 'bad', icon: '✗', label: 'Not supported' },
    contradicted: { cls: 'bad', icon: '⚠', label: 'Contradicted' },
    not_checkable: { cls: 'none', icon: '?', label: 'Could not check' },
  };
  const FACT = {
    present: { cls: 'ok', icon: '✓', label: 'Present' },
    partial: { cls: 'warn', icon: '~', label: 'Partial' },
    absent: { cls: 'none', icon: '–', label: 'Absent' },
    contradicted: { cls: 'bad', icon: '✗', label: 'Contradicted' },
  };
  const LEVEL = {
    fulltext: { label: 'Full text read', short: 'full text', cls: 'ok' },
    abstract: { label: 'Abstract only', short: 'abstract', cls: 'warn' },
    title: { label: 'Title only', short: 'title', cls: 'bad' },
    not_retrieved: { label: 'Not retrieved', short: 'not retrieved', cls: 'none' },
  };
  const DECISION = {
    accept: { label: 'Accept', cls: 'ok', icon: '✓', btn: 'd-accept' },
    edit: { label: 'Needs edit', cls: 'warn', icon: '✎', btn: 'd-edit' },
    reject: { label: 'Reject', cls: 'bad', icon: '✗', btn: 'd-reject' },
  };
  const INHERITANCE = {
    AD: 'Autosomal dominant', AR: 'Autosomal recessive', XL: 'X-linked', XLD: 'X-linked dominant',
    XLR: 'X-linked recessive', YL: 'Y-linked', MT: 'Mitochondrial', DIGENIC: 'Digenic',
    SEMIDOMINANT: 'Semidominant', MULTIFACTORIAL: 'Multifactorial', SOMATIC: 'Somatic mutation',
    SOMATIC_MOSAIC: 'Somatic mosaicism', UNKNOWN: 'Unknown',
  };
  const SECTION_HEADINGS = {
    description: 'Description', nomenclature: 'Nomenclature', cloning_expression: 'Cloning and Expression',
    gene_structure: 'Gene Structure', clinical_features: 'Clinical Features', other_features: 'Other Features',
    biochemical_features: 'Biochemical Features', inheritance: 'Inheritance', cytogenetics: 'Cytogenetics',
    mapping: 'Mapping', heterogeneity: 'Heterogeneity', gene_function: 'Gene Function',
    molecular_genetics: 'Molecular Genetics', genotype_phenotype_correlations: 'Genotype/Phenotype Correlations',
    pathogenesis: 'Pathogenesis', diagnosis: 'Diagnosis', clinical_management: 'Clinical Management',
    population_genetics: 'Population Genetics', evolution: 'Evolution', animal_model: 'Animal Model', history: 'History',
    intro: 'Text',
  };
  const RELEVANCE = { primary: 'Primary', supporting: 'Supporting', background: 'Background', not_relevant: 'Not relevant' };

  // Headline metrics. `help` is the plain-language definition shown in the legend and as a tooltip.
  const METRICS = [
    { key: 'claim_supported_rate', label: 'Claims supported', fmt: 'pct', better: 'high',
      help: 'Share of the draft’s individual claims that the audit found fully supported by the paper cited for them. Needs no OMIM entry, so it is available for new entries too.' },
    { key: 'claim_error_rate', label: 'Claim errors', fmt: 'pct', better: 'low',
      help: 'Share of claims the audit found not supported or contradicted by the cited paper. Lower is better; these are the paragraphs to check first.' },
    { key: 'gold_fact_coverage', label: 'OMIM-fact coverage', fmt: 'pct', better: 'high',
      help: 'OMIM’s own per-paper paragraphs (as OMIM deposited them in ClinVar) are split into single facts, and each is looked for in the draft text citing the same paper. Present counts 1, partial counts ½.' },
    { key: 'gold_fact_contradicted', label: 'Facts contradicted', fmt: 'int', better: 'low',
      help: 'Number of OMIM facts that the draft states in a way incompatible with OMIM’s text.' },
    { key: 'hpo_exact_f1', label: 'Synopsis F1 (exact)', fmt: 'f1', better: 'high',
      help: 'Agreement between the draft’s clinical-synopsis HPO terms and HPO’s annotations of the OMIM entry, counting only identical terms. F1 weighs missed and extra terms equally; 1.00 is perfect agreement, 0 none.' },
    { key: 'hpo_hier_f1', label: 'Synopsis F1 (hierarchical)', fmt: 'f1', better: 'high',
      help: 'As the exact score, but every term also counts for its broader parent terms, so “optic atrophy” earns partial credit against “abnormality of the optic nerve”. Forgives choosing a more or less specific term.' },
    { key: 'variant_recall', label: 'Variant recall', fmt: 'pct', better: 'high',
      help: 'Share of OMIM’s allelic variants for this entry that the draft also lists (matched on nucleotide or protein change).' },
    { key: 'gene_f1', label: 'Gene F1', fmt: 'f1', better: 'high',
      help: 'Agreement between the causal genes in the draft’s phenotype–gene table and OMIM’s gene–phenotype links.' },
    { key: 'inheritance_match', label: 'Inheritance', fmt: 'match', better: 'high',
      help: 'Whether the draft’s mode of inheritance matches OMIM’s. X-linked dominant and recessive count as the same.' },
    { key: 'ref_recall', label: 'Reference recall', fmt: 'pct', better: 'high',
      help: 'Share of OMIM’s references for this entry that the draft cites.' },
  ];
  const ACCESS_HELP = 'Of OMIM’s references for this entry, how many papers could be read as full text, as abstract only, or by title only (or were not retrieved at all). Scores are limited by what could be read.';

  // ------------------------------------------------------------------ helpers
  function h(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        const v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'text') el.textContent = String(v);
        else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
        else if (k === 'value') el.value = v;
        else el.setAttribute(k, v === true ? '' : String(v));
      }
    }
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, kid) {
    if (kid === null || kid === undefined || kid === false) return;
    if (Array.isArray(kid)) { kid.forEach((k) => add(el, k)); return; }
    el.append(kid instanceof Node ? kid : String(kid));
  }
  const $ = (sel, root) => (root || document).querySelector(sel);
  function get(obj, path) {
    let node = obj;
    for (const k of path.split('.')) { if (node === null || node === undefined || typeof node !== 'object') return null; node = node[k]; }
    return node === undefined ? null : node;
  }
  const isNum = (v) => typeof v === 'number' && isFinite(v);
  function fmt(v, kind) {
    if (kind === 'match') {
      if (v === null || v === undefined) return '–';
      if (typeof v === 'boolean') return v ? 'Match' : 'Mismatch';
      return isNum(v) ? Math.round(v * 100) + '% match' : '–';
    }
    if (!isNum(v)) return '–';
    if (kind === 'pct') return (Math.round(v * 1000) / 10).toFixed(v === 1 || v === 0 ? 0 : 1).replace(/\.0$/, '') + '%';
    if (kind === 'f1') return v.toFixed(2);
    if (kind === 'int') return String(Math.round(v));
    return String(v);
  }
  const plural = (n, one, many) => n + ' ' + (n === 1 ? one : (many || one + 's'));
  const humanize = (s) => String(s || '').replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

  function chip(def, extraTitle) {
    if (!def) return null;
    return h('span', { class: 'chip ' + def.cls, title: extraTitle || def.help || null },
      h('span', { class: 'ic', 'aria-hidden': 'true' }, def.icon || ''), def.label);
  }
  function plainChip(text, cls, title) { return h('span', { class: 'chip ' + (cls || 'plain'), title: title || null }, text); }
  function ext(href, text, title) {
    return h('a', { href: href, target: '_blank', rel: 'noopener noreferrer', title: title || null }, text);
  }
  const pubmedUrl = (pmid) => 'https://pubmed.ncbi.nlm.nih.gov/' + encodeURIComponent(pmid) + '/';
  const hpoUrl = (id) => 'https://hpo.jax.org/browse/term/' + encodeURIComponent(id);
  const omimUrl = (mim) => 'https://omim.org/entry/' + encodeURIComponent(mim);
  const hpoLink = (id) => (id ? ext(hpoUrl(id), id, 'Open ' + id + ' on the HPO website') : null);
  function levelChip(level) {
    const d = LEVEL[level];
    if (!d) return null;
    return h('span', { class: 'chip ' + d.cls, title: 'How much of the paper could be read: ' + d.label.toLowerCase() }, d.label);
  }

  // ------------------------------------------------------------------ entries: index now, data on demand
  // DATA.entries is a small index (scores, paragraph ids). Each entry's full data either sits in
  // DATA.payloads (single-file page) or in report_data/<file>.js, which calls __aiomimRegister.
  const DATA_DIR = String(DATA.data_dir || 'report_data');
  const usedKeys = new Set();
  const byKey = new Map();
  const byFile = new Map();
  for (const item of ENTRIES) {
    item.strategies = Array.isArray(item.strategies) ? item.strategies : [];
    item.pids = item.pids || {};
    item.rows = item.rows || {};
    let key = String(item.dir || item.mim || 'entry').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'entry';
    const base = key; let n = 2;
    while (usedKeys.has(key)) key = base + '-' + n++;
    usedKeys.add(key); item.key = key; byKey.set(key, item);
    if (item.file) byFile.set(item.file, item);
    item.loaded = false;
    item.entries = {}; item.evals = {}; item.papers = []; item.extractions = [];
    item.paperBy = new Map(); item.findingBy = new Map(); item.extractionBy = new Map(); item.refBy = new Map();
    item.goldHpo = null;
  }
  function attach(item, payload) {
    Object.assign(item, payload);
    item.entries = item.entries || {};
    item.evals = item.evals || {};
    item.papers = item.papers || [];
    item.extractions = item.extractions || [];
    for (const p of item.papers) item.paperBy.set(String(p.pmid), p);
    for (const ex of item.extractions) {
      item.extractionBy.set(String(ex.pmid), ex);
      for (const f of ex.findings || []) item.findingBy.set(f.id, f);
    }
    if (item.gold && Array.isArray(item.gold.hpo_annotations)) {
      item.goldHpo = new Set(item.gold.hpo_annotations
        .filter((a) => (a.aspect || 'P') === 'P' && String(a.qualifier || '').toUpperCase() !== 'NOT')
        .map((a) => a.hpo_id));
    }
    for (const s of item.strategies) for (const r of get(item, 'entries.' + s + '.references') || []) item.refBy.set(String(r.pmid), r);
    item.loaded = true;
    item.loadError = null;
  }
  window.__aiomimRegister = function (file, payload) {
    const item = byFile.get(String(file));
    if (item && !item.loaded && payload && typeof payload === 'object') attach(item, payload);
  };
  if (DATA.payloads) for (const f of Object.keys(DATA.payloads)) window.__aiomimRegister(f, DATA.payloads[f]);
  delete DATA.payloads;

  const pending = new Map();
  function loadEntry(item) {
    if (item.loaded) return Promise.resolve(item);
    if (pending.has(item.key)) return pending.get(item.key);
    const pr = new Promise((resolve, reject) => {
      if (!item.file) { reject(new Error('This entry has no data file.')); return; }
      const el = document.createElement('script');
      el.src = DATA_DIR + '/' + encodeURIComponent(item.file);
      el.async = true;
      el.onload = () => { el.remove(); if (item.loaded) resolve(item); else reject(new Error('The data file ' + DATA_DIR + '/' + item.file + ' loaded but contained no entry data.')); };
      el.onerror = () => { el.remove(); reject(new Error('The data file ' + DATA_DIR + '/' + item.file + ' could not be loaded.')); };
      document.head.append(el);
    });
    pending.set(item.key, pr);
    pr.then(() => pending.delete(item.key), (e) => { pending.delete(item.key); item.loadError = e.message; });
    return pr;
  }
  const HAS_UPDATES = ENTRIES.some((it) => it.has_updates);

  function paperLabel(item, pmid) {
    const p = item.paperBy.get(String(pmid));
    if (p && p.label) return p.label;
    const r = item.refBy.get(String(pmid));
    if (r && r.label) return r.label;
    return 'PMID ' + pmid;
  }
  function paperLevel(item, pmid) {
    const p = item.paperBy.get(String(pmid));
    if (p && p.content_level) return p.content_level;
    const r = item.refBy.get(String(pmid));
    return r ? r.content_level : null;
  }
  function citeLinks(item, pmids) {
    const out = [];
    (pmids || []).forEach((pmid, i) => {
      if (i) out.push('; ');
      out.push(ext(pubmedUrl(pmid), paperLabel(item, pmid), 'PubMed ' + pmid));
    });
    return out;
  }
  function entryNumber(item, entry) {
    const mim = (entry && entry.mim) || item.mim;
    const prefix = (entry && entry.prefix) || item.prefix || get(item, 'gold.prefix') || get(item, 'seed.prefix') || '';
    return { mim: mim, prefix: prefix };
  }
  function itemName(item) {
    return (item.mim ? item.mim + ' ' : '') + (item.title || item.dir);
  }

  function paragraphsOf(entry) {
    const out = [];
    if (!entry) return out;
    if (entry.intro) out.push({ p: entry.intro, where: 'Text (introduction)', section: 'intro' });
    for (const s of entry.sections || []) for (const p of s.paragraphs || []) out.push({ p: p, where: s.heading || SECTION_HEADINGS[s.name] || humanize(s.name), section: s.name });
    for (const av of entry.allelic_variants || []) for (const p of av.paragraphs || []) out.push({ p: p, where: 'Allelic variant .' + String(av.number || 0).padStart(4, '0') + ' ' + (av.name || ''), section: 'allelic_variant' });
    return out;
  }
  function pidOf(p, i) { return p.id || ('p' + i); }

  // ------------------------------------------------------------------ decisions (localStorage, optional)
  const STORE = 'aiomim-review';
  let storageOk = true;
  try { const t = STORE + '|probe'; window.localStorage.setItem(t, '1'); window.localStorage.removeItem(t); }
  catch (e) { storageOk = false; }
  const decisions = new Map();
  const dkey = (item, s, pid) => [STORE, RUN, item.dir, s, pid].join('|');
  function loadDecisions() {
    if (!storageOk) return;
    for (const item of ENTRIES) for (const s of item.strategies) {
      for (const pid of item.pids[s] || []) {
        const k = dkey(item, s, pid);
        try { const v = window.localStorage.getItem(k); if (v) decisions.set(k, JSON.parse(v)); } catch (e) { /* ignore */ }
      }
    }
  }
  function getDecision(item, s, pid) { return decisions.get(dkey(item, s, pid)) || null; }
  function setDecision(item, s, pid, patch) {
    const k = dkey(item, s, pid);
    const rec = Object.assign({}, decisions.get(k) || {}, patch, { updated: new Date().toISOString() });
    const empty = !rec.decision && !rec.comment && !rec.edited;
    if (empty) decisions.delete(k); else decisions.set(k, rec);
    try {
      if (empty) window.localStorage.removeItem(k); else window.localStorage.setItem(k, JSON.stringify(rec));
    } catch (e) {
      if (storageOk) { storageOk = false; toast('This browser is not saving decisions. Export your review before closing the page.'); }
    }
    return rec;
  }
  function progressOf(item, s) {
    const pids = item.pids[s] || [];
    let done = 0;
    pids.forEach((pid) => { const d = getDecision(item, s, pid); if (d && d.decision) done++; });
    return { done: done, total: pids.length };
  }
  function progressEl(item, s) {
    const pr = progressOf(item, s);
    const pct = pr.total ? Math.round(100 * pr.done / pr.total) : 0;
    return h('span', { class: 'progress', 'data-progress': item.key + '|' + s },
      h('span', { class: 'progress-bar', 'aria-hidden': 'true' }, h('span', { style: 'width:' + pct + '%' })),
      h('span', { class: 'num' }, pr.done + ' of ' + pr.total + ' reviewed'));
  }
  function refreshProgress() {
    document.querySelectorAll('[data-progress]').forEach((el) => {
      const parts = el.getAttribute('data-progress').split('|');
      const item = byKey.get(parts[0]);
      if (item) el.replaceWith(progressEl(item, parts[1]));
    });
  }

  // ------------------------------------------------------------------ state + routing
  const state = {
    overviewStrategy: (DATA.strategies && DATA.strategies[0]) || 'kg',
    selected: null,          // `${key}|${strategy}|${pid}`
    attentionOnly: false,
    hideReviewed: false,
    exportBox: null,
    lastRouteId: null,
  };
  const wide = window.matchMedia ? window.matchMedia('(min-width: 1100px)') : { matches: true };

  function parseHash() {
    let raw = '';
    try { raw = decodeURIComponent(location.hash.replace(/^#/, '')); } catch (e) { raw = ''; }
    if (!raw || raw === 'overview' || raw === 'main') return { view: 'overview' };
    if (raw === 'updates') return { view: 'updates' };
    if (raw.indexOf('entry-') === 0) {
      const parts = raw.slice(6).split('--');
      const item = byKey.get(parts[0]);
      if (!item) return { view: 'missing' };
      let strategy = parts[2] && item.strategies.indexOf(parts[2]) >= 0 ? parts[2] : (item.strategies[0] || null);
      let tab = ['review', 'gold', 'evidence', 'updates'].indexOf(parts[1]) >= 0 ? parts[1] : 'review';
      if (tab === 'review' && !strategy && item.has_updates) tab = 'updates';
      return { view: 'entry', item: item, tab: tab, strategy: strategy };
    }
    return { view: 'overview' };
  }
  function entryHash(item, tab, strategy) {
    let out = 'entry-' + item.key;
    const s = strategy && strategy !== item.strategies[0] ? strategy : null;
    if ((tab && tab !== 'review') || s) out += '--' + (tab || 'review');
    if (s) out += '--' + s;
    return '#' + out;
  }

  let toastTimer = null;
  function toast(msg) {
    const el = $('#toast');
    if (!el) return;
    el.textContent = msg; el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
  }

  function render(opts) {
    opts = opts || {};
    const route = parseHash();
    const main = $('#main');
    const active = document.activeElement;
    const focusId = active && active.getAttribute ? active.getAttribute('data-fid') : null;
    const y = window.scrollY;
    let view;
    if (route.view === 'entry') view = viewEntry(route);
    else if (route.view === 'updates') view = viewAllUpdates();
    else if (route.view === 'missing') view = h('div', { class: 'wrap' }, h('div', { class: 'empty' }, h('strong', null, 'This link points to an entry that is not in this run. '), h('a', { href: '#overview' }, 'Go to the run overview.')));
    else view = viewOverview();
    main.replaceChildren(view);
    updateNav(route);
    const routeId = route.view + '|' + (route.item ? route.item.key : '') + '|' + (route.tab || '');
    if (opts.keepScroll) window.scrollTo(0, y);
    else if (routeId !== state.lastRouteId) { window.scrollTo(0, 0); main.focus({ preventScroll: true }); }
    state.lastRouteId = routeId;
    const want = opts.focus || focusId;
    if (want) {
      const el = document.querySelector('[data-fid="' + CSS.escape(want) + '"]');
      if (el) el.focus({ preventScroll: true });
    }
  }

  function updateNav(route) {
    document.querySelectorAll('[data-nav]').forEach((a) => {
      if (a.getAttribute('data-nav') === route.view) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    const sel = $('#entry-jump');
    if (sel) sel.value = route.view === 'entry' ? route.item.key : '';
    const upd = $('#nav-updates');
    if (upd) upd.hidden = !HAS_UPDATES;
  }

  function buildJump() {
    const sel = $('#entry-jump');
    if (!sel) return;
    sel.replaceChildren(h('option', { value: '' }, ENTRIES.length ? 'Open an entry…' : 'No entries in this run'));
    for (const item of ENTRIES) sel.append(h('option', { value: item.key }, itemName(item)));
    sel.addEventListener('change', () => {
      const item = byKey.get(sel.value);
      if (item) location.hash = entryHash(item);
    });
  }

  // ------------------------------------------------------------------ scores
  function rowFor(item, s) {
    // Rows are computed at build time so the overview needs no entry data.
    const r = item.rows[s] || {};
    const out = { has: item.strategies.indexOf(s) >= 0, hasEval: !!r.has_eval };
    for (const k of Object.keys(r)) out[k] = r[k] === undefined ? null : r[k];
    for (const m of METRICS) if (!(m.key in out)) out[m.key] = null;
    return out;
  }
  function meanRow(rows) {
    const out = {};
    for (const m of METRICS) {
      const vals = rows.map((r) => r[m.key]).filter((v) => v !== null && v !== undefined)
        .map((v) => (typeof v === 'boolean' ? (v ? 1 : 0) : v)).filter(isNum);
      if (m.key === 'gold_fact_contradicted') out[m.key] = vals.length ? vals.reduce((a, b) => a + b, 0) : null;
      else out[m.key] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    }
    return out;
  }
  function accessEl(access) {
    if (!access) return '–';
    const order = ['fulltext', 'abstract', 'title', 'not_retrieved'];
    const parts = order.filter((k) => access[k]).map((k) => h('span', { title: LEVEL[k].label }, access[k] + ' ' + LEVEL[k].short));
    return parts.length ? h('span', { class: 'access' }, parts) : '–';
  }
  function legend(open) {
    return h('details', { class: 'legend', open: open || null },
      h('summary', null, 'What the scores mean'),
      h('dl', null,
        METRICS.map((m) => [h('dt', null, m.label), h('dd', null, m.help)]),
        h('dt', null, 'OMIM references readable'), h('dd', null, ACCESS_HELP),
        h('dt', null, 'Paragraph marks'),
        h('dd', null, ['flagged', 'partial', 'supported', 'unverified'].map((k) => h('div', null, chip(STATUS[k]), ' ', STATUS[k].help))),
        h('dt', null, '“–”'), h('dd', null, 'No value: the score could not be computed, for example because there is no OMIM entry to compare with or OMIM lists nothing of that kind.')));
  }
  function headerCell(m) { return h('th', { class: 'n', scope: 'col' }, h('abbr', { title: m.help }, m.label)); }

  // ------------------------------------------------------------------ overview
  function viewOverview() {
    const wrap = h('div', { class: 'wrap' });
    const strategies = DATA.strategies || [];
    const n = ENTRIES.length;
    const dates = DATA.generated || [];
    const retrieval = DATA.retrieval === 'oracle'
      ? 'from the papers each OMIM entry already cites'
      : DATA.retrieval === 'open' ? 'from papers chosen by a literature search' : 'from the published literature';
    const how = strategies.length > 1
      ? 'Each entry was written ' + strategies.length + ' ways (' + strategies.map(stratLabel).join(' and ') + ') so the two can be compared.'
      : strategies.length === 1 ? 'Each entry was written as an ' + stratLabel(strategies[0]).replace(/^Direct/, 'direct').replace(/^Evidence/, 'evidence') + '.' : '';
    const when = dates.length ? ' Drafted ' + (dates.length > 1 ? dates[0] + ' to ' + dates[dates.length - 1] : dates[0]) + '.' : '';
    wrap.append(h('div', { class: 'page-head' },
      h('div', { class: 'eyebrow' }, 'Run “' + RUN + '”'),
      h('h1', { class: 'page-title' }, 'Review of ' + plural(n, 'machine-drafted entry', 'machine-drafted entries')),
      h('p', { class: 'lede' }, 'This run drafted ' + plural(n, 'OMIM entry', 'OMIM entries') + ' ' + retrieval + '. ' + how + when +
        ' Every claim in a draft was then checked against the paper it cites, and drafts of existing entries were scored against the real OMIM entry.'),
      unreviewedNotice()));

    if (!n) {
      wrap.append(h('div', { class: 'empty' }, h('strong', null, 'This run has no entries yet. '),
        'Entries appear here once the pipeline has written at least one entry folder into the run directory.'));
      return wrap;
    }

    if (DATA.comparison) wrap.append(comparisonFromFile(DATA.comparison));
    else if (strategies.length > 1) wrap.append(comparisonSection(strategies));

    // score table
    const s = strategies.indexOf(state.overviewStrategy) >= 0 ? state.overviewStrategy : strategies[0];
    const sec = h('section', { class: 'section', 'aria-labelledby': 'scores-h' });
    const head = h('div', { class: 'section-head' }, h('h2', { id: 'scores-h' }, 'Scores by entry'));
    if (strategies.length > 1) head.append(strategySwitch(s, (v) => { state.overviewStrategy = v; render({ keepScroll: true, focus: 'ov-strat-' + v }); }, 'ov-strat-'));
    sec.append(head);
    if (strategies.length) sec.append(h('p', { class: 'small muted' }, 'Showing the ' + stratLabel(s).toLowerCase().replace('(baseline)', '(baseline)') + '. ' + (STRATEGY[s] ? STRATEGY[s].about : '') + ' Select an entry to review it.'));
    sec.append(scoreTable(s));
    sec.append(legend(false));
    wrap.append(sec);

    const failures = DATA.failures || {};
    const fk = Object.keys(failures);
    if (fk.length) {
      wrap.append(h('section', { class: 'section' }, h('h2', null, 'Entries that failed to run'),
        h('ul', { class: 'plain-list' }, fk.map((k) => h('li', null, h('strong', null, k + ': '), h('span', { class: 'mono' }, failures[k]))))));
    }
    wrap.append(footer());
    return wrap;
  }
  function unreviewedNotice() {
    return h('div', { class: 'notice', role: 'note' }, h('span', { class: 'notice-icon', 'aria-hidden': 'true' }, '!'),
      h('div', null, h('strong', null, 'Machine-drafted, not yet reviewed. '),
        'Every entry here was written by a language model from the cited papers. Nothing on this page has been checked by a curator; treat each paragraph as a draft until you accept it.'));
  }
  function strategySwitch(current, onPick, fidPrefix) {
    return h('div', { class: 'seg', role: 'group', 'aria-label': 'Which draft to show' },
      (DATA.strategies || []).map((s) => h('button', { type: 'button', 'aria-pressed': String(s === current), 'data-fid': fidPrefix + s, onclick: () => onPick(s) }, stratLabel(s))));
  }
  function comparisonSection(strategies) {
    const means = {};
    for (const s of strategies) means[s] = meanRow(ENTRIES.filter((it) => it.strategies.indexOf(s) >= 0).map((it) => rowFor(it, s)));
    const tbody = h('tbody');
    for (const m of METRICS) {
      const vals = strategies.map((s) => means[s][m.key]);
      const nums = vals.filter(isNum);
      let best = null;
      if (nums.length === strategies.length && nums.length > 1 && new Set(nums.map((v) => v.toFixed(4))).size > 1) best = m.better === 'low' ? Math.min.apply(null, nums) : Math.max.apply(null, nums);
      tbody.append(h('tr', null, h('th', { scope: 'row' }, h('abbr', { title: m.help }, m.label)),
        vals.map((v) => h('td', { class: 'n' + (best !== null && v === best ? ' better' : '') }, fmt(v, m.fmt)))));
    }
    return h('section', { class: 'section', 'aria-labelledby': 'cmp-h' },
      h('h2', { id: 'cmp-h' }, 'The two drafts compared'),
      h('p', { class: 'small muted' }, 'Averages over the entries of this run (facts contradicted is a total). ▲ marks the better value. ' +
        strategies.map((s) => stratLabel(s) + ': ' + (STRATEGY[s] ? STRATEGY[s].about : '')).join(' ')),
      h('div', { class: 'table-scroll compare' }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Score'), strategies.map((s) => h('th', { class: 'n', scope: 'col' }, stratLabel(s))))),
        tbody)));
  }
  function scoreTable(s) {
    const rows = ENTRIES.map((it) => ({ item: it, row: rowFor(it, s) }));
    const tbody = h('tbody');
    for (const { item, row } of rows) {
      const href = entryHash(item, 'review', item.strategies.indexOf(s) >= 0 ? s : null);
      const tr = h('tr', { class: 'clickable', onclick: (e) => { if (!e.target.closest('a')) location.hash = href; } },
        h('td', { class: 'entry-cell' },
          h('a', { href: href }, itemName(item)),
          !item.mim ? h('div', { class: 'small muted' }, 'New entry, no OMIM entry to compare with') : null,
          !row.has ? h('div', { class: 'small muted' }, 'No ' + stratLabel(s).toLowerCase() + ' for this entry') : null),
        h('td', null, item.strategies.indexOf(s) >= 0 ? progressEl(item, s) : '–'),
        METRICS.map((m) => h('td', { class: 'n' }, fmt(row[m.key], m.fmt))),
        h('td', null, accessEl(row.access)));
      tbody.append(tr);
    }
    const mean = meanRow(rows.map((r) => r.row));
    tbody.append(h('tr', { class: 'mean' }, h('td', null, 'Mean of entries with a value'), h('td', null, ''),
      METRICS.map((m) => h('td', { class: 'n' }, fmt(mean[m.key], m.fmt))), h('td', null, '')));
    return h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
      h('caption', { class: 'visually-hidden' }, 'Scores for each entry, ' + stratLabel(s)),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Entry'), h('th', { scope: 'col' }, 'Your review'),
        METRICS.map(headerCell), h('th', { scope: 'col' }, h('abbr', { title: ACCESS_HELP }, 'OMIM refs readable')))),
      tbody));
  }
  function footer() {
    const u = DATA.usage_total || {};
    const bits = [];
    if (isNum(u.calls)) bits.push(plural(u.calls, 'model call'));
    if (isNum(u.input_tokens) || isNum(u.output_tokens)) bits.push(((u.input_tokens || 0) + (u.output_tokens || 0)).toLocaleString('en-US') + ' tokens');
    if (isNum(u.list_price_usd)) bits.push('about $' + u.list_price_usd.toFixed(2) + ' at list price');
    return h('footer', { class: 'foot' },
      bits.length ? h('div', null, 'Run cost: ' + bits.join(', ') + '.') : null,
      h('div', null, 'Generated by aiomim. Your decisions are kept in this browser only' + (storageOk ? '' : ' (and this browser is not saving them)') + '; use the export buttons on each entry to keep them.'));
  }

  // ------------------------------------------------------------------ comparison.json (aiomim compare)
  const cmpKind = (metric) => (/f1/.test(metric) ? 'f1' : 'pct');
  function fmtCmp(v, kind) {
    if (!isNum(v)) return '–';
    return kind === 'f1' ? v.toFixed(2) : (100 * v).toFixed(1) + '%';
  }
  function fmtDiff(v, kind) {
    if (!isNum(v)) return '–';
    const a = Math.abs(v);
    const sign = a < 5e-5 ? '' : v > 0 ? '+' : '−';
    return kind === 'f1' ? sign + a.toFixed(2) : sign + (100 * a).toFixed(1) + ' pp';
  }
  function fmtCI(ci, kind) {
    if (!Array.isArray(ci) || ci.length !== 2) return null;
    return fmtDiff(ci[0], kind) + ' to ' + fmtDiff(ci[1], kind);
  }
  function dirMark(higher) {
    return h('span', { class: 'dir', title: higher ? 'Higher is better' : 'Lower is better' }, higher ? ' ↑' : ' ↓');
  }
  function metricLabel(r) {
    const sub = /^…/.test(r.label || '');
    return h('th', { scope: 'row', class: sub ? 'sub' : null }, (r.label || humanize(r.metric)), dirMark(r.higher_is_better !== false));
  }

  function comparisonFromFile(c) {
    const sec = h('section', { class: 'section', 'aria-labelledby': 'cmp-h' });
    const n = c.n_entries || 0;
    sec.append(h('h2', { id: 'cmp-h' }, 'The two drafts compared'));
    sec.append(h('p', { class: 'lede small' }, plural(n, 'entry', 'entries') + ' were each drafted both ways from the same papers, so every score is compared entry by entry. ' +
      'Difference is the evidence-graph draft minus the direct draft, in percentage points (pp) for percentages and in F1 units for F1 scores. ' +
      '↑ marks scores where higher is better, ↓ where lower is better. The 95% interval is the range the true average difference plausibly lies in; when it spans zero, the data show no clear difference. ' +
      'No interval is computed for fewer than 5 entries. “Entries better” counts the entries where each draft scored better; the sign test p-value asks whether that split could be chance.'));
    const rows = c.overall || [];
    sec.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
      h('caption', { class: 'visually-hidden' }, 'Evidence-graph draft compared with the direct draft, all entries'),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Score'), h('th', { class: 'n', scope: 'col' }, 'Entries'),
        h('th', { class: 'n', scope: 'col' }, stratLabel('kg')), h('th', { class: 'n', scope: 'col' }, stratLabel('direct')),
        h('th', { class: 'n', scope: 'col' }, 'Difference'), h('th', { class: 'n', scope: 'col' }, '95% interval'),
        h('th', { class: 'n', scope: 'col' }, h('abbr', { title: 'Entries where the evidence-graph draft scored better / the direct draft scored better / the same' }, 'Entries better: graph / direct / same')),
        h('th', { class: 'n', scope: 'col' }, h('abbr', { title: 'Exact two-sided sign test on the entries-better counts (ties left out)' }, 'Sign test p')))),
      h('tbody', null, rows.map((r) => {
        const k = cmpKind(r.metric);
        return h('tr', null, metricLabel(r), h('td', { class: 'n' }, String(r.n != null ? r.n : '–')),
          h('td', { class: 'n' }, fmtCmp(r.kg, k)), h('td', { class: 'n' }, fmtCmp(r.direct, k)),
          h('td', { class: 'n strong' }, fmtDiff(r.difference, k)),
          h('td', { class: 'n' }, fmtCI(r.ci95, k) || h('span', { class: 'muted' }, '–')),
          h('td', { class: 'n' }, (r.kg_better || 0) + ' / ' + (r.direct_better || 0) + ' / ' + (r.ties || 0)),
          h('td', { class: 'n' }, isNum(r.sign_test_p) ? r.sign_test_p.toFixed(3) : '–'));
      })))));

    const breakdown = (title, about, groups, groupLabel) => {
      const keys = Object.keys(groups || {});
      if (!keys.length) return null;
      const metrics = [];
      for (const g of keys) for (const r of groups[g].metrics || []) if (!metrics.some((m) => m.metric === r.metric)) metrics.push(r);
      return h('div', { class: 'cmp-block' }, h('h3', null, title), h('p', { class: 'small muted' }, about),
        h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
          h('caption', { class: 'visually-hidden' }, title),
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Score'),
            keys.map((g) => h('th', { class: 'n', scope: 'col' }, groupLabel(g), h('div', { class: 'cmp-n' }, plural(groups[g].n || 0, 'entry', 'entries')))))),
          h('tbody', null, metrics.map((m) => {
            const k = cmpKind(m.metric);
            return h('tr', null, metricLabel(m), keys.map((g) => {
              const r = (groups[g].metrics || []).find((x) => x.metric === m.metric);
              if (!r) return h('td', { class: 'n muted' }, '–');
              return h('td', { class: 'n' }, h('div', { class: 'strong' }, fmtDiff(r.difference, k)),
                h('div', { class: 'cmp-pair' }, fmtCmp(r.kg, k) + ' vs ' + fmtCmp(r.direct, k)),
                fmtCI(r.ci95, k) ? h('div', { class: 'cmp-pair' }, '95%: ' + fmtCI(r.ci95, k)) : null);
            }));
          })))));
    };
    const cellNote = 'Each cell: the difference (graph − direct), then the two averages, evidence graph first.';
    add(sec, breakdown('By when the OMIM entry was created', 'OMIM numbers were assigned in ranges over time, so the number range stands for the era in which the entry was written. ' + cellNote,
      c.by_stratum, (g) => g));
    add(sec, breakdown('By how much of the cited literature could be read in full', 'Grouped by the share of the OMIM entry’s references available as full text rather than abstract or title only. ' + cellNote,
      c.by_access, (g) => humanize(g)));

    const lv = c.by_gold_text_content_level || {};
    const lk = ['fulltext', 'abstract', 'title', 'not_retrieved'].filter((k) => lv[k]).concat(Object.keys(lv).filter((k) => !LEVEL[k]));
    if (lk.length) {
      sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'OMIM facts conveyed, by how much of each paper was readable'),
        h('p', { class: 'small muted' }, 'All OMIM per-paper facts pooled across entries, grouped by how much of the paper they summarise could be read.'),
        h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Paper readable as'), h('th', { class: 'n', scope: 'col' }, 'Facts judged (graph / direct)'),
            h('th', { class: 'n', scope: 'col' }, 'Conveyed: ' + stratShort('kg')), h('th', { class: 'n', scope: 'col' }, 'Conveyed: ' + stratShort('direct')),
            h('th', { class: 'n', scope: 'col' }, 'Contradicted (graph / direct)'))),
          h('tbody', null, lk.map((k) => {
            const g = lv[k].kg || {}; const d = lv[k].direct || {};
            return h('tr', null, h('th', { scope: 'row' }, (LEVEL[k] || { label: humanize(k) }).label),
              h('td', { class: 'n' }, (g.n_facts || 0) + ' / ' + (d.n_facts || 0)),
              h('td', { class: 'n' }, fmtCmp(g.coverage, 'pct')), h('td', { class: 'n' }, fmtCmp(d.coverage, 'pct')),
              h('td', { class: 'n' }, (g.contradicted || 0) + ' / ' + (d.contradicted || 0)));
          }))))));
    }

    const pk = get(c, 'pooled.kg'); const pd = get(c, 'pooled.direct');
    if (pk && pd) {
      const line = (label, path, kind, sub) => h('tr', null, h('th', { scope: 'row', class: sub ? 'sub' : null }, label),
        [pk, pd].map((x) => { const v = get(x, path); return h('td', { class: 'n' }, kind === 'pct' ? fmtCmp(v, 'pct') : isNum(v) ? v.toLocaleString('en-US') : '–'); }));
      sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'Pooled counts'),
        h('p', { class: 'small muted' }, 'Totals over all entries, so entries with many claims or facts weigh more than in the averages above.'),
        h('div', { class: 'table-scroll compare' }, h('table', { class: 'data cmp' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, ''), h('th', { class: 'n', scope: 'col' }, stratLabel('kg')), h('th', { class: 'n', scope: 'col' }, stratLabel('direct')))),
          h('tbody', null,
            line('Claims audited', 'claims.n'), line('supported', 'claims.supported', null, true), line('partly supported', 'claims.partially_supported', null, true),
            line('not supported', 'claims.unsupported', null, true), line('contradicted', 'claims.contradicted', null, true),
            line('Share supported', 'claims.supported_rate', 'pct'), line('Share not supported or contradicted', 'claims.error_rate', 'pct'),
            line('OMIM facts judged', 'gold_facts.n_facts'), line('present', 'gold_facts.present', null, true), line('partial', 'gold_facts.partial', null, true),
            line('absent', 'gold_facts.absent', null, true), line('contradicted', 'gold_facts.contradicted', null, true),
            line('Share conveyed (partial counts ½)', 'gold_facts.coverage', 'pct'), line('Share contradicted', 'gold_facts.contradiction_rate', 'pct'))))));
    }
    return sec;
  }

  // ------------------------------------------------------------------ evidence graph picture
  const SVGNS = 'http://www.w3.org/2000/svg';
  function sv(tag, attrs) {
    const el = document.createElementNS(SVGNS, tag);
    for (const k of Object.keys(attrs || {})) { const v = attrs[k]; if (v !== null && v !== undefined && v !== false) el.setAttribute(k, String(v)); }
    for (let i = 2; i < arguments.length; i++) {
      const kid = arguments[i];
      if (kid === null || kid === undefined || kid === false) continue;
      (Array.isArray(kid) ? kid : [kid]).forEach((c) => { if (c !== null && c !== undefined && c !== false) el.append(c instanceof Node ? c : String(c)); });
    }
    return el;
  }
  const trunc = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; };

  function evidenceGraph(item) {
    const ents = (item.kg && item.kg.entities) || [];
    if (!ents.length) return null;
    const W = 1040, RH = 26, NH = 20, TOP = 34;
    const X = { paper: 8, mid: 292, entry: 560, right: 812 };
    const CW = { paper: 196, mid: 200, entry: 176, right: 220 };
    const CAP_PER_CAT = 6, CAP_PHEN = 42, CAP_VAR = 18, CAP_PAPERS = 30;

    // category of each HPO term, from the clinical synopsis (evidence-graph draft first)
    const catOf = new Map();
    for (const s of ['kg'].concat(item.strategies)) for (const it of get(item, 'entries.' + s + '.clinical_synopsis') || []) if (it.hpo_id && !catOf.has(it.hpo_id)) catOf.set(it.hpo_id, it.category || 'Other features');

    const nodes = new Map();   // id -> {id, kind, label, x, y, w, href, title}
    const rowsMid = [], rowsRight = [], rowsPaper = [];
    const genes = ents.filter((e) => e.rel === 'caused_by');
    const variants = ents.filter((e) => e.rel === 'has_variant');
    const inh = ents.filter((e) => e.rel === 'inheritance');
    const phen = ents.filter((e) => e.rel === 'has_phenotype');
    const byPapers = (a, b) => (b.pmids || []).length - (a.pmids || []).length || String(a.label).localeCompare(String(b.label));

    // middle column: each gene followed by its variants
    const geneIds = genes.map((g) => g.id);
    for (const v of variants) if (v.gene_id && geneIds.indexOf(v.gene_id) < 0) { geneIds.push(v.gene_id); genes.push({ id: v.gene_id, rel: 'gene_only', label: v.gene_id.replace(/^gene:/, ''), pmids: [] }); }
    let shownVar = 0;
    const varsOf = (gid) => variants.filter((v) => v.gene_id === gid).sort(byPapers);
    const orphanVars = variants.filter((v) => !v.gene_id || geneIds.indexOf(v.gene_id) < 0).sort(byPapers);
    const pushVar = (v) => { if (shownVar >= CAP_VAR) return false; shownVar++; rowsMid.push({ kind: 'variant', ent: v }); return true; };
    genes.forEach((g, gi) => {
      if (gi) rowsMid.push({ kind: 'gap' });
      rowsMid.push({ kind: 'gene', ent: g });
      varsOf(g.id).forEach(pushVar);
    });
    if (orphanVars.length) { if (rowsMid.length) rowsMid.push({ kind: 'gap' }); orphanVars.forEach(pushVar); }
    if (variants.length > shownVar) rowsMid.push({ kind: 'more', text: '+' + (variants.length - shownVar) + ' more variants' });

    // right column: inheritance, then phenotypes grouped by synopsis category
    if (inh.length) { rowsRight.push({ kind: 'head', text: 'Inheritance' }); inh.forEach((e) => rowsRight.push({ kind: 'inheritance', ent: e })); }
    const cats = new Map();
    for (const p of phen) { const c = catOf.get(p.hpo_id) || 'Other features'; if (!cats.has(c)) cats.set(c, []); cats.get(c).push(p); }
    let shownPhen = 0;
    const catNames = Array.from(cats.keys()).sort((a, b) => (a === 'Other features') - (b === 'Other features') || a.localeCompare(b));
    for (const c of catNames) {
      const list = cats.get(c).sort(byPapers);
      if (rowsRight.length) rowsRight.push({ kind: 'gap' });
      rowsRight.push({ kind: 'head', text: c, cat: c });
      const room = Math.max(0, Math.min(CAP_PER_CAT, CAP_PHEN - shownPhen));
      list.slice(0, room).forEach((p) => rowsRight.push({ kind: 'phenotype', ent: p }));
      shownPhen += Math.min(room, list.length);
      if (list.length > room) rowsRight.push({ kind: 'more', text: '+' + (list.length - room) + ' more' });
    }

    // papers: every paper the graph cites, oldest first
    const pm = new Set();
    for (const e of ents) for (const p of e.pmids || []) pm.add(String(p));
    const paperList = Array.from(pm).map((p) => ({ pmid: p, year: (item.paperBy.get(p) || {}).year || 9999 })).sort((a, b) => a.year - b.year || a.pmid.localeCompare(b.pmid));
    paperList.slice(0, CAP_PAPERS).forEach((p) => rowsPaper.push({ kind: 'paper', pmid: p.pmid }));
    if (paperList.length > CAP_PAPERS) rowsPaper.push({ kind: 'more', text: '+' + (paperList.length - CAP_PAPERS) + ' more papers' });

    const heightOf = (rows) => rows.reduce((s, r) => s + (r.kind === 'gap' ? 10 : RH), 0);
    const H = Math.max(heightOf(rowsMid), heightOf(rowsRight), heightOf(rowsPaper), 3 * RH) + TOP + 12;
    const place = (rows, col) => {
      let y = TOP + (H - TOP - 12 - heightOf(rows)) / 2;
      for (const r of rows) { r.y = y; r.col = col; y += r.kind === 'gap' ? 10 : RH; }
    };
    place(rowsPaper, 'paper'); place(rowsMid, 'mid'); place(rowsRight, 'right');

    const edgesG = sv('g', { class: 'kg-edges' });
    const nodesG = sv('g', { class: 'kg-nodes' });
    const adj = new Map();
    const link = (a, b, el) => { [a, b].forEach((x) => { if (!adj.has(x)) adj.set(x, { nodes: new Set(), edges: [] }); }); adj.get(a).nodes.add(b); adj.get(b).nodes.add(a); adj.get(a).edges.push(el); adj.get(b).edges.push(el); };
    const curve = (x1, y1, x2, y2) => { const dx = Math.max(30, (x2 - x1) / 2); return 'M' + x1 + ' ' + y1 + ' C' + (x1 + dx) + ' ' + y1 + ' ' + (x2 - dx) + ' ' + y2 + ' ' + x2 + ' ' + y2; };

    function nodeEl(id, kind, x, y, w, label, title, href) {
      const rect = sv('rect', { x: x, y: y, width: w, height: NH, rx: kind === 'paper' ? 3 : 10 });
      const text = sv('text', { x: x + 8, y: y + NH / 2, 'dominant-baseline': 'central' }, label);
      const g = sv('g', { class: 'kg-node kg-' + kind, 'data-node': id, tabindex: href ? null : '0' }, sv('title', null, title), rect, text);
      const el = href ? sv('a', { href: href, target: '_blank', rel: 'noopener noreferrer', class: 'kg-link', 'aria-label': title }, g) : g;
      if (!href) g.setAttribute('aria-label', title);
      nodes.set(id, { id: id, x: x, y: y + NH / 2, w: w, g: g });
      nodesG.append(el);
      return g;
    }
    const charsFor = (w) => Math.floor((w - 14) / 6.4);

    for (const r of rowsPaper) {
      if (r.kind === 'more') { nodesG.append(sv('text', { class: 'kg-more', x: X.paper + 8, y: r.y + NH / 2, 'dominant-baseline': 'central' }, r.text)); continue; }
      const p = item.paperBy.get(r.pmid) || {};
      const label = paperLabel(item, r.pmid);
      nodeEl('paper:' + r.pmid, 'paper', X.paper, r.y, CW.paper, trunc(label, charsFor(CW.paper)),
        label + (p.title ? ': ' + p.title : '') + ' (PMID ' + r.pmid + '). Opens PubMed.', pubmedUrl(r.pmid));
    }
    for (const r of rowsMid) {
      if (r.kind === 'gap') continue;
      if (r.kind === 'more') { nodesG.append(sv('text', { class: 'kg-more', x: X.mid + 8, y: r.y + NH / 2, 'dominant-baseline': 'central' }, r.text)); continue; }
      const e = r.ent;
      const label = r.kind === 'variant' ? (e.omim_name || e.label) : e.label;
      const full = r.kind === 'variant' && e.omim_name ? e.omim_name + ' (' + e.label + ')' : label;
      const indent = r.kind === 'variant' && e.gene_id ? 14 : 0;
      nodeEl(e.id, r.kind, X.mid + indent, r.y, CW.mid - indent, trunc(label, charsFor(CW.mid - indent)),
        (r.kind === 'gene' ? 'Gene ' : 'Variant ') + full + ': ' + plural((e.pmids || []).length, 'supporting paper'));
    }
    for (const r of rowsRight) {
      if (r.kind === 'gap') continue;
      if (r.kind === 'head') { nodesG.append(sv('text', { class: 'kg-head', x: X.right, y: r.y + NH / 2 + 2, 'dominant-baseline': 'central' }, r.text.toUpperCase())); continue; }
      if (r.kind === 'more') { nodesG.append(sv('text', { class: 'kg-more', x: X.right + 8, y: r.y + NH / 2, 'dominant-baseline': 'central' }, r.text)); continue; }
      const e = r.ent;
      const label = e.label || e.hpo_id || e.id;
      nodeEl(e.id, r.kind, X.right, r.y, CW.right, trunc(label, charsFor(CW.right)),
        label + (e.hpo_id ? ' (' + e.hpo_id + ')' : '') + ': ' + plural((e.pmids || []).length, 'supporting paper') + (r.kind === 'phenotype' && e.hpo_id ? '. Opens HPO.' : ''),
        r.kind === 'phenotype' && e.hpo_id ? hpoUrl(e.hpo_id) : null);
    }
    // entry, centred
    const num = entryNumber(item, null);
    const ey = H / 2 - 26;
    const entryG = sv('g', { class: 'kg-node kg-entry', 'data-node': 'entry', tabindex: '0', 'aria-label': 'This entry' },
      sv('title', null, (num.mim ? num.mim + ' ' : '') + (item.title || '')),
      sv('rect', { x: X.entry, y: ey, width: CW.entry, height: 52, rx: 6 }),
      sv('text', { x: X.entry + CW.entry / 2, y: ey + 17, 'text-anchor': 'middle', 'dominant-baseline': 'central', class: 'kg-entry-num' }, num.mim ? (num.prefix ? num.prefix + ' ' : '') + num.mim : 'New entry'),
      sv('text', { x: X.entry + CW.entry / 2, y: ey + 36, 'text-anchor': 'middle', 'dominant-baseline': 'central' }, trunc(item.title, 21)));
    nodes.set('entry', { id: 'entry', x: X.entry, y: H / 2, w: CW.entry, g: entryG });

    // edges: paper -> entity (supports), variant -> gene (in gene), entry -> gene / inheritance / phenotype groups
    const edge = (a, b, d, cls) => { const el = sv('path', { d: d, class: 'kg-edge ' + (cls || '') }); edgesG.append(el); link(a, b, el); return el; };
    for (const e of ents) {
      const t = nodes.get(e.id);
      if (!t) continue;
      for (const p of e.pmids || []) {
        const s = nodes.get('paper:' + p);
        if (s) edge(s.id, t.id, curve(s.x + s.w, s.y, t.x, t.y), 'kg-supports');
      }
      if (e.rel === 'has_variant' && e.gene_id && nodes.get(e.gene_id)) {
        const g = nodes.get(e.gene_id);
        const xr = X.mid + CW.mid;
        edge(e.id, g.id, 'M' + xr + ' ' + t.y + ' C' + (xr + 22) + ' ' + t.y + ' ' + (xr + 22) + ' ' + g.y + ' ' + xr + ' ' + g.y, 'kg-ingene');
      }
    }
    const en = nodes.get('entry');
    const labels = sv('g', { class: 'kg-labels' });
    let firstGene = true;
    for (const g of genes) {
      const n = nodes.get(g.id);
      if (!n || g.rel !== 'caused_by') continue;
      edge('entry', g.id, curve(n.x + n.w + 26, n.y, en.x, en.y), 'kg-entryedge');
      if (firstGene) { labels.append(sv('text', { class: 'kg-rel', x: (n.x + n.w + 26 + en.x) / 2, y: (n.y + en.y) / 2 - 7, 'text-anchor': 'middle' }, 'caused by')); firstGene = false; }
    }
    for (const r of rowsRight) {
      if (r.kind !== 'inheritance' && r.kind !== 'head') continue;
      if (r.kind === 'head' && !r.cat) continue;
      const y = r.y + NH / 2;
      const target = r.kind === 'inheritance' ? r.ent.id : null;
      const el = sv('path', { d: curve(en.x + en.w, en.y, X.right - 6, y), class: 'kg-edge kg-entryedge' });
      edgesG.append(el);
      if (target) link('entry', target, el);
      else { // a category: the entry links to every phenotype shown under it
        for (const p of cats.get(r.cat) || []) if (nodes.get(p.id)) link('entry', p.id, el);
      }
    }
    // column headings
    const heads = sv('g', { class: 'kg-colhead' },
      sv('text', { x: X.paper, y: 14 }, 'PAPERS (' + paperList.length + ')'),
      sv('text', { x: X.mid, y: 14 }, 'GENES AND VARIANTS'),
      sv('text', { x: X.right, y: 14 }, 'INHERITANCE AND FEATURES'));

    const svg = sv('svg', { class: 'kg', viewBox: '0 0 ' + W + ' ' + H, role: 'img', width: W, height: H,
      'aria-label': 'Evidence graph: ' + paperList.length + ' papers linked to the genes, variants, inheritance and clinical features they support in this entry.' },
    heads, edgesG, entryG, nodesG, labels);
    svg.setAttribute('preserveAspectRatio', 'xMidYMin meet');

    // highlight a node's links and neighbours on hover or keyboard focus
    const on = (id) => {
      const a = adj.get(id);
      svg.classList.add('focusing');
      svg.querySelectorAll('.on').forEach((x) => x.classList.remove('on'));
      const n = nodes.get(id); if (n) n.g.classList.add('on');
      if (!a) return;
      a.edges.forEach((e) => e.classList.add('on'));
      a.nodes.forEach((x) => { const m = nodes.get(x); if (m) m.g.classList.add('on'); });
    };
    const off = () => { svg.classList.remove('focusing'); svg.querySelectorAll('.on').forEach((x) => x.classList.remove('on')); };
    nodes.forEach((n) => {
      n.g.addEventListener('pointerenter', () => on(n.id));
      n.g.addEventListener('pointerleave', off);
      n.g.addEventListener('focusin', () => on(n.id));
      n.g.addEventListener('focusout', off);
    });

    const capped = phen.length > shownPhen || variants.length > shownVar || paperList.length > CAP_PAPERS;
    return h('figure', { class: 'kg-figure' },
      h('div', { class: 'kg-scroll' }, svg),
      h('figcaption', { class: 'small muted' },
        'Each line from a paper means that paper supports linking the item to this entry. Dashed lines join a variant to its gene; features are grouped by clinical-synopsis heading. ' +
        'Point at or tab to an item to highlight its links; select a paper to open it in PubMed or a feature to open its HPO page.' +
        (capped ? ' Some items are summarised as “+N more”; the tables below list everything.' : '')));
  }

  // ------------------------------------------------------------------ entry view
  function viewLoading(item) {
    const wrap = h('div', { class: 'wrap' });
    const num = entryNumber(item, null);
    wrap.append(h('header', { class: 'entry-head' },
      h('div', { class: 'entry-number' }, num.mim ? [num.prefix ? h('span', { class: 'prefix' }, num.prefix + ' ') : null, num.mim] : 'New entry (no OMIM number yet)'),
      h('h1', { class: 'entry-title' }, item.title || item.dir)));
    if (item.loadError) {
      wrap.append(h('div', { class: 'empty load-error', role: 'alert', style: 'margin-top:18px' },
        h('strong', null, 'This entry could not be opened. '), item.loadError,
        h('p', { style: 'margin-top:8px' }, 'The page keeps each entry in a separate file in the “' + DATA_DIR + '” folder. Keep that folder next to this page (copy or move them together), then try again.'),
        h('div', { class: 'btn-row', style: 'margin-top:10px' },
          h('button', { type: 'button', class: 'btn primary', 'data-fid': 'retry', onclick: () => { item.loadError = null; render({ keepScroll: true }); } }, 'Try again'),
          h('a', { class: 'btn', href: '#overview' }, 'Back to the overview'))));
      return wrap;
    }
    wrap.append(h('div', { class: 'loading', role: 'status', 'aria-live': 'polite' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the entry…'));
    loadEntry(item).then(() => rerenderIfShowing(item), () => rerenderIfShowing(item));
    return wrap;
  }
  function rerenderIfShowing(item) {
    const r = parseHash();
    if ((r.view === 'entry' && r.item === item) || r.view === 'updates') render({ keepScroll: true });
  }

  function viewEntry(route) {
    const item = route.item;
    if (!item.loaded) return viewLoading(item);
    const s = route.strategy;
    const entry = s ? item.entries[s] : null;
    const ev = s ? item.evals[s] : null;
    const wrap = h('div', { class: 'wrap' });
    const num = entryNumber(item, entry);
    const title = (entry && entry.title) || item.title || item.dir;
    const symbol = (entry && entry.symbol) || get(item, 'seed.symbol') || '';
    const alt = (entry && entry.alt_titles && entry.alt_titles.length ? entry.alt_titles : get(item, 'seed.alt_titles')) || [];

    const head = h('header', { class: 'entry-head' },
      h('div', { class: 'entry-number' },
        num.mim ? [num.prefix ? h('span', { class: 'prefix', title: prefixHelp(num.prefix) }, num.prefix + ' ') : null, num.mim, ' · ', ext(omimUrl(num.mim), 'Open the published OMIM entry')]
          : 'New entry (no OMIM number yet)'),
      h('h1', { class: 'entry-title' }, title + (symbol ? '; ' + symbol : '')),
      alt.length ? h('div', { class: 'entry-alt' }, h('span', { class: 'small muted' }, 'Alternative titles; symbols: '), alt.join('; ')) : null);
    wrap.append(head);
    wrap.append(h('div', { style: 'margin-top:12px' }, unreviewedNotice()));

    const controls = h('div', { class: 'entry-controls' });
    if (item.strategies.length > 1) {
      controls.append(h('div', { class: 'seg', role: 'group', 'aria-label': 'Which draft to show' },
        item.strategies.map((x) => h('button', { type: 'button', 'aria-pressed': String(x === s), 'data-fid': 'strat-' + x,
          onclick: () => { state.selected = null; location.hash = entryHash(item, route.tab === 'updates' ? 'review' : route.tab, x); } }, stratLabel(x)))));
    } else if (s) controls.append(h('span', { class: 'small muted' }, stratLabel(s)));
    if (s) controls.append(progressEl(item, s));
    wrap.append(controls);

    const tabs = [];
    if (s) tabs.push({ id: 'review', label: 'Review draft' });
    if (s) tabs.push({ id: 'gold', label: 'Compare with OMIM', disabled: !ev });
    tabs.push({ id: 'evidence', label: 'Evidence' });
    if (item.updates) tabs.push({ id: 'updates', label: 'Proposed updates', count: (item.updates.proposals || []).length });
    let tab = route.tab;
    if (!tabs.some((t) => t.id === tab)) tab = tabs[0].id;
    wrap.append(h('nav', { class: 'tabs', 'aria-label': 'Entry views' }, tabs.map((t) => h('a', {
      href: entryHash(item, t.id, s), 'aria-current': t.id === tab ? 'page' : null,
      title: t.disabled ? 'No OMIM comparison for this draft' : null,
    }, t.label, isNum(t.count) ? h('span', { class: 'count muted' }, '(' + t.count + ')') : null))));

    if (tab === 'review') wrap.append(reviewTab(item, s, entry));
    else if (tab === 'gold') wrap.append(goldTab(item, s, entry, ev));
    else if (tab === 'evidence') wrap.append(evidenceTab(item));
    else if (tab === 'updates') wrap.append(h('div', { class: 'section' }, updatesBlock(item)));
    return wrap;
  }
  function prefixHelp(p) {
    return ({ '#': 'Phenotype description, molecular basis known', '*': 'Gene', '+': 'Gene and phenotype combined', '%': 'Phenotype or locus, molecular basis unknown', '^': 'Entry removed or moved' })[p] || null;
  }

  // ------------------------------------------------------------------ review tab
  function reviewTab(item, s, entry) {
    const box = h('div');
    if (!entry) {
      box.append(h('div', { class: 'empty', style: 'margin-top:18px' }, 'No draft text was written for this entry.'));
      return box;
    }
    const all = paragraphsOf(entry);
    const counts = { flagged: 0, partial: 0, supported: 0, unverified: 0 };
    all.forEach((x) => { counts[x.p.status] = (counts[x.p.status] || 0) + 1; });

    const filterActive = state.attentionOnly || state.hideReviewed;
    const visible = (p, i) => {
      if (state.attentionOnly && p.status !== 'flagged' && p.status !== 'partial') return false;
      if (state.hideReviewed) { const d = getDecision(item, s, pidOf(p, i)); if (d && d.decision) return false; }
      return true;
    };
    const idx = new Map(); all.forEach((x, i) => idx.set(x.p, i));
    const nVisible = all.filter((x, i) => visible(x.p, i)).length;

    const toolbar = h('div', { class: 'toolbar' },
      h('div', { class: 'chips', 'aria-label': 'Paragraph audit results' },
        ['flagged', 'partial', 'supported', 'unverified'].filter((k) => counts[k]).map((k) => h('span', { class: 'chip ' + STATUS[k].cls, title: STATUS[k].help },
          h('span', { class: 'ic', 'aria-hidden': 'true' }, STATUS[k].icon), counts[k] + ' ' + STATUS[k].label.toLowerCase()))),
      h('label', { class: 'check' }, h('input', { type: 'checkbox', id: 'f-attention', 'data-fid': 'f-attention', checked: state.attentionOnly || null,
        onchange: (e) => { state.attentionOnly = e.target.checked; render({ keepScroll: true, focus: 'f-attention' }); } }), 'Only paragraphs needing attention'),
      h('label', { class: 'check' }, h('input', { type: 'checkbox', id: 'f-reviewed', 'data-fid': 'f-reviewed', checked: state.hideReviewed || null,
        onchange: (e) => { state.hideReviewed = e.target.checked; render({ keepScroll: true, focus: 'f-reviewed' }); } }), 'Hide paragraphs I have decided'),
      h('span', { class: 'spacer' }),
      h('div', { class: 'btn-row' },
        h('button', { type: 'button', class: 'btn', 'data-fid': 'exp-json', onclick: () => exportJSON() }, 'Export review (JSON)'),
        h('button', { type: 'button', class: 'btn', 'data-fid': 'exp-md', onclick: () => exportMarkdown(item, s) }, 'Export reviewed entry (Markdown)')));
    box.append(toolbar);
    if (!storageOk) box.append(h('p', { class: 'small', style: 'color:var(--bad);margin-top:8px' }, 'This browser is not saving your decisions (storage is blocked). They last until you close the page; export them before you leave.'));
    if (state.exportBox) box.append(exportBoxEl());

    const layout = h('div', { class: 'review' });
    const doc = h('article', { class: 'doc', 'aria-label': 'Draft entry text' });
    const aside = h('aside', { class: 'aside', 'aria-label': 'Evidence for the selected paragraph' });
    const selKey = state.selected && state.selected.indexOf(item.key + '|' + s + '|') === 0 ? state.selected.slice((item.key + '|' + s + '|').length) : null;
    let selected = null;

    function paraEl(p) {
      const i = idx.get(p);
      if (!visible(p, i)) return null;
      const pid = pidOf(p, i);
      const st = STATUS[p.status] || STATUS.unverified;
      const d = getDecision(item, s, pid);
      const isSel = selKey === pid;
      if (isSel) selected = all[i];
      const el = h('div', {
        class: 'para s-' + p.status + (d && d.decision === 'reject' ? ' rejected' : ''), role: 'button', tabindex: '0',
        'aria-expanded': String(isSel), 'aria-controls': 'evidence-panel', 'data-fid': 'para-' + pid,
        'aria-label': st.label + ' paragraph ' + pid + (d && d.decision ? ', your decision: ' + DECISION[d.decision].label : '') + '. Press Enter to show evidence.',
      },
      h('div', { class: 'para-meta' }, chip(st), d && d.decision ? chip(DECISION[d.decision]) : null,
        d && d.comment ? plainChip('Comment', 'plain', d.comment) : null, h('span', { class: 'para-id' }, pid)),
      h('p', { class: 'para-text' }, p.text),
      d && d.edited ? [h('div', { class: 'edited-note' }, 'Your edited text:'), h('p', { class: 'edited-text' }, d.edited)] : null,
      p.pmids && p.pmids.length ? h('div', { class: 'para-cites' }, 'Cites ', citeLinks(item, p.pmids)) : null);
      const toggle = () => {
        state.selected = isSel ? null : item.key + '|' + s + '|' + pid;
        render({ keepScroll: true, focus: 'para-' + pid });
      };
      el.addEventListener('click', (e) => { if (!e.target.closest('a,button,input,textarea,select')) toggle(); });
      el.addEventListener('keydown', (e) => { if ((e.key === 'Enter' || e.key === ' ') && e.target === el) { e.preventDefault(); toggle(); } });
      if (isSel && !wide.matches) return [el, h('div', { class: 'inline-panel' }, evidencePanel(item, s, all[i], pid))];
      return el;
    }

    if (filterActive) doc.append(h('p', { class: 'filter-note' }, 'Showing ' + nVisible + ' of ' + plural(all.length, 'paragraph') + '. ',
      h('button', { type: 'button', class: 'btn', 'data-fid': 'clear-filter', onclick: () => { state.attentionOnly = false; state.hideReviewed = false; render({ keepScroll: true }); } }, 'Show all')));
    if (filterActive && nVisible === 0) doc.append(h('div', { class: 'empty' }, state.attentionOnly && !counts.flagged && !counts.partial
      ? 'No paragraph in this draft was flagged or only partly supported by the audit.' : 'Every paragraph matching the filter has a decision.'));

    if (!filterActive && entry.relationships && entry.relationships.length) {
      doc.append(h('h3', null, 'Phenotype–Gene Relationships'));
      doc.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, ['Location', 'Phenotype', 'Phenotype MIM number', 'Inheritance', 'Phenotype mapping key', 'Gene/Locus', 'Gene/Locus MIM number', 'Supported by'].map((t) => h('th', { scope: 'col' }, t)))),
        h('tbody', null, entry.relationships.map((r) => h('tr', null,
          h('td', null, r.location || '–'), h('td', null, r.phenotype || '–'),
          h('td', null, r.phenotype_mim ? ext(omimUrl(r.phenotype_mim), r.phenotype_mim) : '–'),
          h('td', null, (r.inheritance || []).map((c) => h('abbr', { title: INHERITANCE[c] || c }, c + ' '))),
          h('td', { class: 'n' }, r.mapping_key != null ? String(r.mapping_key) : '–'),
          h('td', null, r.gene_symbol || '–'),
          h('td', null, r.gene_mim ? ext(omimUrl(r.gene_mim), r.gene_mim) : '–'),
          h('td', { class: 'small' }, (r.pmids || []).length ? citeLinks(item, r.pmids) : '–')))))));
    }

    const intro = entry.intro ? paraEl(entry.intro) : null;
    if (intro) { doc.append(h('h3', null, 'Text')); add(doc, intro); }
    for (const sec of entry.sections || []) {
      const els = (sec.paragraphs || []).map(paraEl).filter(Boolean);
      if (!els.length) continue;
      doc.append(h('h3', null, sec.heading || SECTION_HEADINGS[sec.name] || humanize(sec.name)));
      add(doc, els);
    }
    if (!filterActive && ((entry.clinical_synopsis || []).length || (entry.inheritance || []).length)) doc.append(synopsisEl(item, s, entry));
    const avEls = (entry.allelic_variants || []).map((av) => {
      const paras = (av.paragraphs || []).map(paraEl).filter(Boolean);
      if (filterActive && !paras.length) return null;
      return h('section', { class: 'av' },
        h('div', { class: 'av-head' },
          h('div', null, h('span', { class: 'av-num' }, '.' + String(av.number || 0).padStart(4, '0')), ' ', h('span', { class: 'av-phen' }, av.phenotype || '')),
          h('div', { class: 'av-name' }, (av.name || '') + (av.hgvs && av.hgvs.length ? ' [' + av.hgvs.join('; ') + ']' : ''))),
        paras);
    }).filter(Boolean);
    if (avEls.length) { doc.append(h('h3', null, 'Allelic Variants')); add(doc, avEls); }
    if (!filterActive && (entry.references || []).length) {
      doc.append(h('h3', null, 'References'));
      doc.append(h('ol', { class: 'refs' }, entry.references.map((r) => h('li', null,
        r.citation || r.label || ('PMID ' + r.pmid), ' ', levelChip(r.content_level), ' ', ext(pubmedUrl(r.pmid), 'PubMed ' + r.pmid)))));
    }
    if (!all.length && !filterActive) doc.append(h('div', { class: 'empty' }, 'This draft has no text paragraphs.'));

    layout.append(doc);
    if (wide.matches) {
      aside.append(selected ? evidencePanel(item, s, selected, pidOf(selected.p, idx.get(selected.p)))
        : h('div', { class: 'aside-empty' }, h('strong', null, 'Select a paragraph'), ' to see what the audit found, the extracted facts and quotes it rests on, and the papers it cites. You record your decision there too.',
          h('p', { style: 'margin-top:8px' }, 'Paragraphs marked ', chip(STATUS.flagged), ' or ', chip(STATUS.partial), ' are the ones to read first.')));
      layout.append(aside);
    }
    box.append(layout);
    return box;
  }

  function synopsisEl(item, s, entry) {
    const frag = h('div');
    frag.append(h('h3', null, 'Clinical Synopsis'));
    const gold = item.goldHpo;
    const groups = new Map();
    for (const it of entry.clinical_synopsis || []) {
      const c = it.category || 'Other';
      if (!groups.has(c)) groups.set(c, []);
      groups.get(c).push(it);
    }
    const box = h('div', { class: 'synopsis' });
    if (gold) box.append(h('p', { class: 'small muted' }, 'Each term shows the papers that report it and whether HPO’s annotation of the OMIM entry lists the same term.'));
    if ((entry.inheritance || []).length) {
      box.append(h('div', { class: 'syn-cat' }, h('h4', null, 'Inheritance'), h('ul', null, entry.inheritance.map((c) => h('li', null, h('span', { class: 'syn-label' }, INHERITANCE[c] || c))))));
    }
    for (const cat of Array.from(groups.keys()).sort()) {
      box.append(h('div', { class: 'syn-cat' }, h('h4', null, cat), h('ul', null, groups.get(cat).map((it) => {
        const n = isNum(it.n_papers) && it.n_papers ? it.n_papers : (it.pmids || []).length;
        let match = null;
        if (gold && it.hpo_id) match = gold.has(it.hpo_id) ? plainChip('✓ In OMIM annotation', 'ok', 'HPO annotates the OMIM entry with this exact term') : plainChip('Not in OMIM annotation', 'plain', 'HPO’s annotation of the OMIM entry does not list this exact term (a broader or narrower term may be listed; see Compare with OMIM)');
        return h('li', null,
          h('span', { class: 'syn-label' }, it.hpo_label || it.feature, it.feature && it.hpo_label && it.feature.toLowerCase() !== it.hpo_label.toLowerCase() ? h('span', { class: 'syn-feature' }, ' (“' + it.feature + '”)') : null),
          it.hpo_id ? hpoLink(it.hpo_id) : h('span', { class: 'muted' }, 'no HPO term'),
          h('span', { class: 'muted', title: (it.pmids || []).map((p) => paperLabel(item, p)).join('; ') || null }, plural(n, 'paper')),
          match);
      }))));
    }
    frag.append(box);
    return frag;
  }

  function evidencePanel(item, s, x, pid) {
    const p = x.p;
    const d = getDecision(item, s, pid) || {};
    const st = STATUS[p.status] || STATUS.unverified;
    const panel = h('section', { class: 'panel', id: 'evidence-panel', 'aria-label': 'Evidence and decision for paragraph ' + pid });
    panel.append(h('div', { class: 'panel-head' },
      h('div', { class: 'chips' }, chip(st), h('span', { class: 'para-id' }, pid)),
      h('h3', null, x.where)));
    const body = h('div', { class: 'panel-body' });

    // decision
    const showEdit = d.decision === 'edit' || !!d.edited;
    const dec = h('div', { class: 'decision', role: 'group', 'aria-label': 'Your decision' },
      h('h4', { style: 'margin:0' }, 'Your decision'),
      h('div', { class: 'decision-buttons' }, Object.keys(DECISION).map((k) => h('button', {
        type: 'button', class: DECISION[k].btn, 'aria-pressed': String(d.decision === k), 'data-fid': 'dec-' + pid + '-' + k,
        onclick: () => { setDecision(item, s, pid, { decision: d.decision === k ? null : k }); render({ keepScroll: true, focus: 'dec-' + pid + '-' + k }); },
      }, h('span', { 'aria-hidden': 'true' }, DECISION[k].icon + ' '), DECISION[k].label))),
      h('div', { class: 'field' }, h('label', { for: 'c-' + pid }, 'Comment (optional)'),
        h('textarea', { id: 'c-' + pid, 'data-fid': 'c-' + pid, rows: '2', placeholder: 'What should change, or why you decided this',
          oninput: (e) => { setDecision(item, s, pid, { comment: e.target.value }); savedNote(); } }, d.comment || '')),
      h('details', { class: 'more', open: showEdit || null },
        h('summary', null, d.edited ? 'Edited text (changed)' : 'Edit the text'),
        h('div', { class: 'field' }, h('label', { for: 'e-' + pid }, 'Edited paragraph (used in the Markdown export)'),
          h('textarea', { id: 'e-' + pid, class: 'edit-text', 'data-fid': 'e-' + pid,
            oninput: (e) => { const v = e.target.value; setDecision(item, s, pid, { edited: v.trim() && v !== p.text ? v : '' }); savedNote(); } }, d.edited || p.text),
          h('div', null, h('button', { type: 'button', class: 'btn', 'data-fid': 'reset-' + pid, onclick: () => { setDecision(item, s, pid, { edited: '' }); render({ keepScroll: true, focus: 'e-' + pid }); } }, 'Restore the original text')))),
      h('div', { class: 'saved-note', 'aria-live': 'polite', id: 'saved-note' }, storageOk ? 'Saved in this browser as you type.' : 'Not saved: this browser blocks storage. Export before closing.'));
    body.append(dec);

    // audit
    const checks = p.checks || [];
    body.append(h('div', null, h('h4', null, 'What the audit found (' + plural(checks.length, 'claim') + ')'),
      checks.length ? claimList(item, checks) : h('p', { class: 'muted' }, 'The audit did not check this paragraph, so nothing here has been compared with the papers.')));

    // findings
    const fids = p.finding_ids || [];
    if (fids.length) {
      body.append(h('div', null, h('h4', null, 'Extracted facts it was written from (' + fids.length + ')'),
        h('ul', { class: 'findings' }, fids.map((fid) => {
          const f = item.findingBy.get(fid);
          if (!f) return h('li', { class: 'muted' }, 'Fact ' + fid + ' is not in this run’s extraction file.');
          return h('li', null,
            h('div', { class: 'chips' }, plainChip(SECTION_HEADINGS[f.section] || humanize(f.section)), h('span', { class: 'small' }, ext(pubmedUrl(f.pmid), paperLabel(item, f.pmid))), h('span', { class: 'para-id' }, f.id)),
            h('div', null, f.statement || ''),
            (f.quotes || []).map((q, qi) => {
              const g = (f.quote_grounding || [])[qi];
              const found = isNum(g) && g >= 0.85;
              return h('div', { class: 'quote-row' }, h('blockquote', { class: 'quote' }, q),
                h('span', { class: 'small ' + (found ? '' : 'muted') }, isNum(g) ? (found ? '✓ Found in the paper' : '✗ Not found word for word in the paper') + ' (match ' + g.toFixed(2) + ')' : 'Not checked against the paper'));
            }));
        }))));
    } else {
      body.append(h('div', null, h('h4', null, 'Extracted facts'), h('p', { class: 'muted' }, s === 'direct'
        ? 'The direct draft is written straight from the papers, so it has no extracted facts to show. Rely on the audit and the papers.'
        : 'This paragraph is not linked to extracted facts.')));
    }

    // papers
    const pmids = p.pmids || [];
    body.append(h('div', null, h('h4', null, 'Cited papers'),
      pmids.length ? h('ul', { class: 'papers-list' }, pmids.map((pmid) => {
        const pp = item.paperBy.get(String(pmid)) || {};
        return h('li', null, h('div', null, ext(pubmedUrl(pmid), paperLabel(item, pmid)), ' ', levelChip(paperLevel(item, pmid))),
          pp.title ? h('div', { class: 'small muted' }, pp.title) : null);
      })) : h('p', { class: 'muted' }, 'This paragraph cites no paper.')));
    panel.append(body);
    return panel;
  }
  // Problems first; with many claims, the supported ones fold away so the problems stay in view.
  const VERDICT_ORDER = { contradicted: 0, unsupported: 1, partially_supported: 2, not_checkable: 3, supported: 4 };
  function claimItem(item, c) {
    const v = VERDICT[c.verdict] || VERDICT.not_checkable;
    return h('li', { class: 'v-' + v.cls }, h('div', { class: 'chips' }, chip(v), c.pmid ? h('span', { class: 'small' }, 'against ', ext(pubmedUrl(c.pmid), paperLabel(item, c.pmid))) : null),
      h('div', { class: 'claim-text' }, c.claim || ''),
      c.evidence_quote ? h('div', { class: 'quote-row' }, h('span', { class: 'small muted' }, 'Evidence in the paper:'), h('blockquote', { class: 'quote' }, c.evidence_quote)) : null,
      c.explanation ? h('div', { class: 'small' }, c.explanation) : null);
  }
  function claimList(item, checks) {
    const sorted = checks.map((c, i) => [c, i]).sort((a, b) => ((VERDICT_ORDER[a[0].verdict] ?? 3) - (VERDICT_ORDER[b[0].verdict] ?? 3)) || a[1] - b[1]).map((x) => x[0]);
    const ok = sorted.filter((c) => c.verdict === 'supported');
    const rest = sorted.filter((c) => c.verdict !== 'supported');
    if (checks.length <= 5 || ok.length < 3) return h('ul', { class: 'claims' }, sorted.map((c) => claimItem(item, c)));
    return h('div', { class: 'claims-wrap' },
      rest.length ? h('ul', { class: 'claims' }, rest.map((c) => claimItem(item, c))) : null,
      h('details', { class: 'more' }, h('summary', null, 'Show ' + plural(ok.length, 'supported claim')),
        h('ul', { class: 'claims' }, ok.map((c) => claimItem(item, c)))));
  }
  let savedTimer = null;
  function savedNote() {
    refreshProgress();
    const el = $('#saved-note');
    if (!el) return;
    el.textContent = storageOk ? 'Saved in this browser.' : 'Not saved: this browser blocks storage. Export before closing.';
    clearTimeout(savedTimer);
    savedTimer = setTimeout(() => { const e2 = $('#saved-note'); if (e2 && storageOk) e2.textContent = 'Saved in this browser as you type.'; }, 1500);
  }

  // ------------------------------------------------------------------ exports
  function download(name, text, mime) {
    try {
      const url = URL.createObjectURL(new Blob([text], { type: mime }));
      const a = h('a', { href: url, download: name, style: 'display:none' });
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) { /* fall back to the copy box below */ }
    state.exportBox = { name: name, text: text };
    render({ keepScroll: true, focus: 'export-copy' });
    toast('Exported ' + name);
  }
  function exportBoxEl() {
    const b = state.exportBox;
    return h('div', { class: 'export-box' },
      h('div', null, h('strong', null, b.name), ' was downloaded. If your browser did not save a file, copy the text below.'),
      h('label', { class: 'visually-hidden', for: 'export-text' }, 'Exported text'),
      h('textarea', { id: 'export-text', readonly: true }, b.text),
      h('div', { class: 'btn-row' },
        h('button', { type: 'button', class: 'btn primary', 'data-fid': 'export-copy', onclick: () => {
          const ta = $('#export-text');
          const done = () => toast('Copied to the clipboard');
          const fallback = () => { ta.focus(); ta.select(); toast('Text selected; press Ctrl+C or ⌘C to copy'); };
          try { navigator.clipboard.writeText(b.text).then(done, fallback); } catch (e) { fallback(); }
        } }, 'Copy text'),
        h('button', { type: 'button', class: 'btn', onclick: () => { state.exportBox = null; render({ keepScroll: true }); } }, 'Close')));
  }
  const safeName = (s) => String(s).replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'entry';
  function exportJSON() {
    // Decisions live in the index; their paragraph text needs the entry data, so load it first.
    const wanted = ENTRIES.filter((item) => item.strategies.some((s) => (item.pids[s] || []).some((pid) => getDecision(item, s, pid))));
    const missing = wanted.filter((it) => !it.loaded);
    if (missing.length) toast('Loading ' + plural(missing.length, 'entry', 'entries') + ' for the export…');
    Promise.all(wanted.map((it) => loadEntry(it).catch(() => null))).then(() => {
      const rows = [];
      for (const item of wanted) for (const s of item.strategies) {
        const paras = item.loaded ? paragraphsOf(item.entries[s]) : [];
        (item.pids[s] || []).forEach((pid, i) => {
          const d = getDecision(item, s, pid);
          if (!d) return;
          const x = paras[i] && pidOf(paras[i].p, i) === pid ? paras[i] : null;
          rows.push({
            entry: item.mim || item.dir, entry_title: item.title, draft: s, draft_label: stratLabel(s),
            paragraph_id: pid, location: x ? x.where : null, decision: d.decision || null,
            original_text: x ? x.p.text : null, edited_text: d.edited || null, comment: d.comment || null,
            audit_status: x ? x.p.status : null, pmids: x ? x.p.pmids || [] : [], decided_at: d.updated || null,
          });
        });
      }
      const progress = [];
      for (const item of ENTRIES) for (const s of item.strategies) { const pr = progressOf(item, s); progress.push({ entry: item.mim || item.dir, draft: s, reviewed: pr.done, paragraphs: pr.total }); }
      const failed = wanted.filter((it) => !it.loaded).map((it) => it.mim || it.dir);
      const out = { run: RUN, exported_at: new Date().toISOString(), note: 'Curator decisions on machine-drafted OMIM entries.' +
        (failed.length ? ' Paragraph text missing for entries whose data file could not be loaded: ' + failed.join(', ') + '.' : ''), progress: progress, decisions: rows };
      download('review-' + safeName(RUN) + '.json', JSON.stringify(out, null, 2) + '\n', 'application/json');
    });
  }
  function exportMarkdown(item, s) {
    const entry = item.entries[s];
    if (!entry) return;
    const num = entryNumber(item, entry);
    const out = [];
    const tally = { accept: 0, edit: 0, reject: 0, none: 0 };
    const all = paragraphsOf(entry);
    const idx = new Map(); all.forEach((x, i) => idx.set(x.p, i));
    const text = (p) => {
      const d = getDecision(item, s, pidOf(p, idx.get(p))) || {};
      tally[d.decision || 'none']++;
      if (d.decision === 'reject') return null;
      return d.edited || p.text;
    };
    out.push('# ' + (num.mim ? ((num.prefix ? num.prefix + ' ' : '') + num.mim) : '(new entry)'));
    out.push('## ' + (entry.title || item.title || '') + (entry.symbol ? '; ' + entry.symbol : ''));
    if ((entry.alt_titles || []).length) out.push('*Alternative titles; symbols*\n\n' + entry.alt_titles.join('  \n'));
    if ((entry.relationships || []).length) {
      out.push('### Phenotype-Gene Relationships');
      out.push(['| Location | Phenotype | Phenotype MIM number | Inheritance | Phenotype mapping key | Gene/Locus | Gene/Locus MIM number |', '|---|---|---|---|---|---|---|']
        .concat(entry.relationships.map((r) => '| ' + [r.location || '', r.phenotype || '', r.phenotype_mim || '', (r.inheritance || []).join(', '), r.mapping_key != null ? r.mapping_key : '', r.gene_symbol || '', r.gene_mim || ''].join(' | ') + ' |')).join('\n'));
    }
    out.push('### TEXT');
    if (entry.intro) { const t = text(entry.intro); if (t) out.push(t); }
    for (const sec of entry.sections || []) {
      const paras = (sec.paragraphs || []).map(text).filter(Boolean);
      if (paras.length) { out.push('### ' + (sec.heading || SECTION_HEADINGS[sec.name] || humanize(sec.name))); out.push.apply(out, paras); }
    }
    if ((entry.clinical_synopsis || []).length || (entry.inheritance || []).length) {
      out.push('### Clinical Synopsis');
      if ((entry.inheritance || []).length) out.push('**INHERITANCE**  \n- ' + entry.inheritance.map((c) => INHERITANCE[c] || c).join(', '));
      const groups = {};
      for (const it of entry.clinical_synopsis || []) (groups[it.category || 'Other'] = groups[it.category || 'Other'] || []).push(it);
      for (const c of Object.keys(groups).sort()) out.push('**' + c.toUpperCase() + '**  \n' + groups[c].map((it) => '- ' + (it.hpo_label || it.feature) + (it.hpo_id ? ' [' + it.hpo_id + ']' : '')).join('\n'));
    }
    const avs = [];
    for (const av of entry.allelic_variants || []) {
      const paras = (av.paragraphs || []).map(text).filter(Boolean);
      if (!paras.length && (av.paragraphs || []).length) continue; // every paragraph rejected
      avs.push('**.' + String(av.number || 0).padStart(4, '0') + ' ' + String(av.phenotype || '').toUpperCase() + '**  \n' + (av.name || '') + (av.hgvs && av.hgvs.length ? ' [' + av.hgvs.join('; ') + ']' : ''));
      avs.push.apply(avs, paras);
    }
    if (avs.length) { out.push('### ALLELIC VARIANTS'); out.push.apply(out, avs); }
    if ((entry.references || []).length) {
      out.push('### REFERENCES');
      out.push(entry.references.map((r, i) => (i + 1) + '. ' + (r.citation || r.label || 'PMID ' + r.pmid)).join('\n'));
    }
    out.push('---\n*Machine-drafted from the cited literature (' + stratLabel(s).toLowerCase() + '), run “' + RUN + '”. Curator review: ' +
      tally.accept + ' accepted, ' + tally.edit + ' edited, ' + tally.reject + ' rejected and removed, ' + tally.none + ' not yet reviewed. Exported ' + new Date().toISOString().slice(0, 10) + '.*');
    download('entry-' + safeName(item.mim || item.dir) + '-' + safeName(s) + '-reviewed.md', out.join('\n\n') + '\n', 'text/markdown');
  }

  // ------------------------------------------------------------------ gold comparison tab
  function parseTerm(s) {
    const m = /^(HP:\d+)\s*(.*)$/.exec(String(s || ''));
    return m ? { id: m[1], label: m[2] } : { id: null, label: String(s || '') };
  }
  function termList(list, emptyText) {
    if (!list || !list.length) return h('p', { class: 'small muted' }, emptyText);
    return h('ul', { class: 'plain-list' }, list.map((t) => { const x = parseTerm(t); return h('li', null, x.label || x.id, ' ', x.id ? hpoLink(x.id) : null); }));
  }
  function pmidList(item, list, emptyText) {
    if (!list.length) return h('p', { class: 'small muted' }, emptyText);
    return h('ul', { class: 'plain-list' }, list.map((pmid) => h('li', null, ext(pubmedUrl(pmid), paperLabel(item, pmid)), ' ', h('span', { class: 'muted mono' }, pmid), ' ', levelChip(paperLevel(item, pmid)))));
  }
  function citedByEntry(entry) {
    const seen = [];
    const push = (p) => { if (seen.indexOf(String(p)) < 0) seen.push(String(p)); };
    paragraphsOf(entry).forEach((x) => (x.p.pmids || []).forEach(push));
    (entry.relationships || []).forEach((r) => (r.pmids || []).forEach(push));
    return seen;
  }

  // Same text as evaluate._draft_text_for: the draft paragraphs citing any of the paragraph's papers.
  function draftTextFor(entry, pmids) {
    if (!entry) return '';
    const wanted = new Set((pmids || []).map(String));
    const hit = (p) => (p.pmids || []).some((x) => wanted.has(String(x)));
    const chunks = [];
    for (const sec of entry.sections || []) for (const p of sec.paragraphs || []) if (hit(p)) chunks.push('[' + (sec.heading || '') + '] ' + p.text);
    for (const av of entry.allelic_variants || []) for (const p of av.paragraphs || []) if (hit(p)) chunks.push('[Allelic variant ' + (av.name || '') + '] ' + p.text);
    return chunks.join('\n\n');
  }
  function draftFor(entry, gp) {
    if (typeof gp.draft === 'string') return gp.draft;
    if (gp._draft === undefined) gp._draft = draftTextFor(entry, gp.pmids);
    return gp._draft;
  }
  function goldTab(item, s, entry, ev) {
    const box = h('div', { class: 'section' });
    if (!ev) {
      box.append(h('div', { class: 'empty' }, h('strong', null, 'No comparison with OMIM for this draft. '),
        item.gold ? 'The OMIM gold standard was collected, but this draft was not scored against it.' : 'This is a new entry with no OMIM entry to compare against, or scoring was skipped for this run. The audit of each paragraph against its cited paper is still available under Review draft.'));
      return box;
    }
    const row = rowFor(item, s);
    box.append(h('p', { class: 'source-note' }, 'This view compares the ' + stratLabel(s).toLowerCase() + ' with the real OMIM entry' + (item.mim ? ' ' + item.mim : '') +
      '. OMIM’s reference paragraphs below are OMIM-authored text as distributed publicly through ClinVar (OMIM is a ClinVar submitter); HPO terms come from HPO’s annotation of the OMIM entry.'));
    box.append(h('div', { class: 'metric-grid' }, METRICS.map((m) => {
      let sub = null;
      if (m.key === 'claim_supported_rate' && isNum(row.claims)) sub = plural(row.claims, 'claim') + ' audited';
      if (m.key === 'gold_fact_coverage' && isNum(row.gold_facts)) sub = 'of ' + plural(row.gold_facts, 'OMIM fact');
      if (m.key === 'variant_recall' && ev.variants) sub = (ev.variants.n_matched || 0) + ' of ' + (ev.variants.n_gold || 0) + ' OMIM variants';
      if (m.key === 'ref_recall' && get(ev, 'references.cited.n_gold') != null) sub = (get(ev, 'references.cited.tp') || 0) + ' of ' + get(ev, 'references.cited.n_gold') + ' OMIM references';
      return h('div', { class: 'metric', title: m.help }, h('div', { class: 'm-label' }, m.label), h('div', { class: 'm-value' }, fmt(row[m.key], m.fmt)), sub ? h('div', { class: 'm-sub' }, sub) : null);
    }), h('div', { class: 'metric', title: ACCESS_HELP }, h('div', { class: 'm-label' }, 'OMIM refs readable'), h('div', { class: 'm-value', style: 'font-size:var(--fs-base)' }, accessEl(row.access)))));
    box.append(legend(false));

    // per-paragraph fact comparison
    const gt = ev.gold_text || {};
    const sec = h('section', { class: 'section', 'aria-labelledby': 'gt-h' }, h('h2', { id: 'gt-h' }, 'OMIM’s paragraphs and the draft, side by side'));
    if (!gt.n_paragraphs || !(gt.paragraphs || []).length) {
      sec.append(h('div', { class: 'empty' }, 'OMIM has deposited no per-paper paragraphs for this entry in ClinVar, so there is no text to compare. The other scores still apply.'));
    } else {
      sec.append(h('p', { class: 'small muted' }, 'A judge model split each OMIM paragraph into single facts and looked for each one in the draft paragraphs citing the same paper. Wording does not matter; facts do.'));
      const byLevel = gt.by_content_level || {};
      const lk = Object.keys(byLevel);
      if (lk.length) {
        sec.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
          h('caption', { class: 'visually-hidden' }, 'Fact coverage by how much of the paper could be read'),
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'How much of the paper was readable'), h('th', { class: 'n', scope: 'col' }, 'Facts'), h('th', { class: 'n', scope: 'col' }, 'Coverage'), h('th', { class: 'n', scope: 'col' }, 'Contradicted'))),
          h('tbody', null, lk.map((k) => h('tr', null, h('td', null, (LEVEL[k] || { label: humanize(k) }).label), h('td', { class: 'n' }, fmt(byLevel[k].n_facts, 'int')), h('td', { class: 'n' }, fmt(byLevel[k].coverage, 'pct')), h('td', { class: 'n' }, fmt(byLevel[k].contradicted, 'int'))))))));
      }
      gt.paragraphs.forEach((gp, i) => {
        const facts = gp.facts || [];
        sec.append(h('article', { class: 'gold-para', 'aria-label': 'OMIM paragraph ' + (i + 1) },
          h('div', { class: 'gold-para-head' },
            h('strong', null, (gp.pmids || []).length ? citeLinks(item, gp.pmids) : 'No paper cited'),
            levelChip(gp.content_level),
            h('span', { class: 'muted' }, isNum(gp.n_facts) && gp.n_facts ? (gp.present || 0) + ' present, ' + (gp.partial || 0) + ' partial, ' + (gp.absent || 0) + ' absent' + (gp.contradicted ? ', ' + gp.contradicted + ' contradicted' : '') + ' · coverage ' + fmt(gp.coverage, 'pct') : 'No facts judged')),
          h('div', { class: 'side-by-side' },
            h('div', null, h('div', { class: 'side-label' }, 'OMIM text (reference)'), h('div', { class: 'side-text' }, gp.reference || '')),
            h('div', null, h('div', { class: 'side-label' }, 'Draft text citing the same paper'), draftFor(entry, gp) ? h('div', { class: 'side-text' }, draftFor(entry, gp)) : h('div', { class: 'muted small' }, 'The draft has no paragraph citing this paper.'))),
          facts.length ? h('ul', { class: 'facts', 'aria-label': 'Facts in the OMIM paragraph' }, facts.map((f) => h('li', null,
            chip(FACT[f.status] || FACT.absent), h('span', null, f.fact || ''), f.note ? h('span', { class: 'note' }, f.note) : null))) : null));
      });
    }
    box.append(sec);

    // synopsis, variants, references, genes
    const syn = ev.synopsis || {};
    const goldIds = item.goldHpo ? Array.from(item.goldHpo) : [];
    const draftIds = (entry && entry.clinical_synopsis || []).map((x) => x.hpo_id).filter(Boolean);
    const shared = draftIds.filter((id) => item.goldHpo && item.goldHpo.has(id));
    const labelOf = (id) => { const t = (entry.clinical_synopsis || []).find((x) => x.hpo_id === id); return t ? t.hpo_label || t.feature : id; };
    box.append(h('section', { class: 'section' }, h('h2', null, 'Clinical synopsis (HPO terms)'),
      h('p', { class: 'small muted' }, plural(shared.length, 'term') + ' in both, ' + (syn.missed || []).length + ' in OMIM’s annotation only, ' + (syn.extra || []).length + ' in the draft only' + (goldIds.length ? ' (OMIM annotation has ' + plural(goldIds.length, 'phenotype term') + ')' : '') + '.'),
      h('div', { class: 'two-col' },
        h('div', { class: 'box' }, h('h3', null, 'In OMIM’s annotation, missing from the draft'), termList(syn.missed, 'None missed.')),
        h('div', { class: 'box' }, h('h3', null, 'In the draft, not in OMIM’s annotation'), termList(syn.extra, 'None extra.'))),
      shared.length ? h('div', { class: 'box' }, h('h3', null, 'In both'), termList(shared.map((id) => id + ' ' + labelOf(id)), '')) : null));

    const va = ev.variants || {};
    box.append(h('section', { class: 'section' }, h('h2', null, 'Allelic variants'),
      h('div', { class: 'two-col' },
        h('div', { class: 'box' }, h('h3', null, 'Matched (' + (va.matched || []).length + ')'),
          (va.matched || []).length ? h('ul', { class: 'plain-list' }, va.matched.map((m) => h('li', null, h('span', { class: 'mono' }, m.gold), h('span', { class: 'muted' }, ' ↔ draft: '), h('span', { class: 'mono' }, m.generated)))) : h('p', { class: 'small muted' }, 'None.')),
        h('div', { class: 'box' }, h('h3', null, 'OMIM variants missing from the draft (' + (va.missed || []).length + ')'),
          (va.missed || []).length ? h('ul', { class: 'plain-list mono' }, va.missed.map((m) => h('li', null, m))) : h('p', { class: 'small muted' }, 'None missed.'))),
      (va.not_in_omim || []).length ? h('div', { class: 'box' }, h('h3', null, 'In the draft, not listed by OMIM (' + va.not_in_omim.length + ')'),
        h('p', { class: 'small muted' }, 'Not necessarily wrong: OMIM lists only selected variants. Check the evidence before accepting.'),
        h('ul', { class: 'plain-list mono' }, va.not_in_omim.map((m) => h('li', null, m)))) : null));

    const goldRefs = (item.gold && item.gold.cited_pmids || []).map(String);
    const cited = entry ? citedByEntry(entry) : [];
    const missedRefs = goldRefs.filter((p) => cited.indexOf(p) < 0);
    const extraRefs = cited.filter((p) => goldRefs.indexOf(p) < 0);
    box.append(h('section', { class: 'section' }, h('h2', null, 'References'),
      h('p', { class: 'small muted' }, 'OMIM cites ' + plural(goldRefs.length, 'paper') + '; the draft cites ' + plural(cited.length, 'paper') + ', ' + (cited.length - extraRefs.length) + ' of them also cited by OMIM.'),
      h('div', { class: 'two-col' },
        h('div', { class: 'box' }, h('h3', null, 'Cited by OMIM, not by the draft (' + missedRefs.length + ')'), pmidList(item, missedRefs, 'None.')),
        h('div', { class: 'box' }, h('h3', null, 'Cited by the draft, not by OMIM (' + extraRefs.length + ')'), pmidList(item, extraRefs, 'None.')))));

    const ge = ev.genes || {}; const inh = ev.inheritance || {};
    const inhNames = (codes) => (codes || []).length ? codes.map((c) => INHERITANCE[c] || c).join(', ') : '–';
    box.append(h('section', { class: 'section' }, h('h2', null, 'Genes and inheritance'),
      h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, ''), h('th', { scope: 'col' }, 'Draft'), h('th', { scope: 'col' }, 'OMIM'), h('th', { scope: 'col' }, 'Result'))),
        h('tbody', null,
          h('tr', null, h('th', { scope: 'row' }, 'Causal gene(s)'), h('td', null, (ge.predicted || []).join(', ') || '–'), h('td', null, (ge.gold || []).join(', ') || '–'), h('td', null, 'F1 ' + fmt(ge.f1, 'f1'))),
          h('tr', null, h('th', { scope: 'row' }, 'Inheritance'), h('td', null, inhNames(inh.predicted)), h('td', null, inhNames(inh.gold)),
            h('td', null, inh.match === true ? chip({ cls: 'ok', icon: '✓', label: 'Match' }) : inh.match === false ? chip({ cls: 'bad', icon: '✗', label: 'Mismatch' }) : '–')))))));

    if (ev.omim_text && ev.omim_text.sections) {
      const secs = ev.omim_text.sections;
      box.append(h('section', { class: 'section' }, h('h2', null, 'Full OMIM text, section by section'),
        h('p', { class: 'small muted' }, 'Each section of the OMIM entry text (from the OMIM API) split into facts and looked for anywhere in the draft. Overall coverage ' + fmt(ev.omim_text.coverage, 'pct') + '.'),
        h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
          h('thead', null, h('tr', null, ['OMIM section', 'Facts', 'Coverage', 'Contradicted', 'Draft has this section'].map((t, i) => h('th', { scope: 'col', class: i && i < 4 ? 'n' : null }, t)))),
          h('tbody', null, Object.keys(secs).map((k) => h('tr', null, h('td', null, SECTION_HEADINGS[k] || humanize(k)), h('td', { class: 'n' }, fmt(secs[k].n_facts, 'int')),
            h('td', { class: 'n' }, fmt(secs[k].coverage, 'pct')), h('td', { class: 'n' }, fmt(secs[k].contradicted, 'int')), h('td', null, secs[k].has_namesake_section ? 'Yes' : 'No'))))))));
    }
    return box;
  }

  // ------------------------------------------------------------------ evidence tab
  function evidenceTab(item) {
    const box = h('div', { class: 'section' });
    const r = item.retrieval;
    if (r) {
      box.append(h('p', { class: 'source-note' }, r.mode === 'oracle' ? 'Papers: the references the OMIM entry already cites.' : r.mode === 'open' ? 'Papers: chosen by a literature search' + ((r.queries || []).length ? ' (' + plural(r.queries.length, 'query', 'queries') + ')' : '') + '.' : '',
        (r.missing || []).length ? ' ' + plural(r.missing.length, 'paper') + ' could not be retrieved: ' + r.missing.join(', ') + '.' : ''));
    }
    const papers = item.papers || [];
    const sec = h('section', { class: 'section', 'aria-labelledby': 'pp-h' }, h('h2', { id: 'pp-h' }, 'Papers read (' + papers.length + ')'));
    if (!papers.length) sec.append(h('div', { class: 'empty' }, 'No paper list was saved for this entry.'));
    else {
      sec.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Paper'), h('th', { class: 'n', scope: 'col' }, 'Year'), h('th', { scope: 'col' }, 'Journal'),
          h('th', { scope: 'col' }, h('abbr', { title: 'How central the paper is to this entry, as judged when its facts were extracted' }, 'Relevance')),
          h('th', { scope: 'col' }, 'Readable'), h('th', { class: 'n', scope: 'col' }, h('abbr', { title: 'Facts extracted with a supporting quote that was found in the paper' }, 'Facts kept')),
          h('th', { class: 'n', scope: 'col' }, h('abbr', { title: 'Facts discarded because their supporting quote could not be found in the paper' }, 'Dropped')), h('th', { scope: 'col' }, 'PubMed'))),
        h('tbody', null, papers.map((p) => {
          const ex = item.extractionBy.get(String(p.pmid));
          return h('tr', null,
            h('td', { style: 'min-width:260px' }, h('strong', null, p.label || ('PMID ' + p.pmid)), p.title ? h('div', { class: 'small muted' }, p.title) : null, ex && ex.error ? h('div', { class: 'small', style: 'color:var(--bad)' }, 'Extraction failed: ' + ex.error) : null),
            h('td', { class: 'n' }, p.year || '–'), h('td', null, p.journal || '–'),
            h('td', { title: ex && ex.relevance_reason ? ex.relevance_reason : null }, ex ? RELEVANCE[ex.relevance] || humanize(ex.relevance) : '–'),
            h('td', null, levelChip(p.content_level)),
            h('td', { class: 'n' }, ex ? String((ex.findings || []).length) : '–'), h('td', { class: 'n' }, ex ? String(ex.n_dropped || 0) : '–'),
            h('td', null, ext(pubmedUrl(p.pmid), p.pmid)));
        })))));
    }
    box.append(sec);

    const kg = item.kg;
    const ksec = h('section', { class: 'section', 'aria-labelledby': 'kg-h' }, h('h2', { id: 'kg-h' }, 'What the evidence graph established'),
      h('p', { class: 'small muted' }, 'Built from the extracted facts before the evidence-graph draft was written. Each row lists the papers that support linking it to this entry.'));
    if (!kg || !(kg.entities || []).length) ksec.append(h('div', { class: 'empty' }, 'No evidence graph for this entry (only the evidence-graph draft builds one).'));
    else {
      add(ksec, evidenceGraph(item));
      ksec.append(h('p', { class: 'small muted kg-phone-note' }, 'The graph picture is shown on wider screens. The tables below list the same links.'));
      const groups = [
        { rel: 'caused_by', title: 'Causal genes' }, { rel: 'has_variant', title: 'Variants' },
        { rel: 'inheritance', title: 'Mode of inheritance' }, { rel: 'has_phenotype', title: 'Phenotypes' },
      ];
      for (const g of groups) {
        const rows = kg.entities.filter((e) => e.rel === g.rel).sort((a, b) => (b.pmids || []).length - (a.pmids || []).length);
        ksec.append(h('h3', { style: 'font-size:var(--fs-md);margin-top:8px' }, g.title + ' (' + rows.length + ')'));
        if (!rows.length) { ksec.append(h('p', { class: 'small muted' }, 'None.')); continue; }
        ksec.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, g.rel === 'has_phenotype' ? 'Feature' : 'Name'), g.rel === 'has_phenotype' ? h('th', { scope: 'col' }, 'HPO') : null,
            h('th', { class: 'n', scope: 'col' }, 'Papers'), h('th', { scope: 'col' }, 'Supported by'), g.rel === 'has_phenotype' ? h('th', { scope: 'col' }, 'Reported absent in') : null)),
          h('tbody', null, rows.map((e) => h('tr', null,
            h('td', null, g.rel === 'inheritance' ? (e.label || e.id) : g.rel === 'has_variant' ? h('span', { class: 'mono' }, e.omim_name ? e.omim_name + ' · ' : '', e.label) : e.label || e.id),
            g.rel === 'has_phenotype' ? h('td', null, hpoLink(e.hpo_id) || '–') : null,
            h('td', { class: 'n' }, String((e.pmids || []).length)),
            h('td', { class: 'small' }, (e.pmids || []).length ? citeLinks(item, e.pmids) : '–'),
            g.rel === 'has_phenotype' ? h('td', { class: 'small' }, (e.absent_in || []).length ? citeLinks(item, e.absent_in) : '–') : null))))));
      }
    }
    box.append(ksec);

    const kgEntry = item.entries.kg || Object.values(item.entries).find((e) => e.meta && e.meta.extraction) || null;
    const x = kgEntry && kgEntry.meta ? kgEntry.meta.extraction : null;
    const st = (kg && kg.stats) || (kgEntry && kgEntry.meta && kgEntry.meta.kg) || null;
    const ssec = h('section', { class: 'section' }, h('h2', null, 'Extraction statistics'));
    if (!x && !st) ssec.append(h('div', { class: 'empty' }, 'No extraction statistics were saved for this entry.'));
    else {
      const kv = h('dl', { class: 'kv' });
      const row = (k, v) => kv.append(h('dt', null, k), h('dd', null, v));
      if (x) {
        row('Facts kept', fmt(x.findings_kept, 'int'));
        row('Facts dropped (quote not found in paper)', fmt(x.findings_dropped_ungrounded, 'int'));
        row('Quote grounding rate', fmt(x.quote_grounding_rate, 'pct'));
        if (x.papers_by_relevance) row('Papers by relevance', Object.keys(x.papers_by_relevance).map((k) => (RELEVANCE[k] || k) + ': ' + x.papers_by_relevance[k]).join(', '));
        if ((x.papers_failed || []).length) row('Papers that failed extraction', x.papers_failed.join(', '));
        if (x.hpo_resolution && typeof x.hpo_resolution === 'object') row('HPO term resolution', Object.keys(x.hpo_resolution).map((k) => humanize(k) + ': ' + x.hpo_resolution[k]).join(', '));
      }
      const plc = kgEntry && kgEntry.meta && kgEntry.meta.papers_by_content_level;
      if (plc) row('Papers by readable level', Object.keys(plc).map((k) => (LEVEL[k] ? LEVEL[k].label : k) + ': ' + plc[k]).join(', '));
      if (st && st.nodes) row('Graph nodes', Object.keys(st.nodes).map((k) => k + ' ' + st.nodes[k]).join(', '));
      if (st && st.edges) row('Graph links', Object.keys(st.edges).map((k) => humanize(k).toLowerCase() + ' ' + st.edges[k]).join(', '));
      ssec.append(kv);
    }
    const u = item.usage && item.usage.total;
    if (u) ssec.append(h('p', { class: 'small muted' }, 'Model use for this entry: ' + plural(u.calls || 0, 'call') + ', ' + ((u.input_tokens || 0) + (u.output_tokens || 0)).toLocaleString('en-US') + ' tokens' + (isNum(u.list_price_usd) ? ', about $' + u.list_price_usd.toFixed(2) : '') + (isNum(item.usage.wall_seconds) ? ', ' + Math.round(item.usage.wall_seconds) + ' s' : '') + '.'));
    box.append(ssec);
    return box;
  }

  // ------------------------------------------------------------------ proposed updates
  function updatesBlock(item) {
    const u = item.updates;
    const frag = h('div', { class: 'section' });
    if (!u) return frag;
    const props = u.proposals || [];
    frag.append(h('p', { class: 'lede' }, 'Newer literature that the entry does not cite' + (u.since ? ', from ' + u.since + ' on' : '') + ': ' +
      plural(u.n_screened || 0, 'paper') + ' screened, ' + (u.n_read || 0) + ' read, ' + plural(props.length, 'proposal') + '. Each proposal is a draft for you to accept, edit or reject; its paragraphs were audited against the new paper.'));
    const b = u.backtest;
    if (b) {
      const pr = b.proposed || {};
      frag.append(h('div', { class: 'box' }, h('h3', null, 'Back-test: the entry as it stood before ' + u.as_of),
        h('p', { class: 'small' }, 'OMIM’s curators later added ' + plural((b.held_out || []).length, 'reference') + ' from ' + u.as_of + ' on. This run proposed ' + (b.found || []).length + ' of them (recall ' + fmt(pr.recall, 'pct') + ', precision ' + fmt(pr.precision, 'pct') + ').'),
        h('dl', { class: 'kv' },
          h('dt', null, 'Found in screening'), h('dd', null, fmt(get(b, 'screened.recall'), 'pct') + ' of held-out references'),
          h('dt', null, 'Read in full'), h('dd', null, fmt(get(b, 'read.recall'), 'pct')),
          h('dt', null, 'Proposed'), h('dd', null, fmt(pr.recall, 'pct')),
          (b.missed || []).length ? [h('dt', null, 'Missed'), h('dd', null, citeLinks(item, b.missed))] : null)));
    }
    if (!props.length) { frag.append(h('div', { class: 'empty' }, 'No newer paper warranted an update.')); return frag; }
    for (const p of props) {
      frag.append(h('article', { class: 'proposal' },
        h('div', { class: 'proposal-head' },
          h('div', { class: 'chips' }, h('span', { class: 'chip prio-' + p.priority }, String(p.priority || '').toUpperCase() + ' priority'),
            (p.update_types || []).map((t) => plainChip(humanize(t))), levelChip(p.content_level)),
          h('div', null, h('strong', null, ext(pubmedUrl(p.pmid), p.label || ('PMID ' + p.pmid))), p.citation ? h('div', { class: 'small muted' }, p.citation) : null),
          h('p', null, h('strong', null, 'Why: '), p.rationale || '')),
        h('div', { class: 'proposal-body' },
          (p.paragraphs || []).map((pp) => h('div', { class: 'prop-para' },
            h('div', { class: 'chips' }, plainChip(SECTION_HEADINGS[pp.section] || humanize(pp.section), 'info'), chip(STATUS[pp.status] || STATUS.unverified)),
            h('div', { class: 'side-text' }, pp.text || ''),
            (pp.checks || []).length ? h('details', { class: 'more' }, h('summary', null, 'Audit of ' + plural(pp.checks.length, 'claim')),
              h('ul', { class: 'claims' }, pp.checks.map((c) => { const v = VERDICT[c.verdict] || VERDICT.not_checkable; return h('li', { class: 'v-' + v.cls }, chip(v), h('div', { class: 'claim-text' }, c.claim || ''), c.evidence_quote ? h('blockquote', { class: 'quote' }, c.evidence_quote) : null, c.explanation ? h('div', { class: 'small' }, c.explanation) : null); }))) : null)),
          (p.evidence || []).length ? h('details', { class: 'more' }, h('summary', null, 'Evidence from the paper (' + plural(p.evidence.length, 'fact') + ')'),
            h('ul', { class: 'findings' }, p.evidence.map((f) => h('li', null, h('div', null, f.statement || ''), (f.quotes || []).map((q) => h('blockquote', { class: 'quote' }, q)))))) : null)));
    }
    return frag;
  }
  function viewAllUpdates() {
    const wrap = h('div', { class: 'wrap' });
    wrap.append(h('div', { class: 'page-head' }, h('div', { class: 'eyebrow' }, 'Run “' + RUN + '”'), h('h1', { class: 'page-title' }, 'Proposed updates'),
      h('p', { class: 'lede' }, 'Suggested additions to existing entries from literature published after the entry’s references. Machine-drafted and not reviewed.')));
    const items = ENTRIES.filter((it) => it.has_updates);
    if (!items.length) { wrap.append(h('div', { class: 'empty' }, 'This run proposed no updates.')); return wrap; }
    for (const it of items) {
      let body;
      if (it.loaded) body = updatesBlock(it);
      else if (it.loadError) body = h('div', { class: 'empty load-error', role: 'alert' }, h('strong', null, 'Could not load this entry. '), it.loadError);
      else {
        body = h('div', { class: 'loading', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading…');
        loadEntry(it).then(() => rerenderIfShowing(it), () => rerenderIfShowing(it));
      }
      wrap.append(h('section', { class: 'section' }, h('h2', null, h('a', { href: entryHash(it, 'updates') }, itemName(it))), body));
    }
    return wrap;
  }

  // ------------------------------------------------------------------ boot
  loadDecisions();
  buildJump();
  window.addEventListener('hashchange', () => { state.exportBox = null; render(); });
  const onWide = () => render({ keepScroll: true });
  if (wide.addEventListener) wide.addEventListener('change', onWide);
  render();
})();
