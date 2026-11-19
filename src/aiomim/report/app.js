/* OMIM draft review page. Vanilla JS, no dependencies.
   All data comes from the JSON block #report-data; every string from it is inserted with
   textContent / setAttribute through h(), never as HTML.
   The page knows nothing about particular generation strategies: their names, labels, summaries
   and which of them is a control all come from the data (DATA.strategy_info), and an entry may
   have a draft from any subset of them. */
(function () {
  'use strict';

  // ------------------------------------------------------------------ data
  let DATA;
  try { DATA = JSON.parse(document.getElementById('report-data').textContent || '{}'); }
  catch (e) { DATA = {}; }
  const ENTRIES = Array.isArray(DATA.entries) ? DATA.entries : [];
  const RUN = String(DATA.run || 'run');

  // Strategies come from the data (strategies.json, or the pipeline's registry at build time),
  // so the page works for any number of them. A control is a yardstick, not a way to write entries.
  const SINFO = new Map();
  (Array.isArray(DATA.strategy_info) ? DATA.strategy_info : []).forEach((i) => { if (i && i.name) SINFO.set(i.name, i); });
  const STRATS = Array.isArray(DATA.strategies) ? DATA.strategies : [];
  const BASELINE = DATA.baseline && STRATS.indexOf(DATA.baseline) >= 0 ? DATA.baseline : null;
  const stratInfo = (s) => SINFO.get(s) || { name: s, label: String(s), summary: '', control: false };
  const stratLabel = (s) => stratInfo(s).label;
  const stratAbout = (s) => stratInfo(s).summary || '';
  const isControl = (s) => !!stratInfo(s).control;
  // The label without a trailing "(control)", for places where a Control tag is shown beside it.
  const stratName = (s) => stratLabel(s).replace(/\s*\(control\)\s*$/i, '') || stratLabel(s);
  // Strategy names go into the link hash, which may hold only letters, digits and hyphens.
  const stratSlug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'draft';
  const draftName = (s) => 'the “' + stratName(s) + '” draft' + (isControl(s) ? ' (a control)' : '');

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
    item.recordBy = new Map();
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
    // The build stores some things once and leaves the rest to be filled in here:
    // a reference that repeats the paper list keeps only its PMID,
    for (const s of Object.keys(item.entries)) for (const r of item.entries[s].references || []) {
      const p = item.paperBy.get(String(r.pmid));
      if (p) {
        if (r.citation === undefined && p.reference) r.citation = p.reference;
        if (r.label === undefined && p.label) r.label = p.label;
        if (r.content_level === undefined && p.content_level) r.content_level = p.content_level;
      }
      item.refBy.set(String(r.pmid), r);
    }
    // OMIM's paragraph text is kept once per entry (gold_refs), and per-paragraph tallies are recounted.
    const refs = Array.isArray(item.gold_refs) ? item.gold_refs : [];
    for (const s of Object.keys(item.evals)) for (const gp of get(item.evals[s], 'gold_text.paragraphs') || []) {
      if (gp.reference === undefined && isNum(gp.ref)) gp.reference = refs[gp.ref] || '';
      if (gp.n_facts === undefined && Array.isArray(gp.facts)) Object.assign(gp, tallyFacts(gp.facts));
    }
    // Case-table records and notes, for paragraphs of a "case table first" draft.
    item.recordBy = new Map();
    for (const r of get(item, 'cohort.records') || []) item.recordBy.set(r.id, r);
    for (const n of get(item, 'cohort.notes') || []) item.recordBy.set(n.id, n);
    item.loaded = true;
    item.loadError = null;
  }
  // Same arithmetic as evaluate._tally.
  function tallyFacts(facts) {
    const c = { present: 0, partial: 0, absent: 0, contradicted: 0 };
    for (const f of facts) if (c[f.status] !== undefined) c[f.status]++;
    const n = facts.length;
    const r3 = (v) => Math.round(v * 1000) / 1000;
    return { n_facts: n, present: c.present, partial: c.partial, absent: c.absent, contradicted: c.contradicted,
      coverage: n ? r3((c.present + 0.5 * c.partial) / n) : null, strict_coverage: n ? r3(c.present / n) : null,
      contradiction_rate: n ? r3(c.contradicted / n) : null };
  }
  window.__aiomimRegister = function (file, payload) {
    const item = byFile.get(String(file));
    if (item && !item.loaded && payload && typeof payload === 'object') attach(item, payload);
  };
  if (DATA.payloads) for (const f of Object.keys(DATA.payloads)) window.__aiomimRegister(f, DATA.payloads[f]);
  delete DATA.payloads;
  // A large single-file page carries each entry gzip-compressed (base64); it is unpacked when opened.
  const PACKED = DATA.packed && typeof DATA.packed === 'object' ? DATA.packed : {};
  function unpack(b64) {
    if (typeof DecompressionStream !== 'function' || typeof Response !== 'function') {
      return Promise.reject(new Error('This browser cannot unpack the entry data stored in this page. Open the page in a current version of Chrome, Edge, Firefox or Safari.'));
    }
    return Promise.resolve().then(() => {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    }).then((text) => JSON.parse(text));
  }

  const pending = new Map();
  function loadEntry(item) {
    if (item.loaded) return Promise.resolve(item);
    if (pending.has(item.key)) return pending.get(item.key);
    const pr = PACKED[item.file] ? unpack(PACKED[item.file]).then((payload) => {
      attach(item, payload);
      delete PACKED[item.file];
      return item;
    }, (e) => { throw new Error(e && e.message ? e.message : 'The entry data in this page could not be unpacked.'); }) : new Promise((resolve, reject) => {
      if (!item.file) { reject(new Error('This entry has no data file.')); return; }
      const el = document.createElement('script');
      el.src = DATA_DIR + '/' + encodeURIComponent(item.file);
      el.async = true;
      el.onload = () => { el.remove(); if (item.loaded) resolve(item); else reject(new Error('The data file ' + DATA_DIR + '/' + item.file + ' loaded but contained no entry data.')); };
      el.onerror = () => { el.remove(); reject(new Error('The data file ' + DATA_DIR + '/' + item.file + ' could not be loaded.')); };
      document.head.append(el);
    });
    pending.set(item.key, pr);
    // Re-render exactly once per load. Views call loadEntry() on every render while an
    // entry is pending; attaching the re-render there would stack one more handler per
    // render, and a view that loads several entries would re-render exponentially.
    pr.then(() => { pending.delete(item.key); rerenderIfShowing(item); },
            (e) => { pending.delete(item.key); item.loadError = e.message; rerenderIfShowing(item); });
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
    overviewStrategy: STRATS[0] || null,
    overviewMode: 'strategy',   // 'strategy': every score of one strategy; 'metric': one score across strategies
    overviewMetric: 'claim_supported_rate',
    open: new Set(),            // disclosure blocks the reader opened, kept across re-renders
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
    if (!raw || raw === 'overview' || raw === 'main') return { view: 'overview', panel: 'scores' };
    if (raw.indexOf('overview--') === 0) return { view: 'overview', panel: raw.slice(10) };
    if (raw === 'updates') return { view: 'updates' };
    if (raw.indexOf('entry-') === 0) {
      const parts = raw.slice(6).split('--');
      const item = byKey.get(parts[0]);
      if (!item) return { view: 'missing' };
      let strategy = (parts[2] && item.strategies.find((x) => stratSlug(x) === parts[2])) || item.strategies[0] || null;
      let tab = ['review', 'gold', 'evidence', 'updates'].indexOf(parts[1]) >= 0 ? parts[1] : 'review';
      if (tab === 'review' && !strategy && item.has_updates) tab = 'updates';
      return { view: 'entry', item: item, tab: tab, strategy: strategy };
    }
    return { view: 'overview', panel: 'scores' };
  }
  function entryHash(item, tab, strategy) {
    let out = 'entry-' + item.key;
    const s = strategy && strategy !== item.strategies[0] ? strategy : null;
    if ((tab && tab !== 'review') || s) out += '--' + (tab || 'review');
    if (s) out += '--' + stratSlug(s);
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
    else view = viewOverview(route);
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
  const CMP_PANELS = [
    { id: 'scores', label: 'Scores' },
    { id: 'baseline', label: 'Against the baseline' },
    { id: 'breakdowns', label: 'By paper access and entry type' },
    { id: 'totals', label: 'Totals' },
    { id: 'cost', label: 'Cost' },
  ];
  function tag(text, cls, title) { return h('span', { class: 'tag ' + (cls || ''), title: title || null }, text); }
  const controlTag = () => tag('Control', 'tag-control', 'A control, not a method: it is there to compare against, not to produce entries.');
  const baselineTag = () => tag('Baseline', 'tag-baseline', 'The strategy the others are compared against.');
  // A strategy's name with its Control / Baseline tags, for table headers, buttons and lists.
  function stratTitle(s, withBaseline) {
    return [h('span', { class: 'strat-name' }, stratName(s)), isControl(s) ? controlTag() : null, withBaseline && s === BASELINE ? baselineTag() : null];
  }
  const ctl = (s, cls) => (cls || '') + (isControl(s) ? ' ctl' : '');
  function listWords(words) {
    if (words.length < 2) return words.join('');
    return words.slice(0, -1).join(', ') + ' and ' + words[words.length - 1];
  }
  function strategyList(compared) {
    const listed = new Map(((compared && compared.strategies) || []).map((x) => [x.name, x]));
    return h('dl', { class: 'strat-list' }, STRATS.map((s) => {
      const info = stratInfo(s);
      const bits = [];
      if (isNum(info.n_drafts)) bits.push('drafted for ' + plural(info.n_drafts, 'entry', 'entries'));
      if (isNum(info.n_scored) && info.n_scored !== info.n_drafts) bits.push(info.n_scored + ' scored against OMIM');
      return [h('dt', null, stratTitle(s, true)),
        h('dd', null, stratAbout(s), bits.length ? h('span', { class: 'muted' }, (stratAbout(s) ? ' ' : '') + '(' + bits.join(', ') + ')') : null)];
    }));
  }

  function viewOverview(route) {
    const wrap = h('div', { class: 'wrap' });
    const strategies = STRATS;
    const n = ENTRIES.length;
    const dates = DATA.generated || [];
    const retrieval = DATA.retrieval === 'oracle'
      ? 'from the papers each OMIM entry already cites'
      : DATA.retrieval === 'open' ? 'from papers chosen by a literature search' : 'from the published literature';
    const methods = strategies.filter((s) => !isControl(s));
    const controls = strategies.filter(isControl);
    let how = '';
    if (strategies.length === 1) how = 'Each entry was written one way: ' + stratName(strategies[0]) + '.';
    else if (strategies.length > 1) {
      how = 'Entries were written in ' + (methods.length === 1 ? 'one way' : methods.length + ' different ways') + ' (' + listWords(methods.map(stratName)) + ')' +
        (controls.length ? ', plus ' + (controls.length === 1 ? 'a control' : controls.length + ' controls') + ' (' + listWords(controls.map(stratName)) + ')' : '') +
        ', so the drafts can be compared.';
    }
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

    if (DATA.compared) wrap.append(comparedSection(DATA.compared, route && route.panel));
    else if (DATA.comparison) wrap.append(comparisonFromFile(DATA.comparison));
    else if (strategies.length > 1) wrap.append(comparisonSection(strategies));

    wrap.append(entriesSection(strategies));

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
  // One button per strategy; `list` is whatever strategies apply (the run's, or one entry's).
  function strategySwitch(list, current, onPick, fidPrefix) {
    return h('div', { class: 'seg', role: 'group', 'aria-label': 'Which draft to show' },
      list.map((s) => h('button', { type: 'button', 'aria-pressed': String(s === current), 'data-fid': fidPrefix + s, title: stratAbout(s) || null,
        class: isControl(s) ? 'is-control' : null, onclick: () => onPick(s) }, stratTitle(s))));
  }

  // Scores by entry: either every score of one strategy, or one score across all strategies.
  function entriesSection(strategies) {
    const s = strategies.indexOf(state.overviewStrategy) >= 0 ? state.overviewStrategy : strategies[0];
    const sec = h('section', { class: 'section', 'aria-labelledby': 'scores-h', id: 'entries' });
    sec.append(h('div', { class: 'section-head' }, h('h2', { id: 'scores-h' }, 'Scores by entry')));
    const byMetric = strategies.length > 1 && state.overviewMode === 'metric';
    if (strategies.length > 1) {
      const controls = h('div', { class: 'entry-controls' },
        h('div', { class: 'seg', role: 'group', 'aria-label': 'What the table shows' },
          h('button', { type: 'button', 'aria-pressed': String(!byMetric), 'data-fid': 'ov-mode-strategy',
            onclick: () => { state.overviewMode = 'strategy'; render({ keepScroll: true, focus: 'ov-mode-strategy' }); } }, 'All scores of one strategy'),
          h('button', { type: 'button', 'aria-pressed': String(byMetric), 'data-fid': 'ov-mode-metric',
            onclick: () => { state.overviewMode = 'metric'; render({ keepScroll: true, focus: 'ov-mode-metric' }); } }, 'One score, every strategy')));
      if (byMetric) {
        controls.append(h('label', { class: 'check' }, 'Score ',
          h('select', { id: 'ov-metric', 'data-fid': 'ov-metric', onchange: (e) => { state.overviewMetric = e.target.value; render({ keepScroll: true, focus: 'ov-metric' }); } },
            METRICS.map((m) => h('option', { value: m.key, selected: m.key === state.overviewMetric || null }, m.label)))));
      } else {
        controls.append(strategySwitch(strategies, s, (v) => { state.overviewStrategy = v; render({ keepScroll: true, focus: 'ov-strat-' + v }); }, 'ov-strat-'));
      }
      sec.append(controls);
    }
    if (byMetric) {
      const m = METRICS.find((x) => x.key === state.overviewMetric) || METRICS[0];
      sec.append(h('p', { class: 'small muted' }, m.label + ': ' + m.help + ' Select a number to open that draft of the entry.'));
      sec.append(metricTable(strategies, m));
    } else {
      if (strategies.length) sec.append(h('p', { class: 'small muted' }, 'Showing ' + draftName(s) + '. ' + stratAbout(s) + ' Select an entry to review it.'));
      else sec.append(h('p', { class: 'small muted' }, 'No entry of this run has a draft yet.'));
      sec.append(scoreTable(s || '', strategies.length > 1));
    }
    sec.append(legend(false));
    return sec;
  }
  // Fallback comparison when the run has no comparison file: plain averages from the entry index.
  function comparisonSection(strategies) {
    const means = {};
    for (const s of strategies) means[s] = meanRow(ENTRIES.filter((it) => it.strategies.indexOf(s) >= 0).map((it) => rowFor(it, s)));
    const tbody = h('tbody');
    for (const m of METRICS) {
      tbody.append(h('tr', null, h('th', { scope: 'row' }, h('abbr', { title: m.help }, m.label), dirMark(m.better !== 'low')),
        strategies.map((s) => h('td', { class: ctl(s, 'n') }, fmt(means[s][m.key], m.fmt)))));
    }
    return h('section', { class: 'section', 'aria-labelledby': 'cmp-h' },
      h('h2', { id: 'cmp-h' }, strategies.length === 2 ? 'The two drafts compared' : 'The strategies compared'),
      h('p', { class: 'small muted' }, 'Plain averages over the entries each strategy drafted in this run (facts contradicted is a total), so the columns may rest on different entries. ' +
        '↑ higher is better, ↓ lower is better. Run “aiomim compare” for paired differences with confidence intervals.'),
      strategyList(null),
      h('div', { class: 'table-scroll' + (strategies.length <= 3 ? ' compare' : '') }, h('table', { class: 'data cmp' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Score'), strategies.map((s) => h('th', { class: ctl(s, 'n'), scope: 'col' }, stratTitle(s))))),
        tbody)));
  }
  function draftCount(item) {
    const have = item.strategies.filter((x) => (item.rows[x] || {}).has_draft !== false);
    return h('span', { title: have.length ? have.map(stratName).join(', ') : null }, have.length + ' of ' + STRATS.length);
  }
  function entryCell(item, href, note) {
    return h('td', { class: 'entry-cell' },
      h('a', { href: href }, itemName(item)),
      !item.mim ? h('div', { class: 'small muted' }, 'New entry, no OMIM entry to compare with') : null,
      !item.strategies.length ? h('div', { class: 'small muted' }, 'No draft yet: still being written, or drafting failed') : note || null);
  }
  function scoreTable(s, showDrafts) {
    const rows = ENTRIES.map((it) => ({ item: it, row: rowFor(it, s) }));
    const tbody = h('tbody');
    for (const { item, row } of rows) {
      const href = entryHash(item, 'review', item.strategies.indexOf(s) >= 0 ? s : null);
      const tr = h('tr', { class: 'clickable', onclick: (e) => { if (!e.target.closest('a')) location.hash = href; } },
        entryCell(item, href, !row.has ? h('div', { class: 'small muted' }, 'No “' + stratName(s) + '” draft for this entry') : null),
        showDrafts ? h('td', { class: 'n' }, draftCount(item)) : null,
        h('td', null, item.strategies.indexOf(s) >= 0 && (item.pids[s] || []).length ? progressEl(item, s) : '–'),
        METRICS.map((m) => h('td', { class: 'n' }, fmt(row[m.key], m.fmt))),
        h('td', null, accessEl(row.access)));
      tbody.append(tr);
    }
    const mean = meanRow(rows.map((r) => r.row));
    tbody.append(h('tr', { class: 'mean' }, h('td', null, 'Mean of entries with a value'), showDrafts ? h('td', null, '') : null, h('td', null, ''),
      METRICS.map((m) => h('td', { class: 'n' }, fmt(mean[m.key], m.fmt))), h('td', null, '')));
    return h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
      h('caption', { class: 'visually-hidden' }, 'Scores for each entry' + (s ? ', ' + stratLabel(s) : '')),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Entry'),
        showDrafts ? h('th', { class: 'n', scope: 'col' }, h('abbr', { title: 'How many of the run’s strategies have a draft of this entry' }, 'Drafts')) : null,
        h('th', { scope: 'col' }, 'Your review'),
        METRICS.map(headerCell), h('th', { scope: 'col' }, h('abbr', { title: ACCESS_HELP }, 'OMIM refs readable')))),
      tbody));
  }
  function metricTable(strategies, m) {
    const tbody = h('tbody');
    const cols = {};
    for (const s of strategies) cols[s] = [];
    for (const item of ENTRIES) {
      const href = entryHash(item, 'review', null);
      tbody.append(h('tr', null, entryCell(item, href),
        strategies.map((s) => {
          const has = item.strategies.indexOf(s) >= 0;
          const v = has ? rowFor(item, s)[m.key] : null;
          cols[s].push(rowFor(item, s));
          const text = fmt(v, m.fmt);
          return h('td', { class: ctl(s, 'n') }, has ? h('a', { href: entryHash(item, 'review', s), title: 'Open the “' + stratName(s) + '” draft of ' + itemName(item) }, text) : h('span', { class: 'muted', title: 'No “' + stratName(s) + '” draft for this entry' }, '–'));
        })));
    }
    tbody.append(h('tr', { class: 'mean' }, h('td', null, m.key === 'gold_fact_contradicted' ? 'Total' : 'Mean of entries with a value'),
      strategies.map((s) => h('td', { class: ctl(s, 'n') }, fmt(meanRow(cols[s])[m.key], m.fmt)))));
    return h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
      h('caption', { class: 'visually-hidden' }, m.label + ' for each entry, by strategy'),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Entry'), strategies.map((s) => h('th', { class: ctl(s, 'n'), scope: 'col' }, stratTitle(s))))),
      tbody));
  }
  function footer() {
    const u = DATA.usage_total || {};
    const bits = [];
    if (isNum(u.calls)) bits.push(plural(u.calls, 'model call'));
    if (isNum(u.input_tokens) || isNum(u.output_tokens)) bits.push(((u.input_tokens || 0) + (u.output_tokens || 0)).toLocaleString('en-US') + ' tokens');
    if (isNum(u.list_price_usd)) bits.push('about $' + u.list_price_usd.toFixed(2) + ' at list price');
    return h('footer', { class: 'foot' },
      bits.length ? h('div', null, 'Last pass of the run: ' + bits.join(', ') + ' (calls answered from cache cost nothing).') : null,
      h('div', null, 'Generated by aiomim. Your decisions are kept in this browser only' + (storageOk ? '' : ' (and this browser is not saving them)') + '; use the export buttons on each entry to keep them.'));
  }

  // ------------------------------------------------------------------ strategies.json (aiomim compare, any number of strategies)
  const cmpKind = (metric) => (/f1/.test(metric) ? 'f1' : 'pct');
  function fmtCmp(v, kind) {
    if (!isNum(v)) return '–';
    return kind === 'f1' ? v.toFixed(2) : (100 * v).toFixed(1) + '%';
  }
  // Differences: percentage points for percentages, F1 units (three decimals: they are small) for F1.
  // The sign is taken from the rounded number, so nothing prints as "−0.0".
  function fmtDiff(v, kind) {
    if (!isNum(v)) return '–';
    const body = kind === 'f1' ? Math.abs(v).toFixed(3) : (100 * Math.abs(v)).toFixed(1);
    const zero = Number(body) === 0;
    return (zero ? '' : v > 0 ? '+' : '−') + body + (kind === 'f1' ? '' : ' pp');
  }
  function fmtCI(ci, kind) {
    if (!Array.isArray(ci) || ci.length !== 2) return null;
    return fmtDiff(ci[0], kind) + ' to ' + fmtDiff(ci[1], kind);
  }
  // True when the interval, as printed, lies wholly on one side of zero.
  function ciExcludesZero(ci, kind) {
    if (!Array.isArray(ci) || ci.length !== 2) return false;
    const a = fmtDiff(ci[0], kind).charAt(0); const b = fmtDiff(ci[1], kind).charAt(0);
    return (a === '+' && b === '+') || (a === '−' && b === '−');
  }
  function dirMark(higher) {
    return h('span', { class: 'dir', title: higher ? 'Higher is better' : 'Lower is better' }, higher ? ' ↑' : ' ↓');
  }
  function metricLabel(r) {
    const sub = /^…/.test(r.label || '');
    const dir = r.higher_is_better === true || r.higher_is_better === false ? dirMark(r.higher_is_better) : null;
    return h('th', { scope: 'row', class: sub ? 'sub' : null }, (r.label || humanize(r.metric)), dir);
  }
  const usd = (v) => (isNum(v) ? '$' + v.toFixed(2) : '–');
  const count = (v) => (isNum(v) ? v.toLocaleString('en-US') : '–');

  function comparedSection(c, panel) {
    const names = ((c.strategies || []).map((x) => x.name)).filter((x, i, a) => x && a.indexOf(x) === i);
    const base = c.baseline && names.indexOf(c.baseline) >= 0 ? c.baseline : null;
    const others = names.filter((x) => x !== base);
    const n = c.n_entries || 0;
    const active = CMP_PANELS.some((p) => p.id === panel) ? panel : 'scores';
    const sec = h('section', { class: 'section', 'aria-labelledby': 'cmp-h' });
    sec.append(h('div', { class: 'section-head' }, h('h2', { id: 'cmp-h' }, 'The strategies compared'),
      h('button', { type: 'button', class: 'btn', 'data-fid': 'to-entries', onclick: () => { const el = document.getElementById('entries'); if (el) el.scrollIntoView(); } }, 'Skip to the entry list ↓')));
    sec.append(h('p', { class: 'lede small' },
      plural(n, 'entry', 'entries') + (n === 1 ? ' was' : ' were') + ' written by every one of the ' + names.length + ' strategies below from the same papers, then put through the same audit and the same scoring. ' +
      'The comparison uses only those ' + n + (ENTRIES.length > n ? ' of the run’s ' + ENTRIES.length : '') + ' entries, so every column rests on the same entries. ' +
      '↑ marks scores where higher is better, ↓ where lower is better.'));
    sec.append(strategyList(c));
    const controls = names.filter(isControl);
    if (controls.length) {
      sec.append(h('p', { class: 'small control-note' }, controlTag(), ' ', listWords(controls.map(stratName)) + (controls.length === 1 ? ' is a control, not a way of writing entries.' : ' are controls, not ways of writing entries.') +
        ' Its columns are shaded: read them as a reference point for the other strategies.'));
    }
    sec.append(h('nav', { class: 'tabs', 'aria-label': 'Comparison tables' }, CMP_PANELS.map((p) => h('a', {
      href: '#overview' + (p.id === 'scores' ? '' : '--' + p.id), 'aria-current': p.id === active ? 'page' : null, 'data-fid': 'cmp-' + p.id,
    }, p.label))));

    const head = (first, list, withBaseline) => h('thead', null, h('tr', null, h('th', { scope: 'col' }, first),
      (list || names).map((s) => h('th', { class: ctl(s, 'n'), scope: 'col' }, stratTitle(s, withBaseline)))));
    // rows of {label, higher_is_better, values:{strategy: v}, n:{strategy: n}}
    const meansTable = (rows, caption, format, first) => h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
      h('caption', { class: 'visually-hidden' }, caption), head(first || 'Score', names, true),
      h('tbody', null, (rows || []).map((r) => h('tr', null, metricLabel(r), names.map((s) => {
        const v = (r.values || {})[s];
        const k = (r.n || {})[s];
        return h('td', { class: ctl(s, 'n'), title: isNum(k) ? 'Mean over ' + plural(k, 'entry', 'entries') : null }, format(v, r),
          isNum(k) && isNum(v) && k !== n ? h('div', { class: 'cmp-pair' }, 'n = ' + k) : null);
      }))))));
    const pctOrF1 = (v, r) => fmtCmp(v, cmpKind(r.metric));

    if (active === 'scores') {
      sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'Scores'),
        h('p', { class: 'small muted' }, 'Mean over the ' + n + ' entries. “n =” appears where a score exists for fewer entries (for example, OMIM lists no variants for some).'),
        meansTable(c.means, 'Mean scores by strategy', pctOrF1)));
      if ((c.volume || []).length) {
        sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'How much each strategy writes'),
          h('p', { class: 'small muted' }, 'Mean per entry. More text gives more chances both to convey a fact and to get one wrong, so read the scores above with these in mind.'),
          meansTable(c.volume, 'Amount written per entry, by strategy', (v) => (isNum(v) ? v.toFixed(1) : '–'), 'Per entry')));
      }
    }

    if (active === 'baseline') {
      const vs = c.versus_baseline || {};
      const metrics = [];
      for (const s of others) for (const r of vs[s] || []) if (!metrics.some((m) => m.metric === r.metric)) metrics.push(r);
      const block = h('div', { class: 'cmp-block' }, h('h3', null, 'Differences from the baseline' + (base ? ' (' + stratName(base) + ')' : '')));
      if (!base || !metrics.length) block.append(h('div', { class: 'empty' }, 'This comparison has no baseline to measure the other strategies against.'));
      else {
        block.append(h('p', { class: 'small muted' }, 'Each strategy is compared with the baseline entry by entry. The first line of a cell is the mean difference, strategy minus baseline, in percentage points (pp) for percentages and in F1 units for F1 scores. ' +
          'The second line is the 95% interval: the range the true average difference plausibly lies in. When it spans zero, these ' + n + ' entries show no clear difference; ● marks intervals that do not include zero. ' +
          'The third line counts the entries on which the strategy scored better, worse or the same as the baseline. Whether a positive difference is good depends on the arrow beside the score.'));
        block.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
          h('caption', { class: 'visually-hidden' }, 'Paired differences from the baseline'),
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Score'),
            h('th', { class: ctl(base, 'n'), scope: 'col' }, stratTitle(base, true), h('div', { class: 'cmp-n' }, 'mean')),
            others.map((s) => h('th', { class: ctl(s, 'n'), scope: 'col' }, stratTitle(s), h('div', { class: 'cmp-n' }, 'difference'))))),
          h('tbody', null, metrics.map((m) => {
            const k = cmpKind(m.metric);
            const any = others.map((s) => (vs[s] || []).find((x) => x.metric === m.metric)).find(Boolean);
            return h('tr', null, metricLabel(m), h('td', { class: ctl(base, 'n') }, fmtCmp(any ? any.baseline : null, k)),
              others.map((s) => {
                const r = (vs[s] || []).find((x) => x.metric === m.metric);
                if (!r) return h('td', { class: ctl(s, 'n muted') }, '–');
                const clear = ciExcludesZero(r.ci95, k);
                return h('td', { class: ctl(s, 'n'), title: 'Over ' + plural(r.n || 0, 'entry', 'entries') + (isNum(r.sign_test_p) ? '; sign test p = ' + r.sign_test_p.toFixed(3) : '') },
                  h('div', { class: 'strong' }, clear ? h('span', { class: 'ci-clear', title: 'The 95% interval does not include zero' }, '● ') : null, fmtDiff(r.difference, k)),
                  h('div', { class: 'cmp-pair' }, fmtCI(r.ci95, k) || 'no interval'),
                  h('div', { class: 'cmp-pair' }, (r.better || 0) + ' better · ' + (r.worse || 0) + ' worse · ' + (r.ties || 0) + ' same'));
              }));
          })))));
      }
      sec.append(block);
    }

    if (active === 'breakdowns') {
      const lv = c.by_content_level || {};
      const lk = ['fulltext', 'abstract', 'title', 'not_retrieved'].filter((k) => lv[k]).concat(Object.keys(lv).filter((k) => !LEVEL[k]));
      if (lk.length) {
        sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'OMIM facts conveyed, by how much of the paper was readable'),
          h('p', { class: 'small muted' }, 'OMIM’s per-paper facts pooled over the ' + n + ' entries and grouped by how much of the paper they summarise could be read. Each cell: share of facts conveyed (partial counts ½), then the number of facts judged.'),
          h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
            h('caption', { class: 'visually-hidden' }, 'OMIM-fact coverage by readable level of the paper'), head('Paper readable as'),
            h('tbody', null, lk.map((k) => h('tr', null, h('th', { scope: 'row' }, (LEVEL[k] || { label: humanize(k) }).label),
              names.map((s) => {
                const cell = lv[k][s];
                if (!cell) return h('td', { class: ctl(s, 'n muted') }, '–');
                return h('td', { class: ctl(s, 'n'), title: (cell.present || 0) + ' present, ' + (cell.partial || 0) + ' partial, ' + (cell.contradicted || 0) + ' contradicted' },
                  h('div', null, fmtCmp(cell.coverage, 'pct')), h('div', { class: 'cmp-pair' }, count(cell.n_facts) + ' facts'));
              }))))))));
      }
      const grouped = (title, about, groups) => {
        const keys = Object.keys(groups || {});
        if (!keys.length) return null;
        const body = h('tbody');
        for (const g of keys) {
          body.append(h('tr', { class: 'group' }, h('th', { scope: 'rowgroup', colspan: String(names.length + 1) }, humanize(g), h('span', { class: 'cmp-n' }, ' · ' + plural(groups[g].n || 0, 'entry', 'entries')))));
          for (const r of groups[g].means || []) {
            body.append(h('tr', null, metricLabel(r), names.map((s) => {
              const v = (r.values || {})[s]; const k = (r.n || {})[s];
              return h('td', { class: ctl(s, 'n'), title: isNum(k) ? 'Mean over ' + plural(k, 'entry', 'entries') : null }, pctOrF1(v, r),
                isNum(k) && isNum(v) && k !== groups[g].n ? h('div', { class: 'cmp-pair' }, 'n = ' + k) : null);
            })));
          }
        }
        return h('details', { class: 'legend cmp-details', open: state.open.has(title) || null, ontoggle: (e) => { if (e.target.open) state.open.add(title); else state.open.delete(title); } },
          h('summary', null, title, h('span', { class: 'muted small' }, ' · ' + keys.length + ' groups')),
          h('div', { class: 'cmp-details-body' }, h('p', { class: 'small muted' }, about),
            h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' }, h('caption', { class: 'visually-hidden' }, title), head('Score'), body))));
      };
      const small = ' Groups with few entries give unsteady averages; the group sizes are shown.';
      add(sec, grouped('By share of the entry’s references readable as full text', 'Entries grouped by how many of OMIM’s references for them could be read in full rather than as abstract or title only.' + small, c.by_access));
      add(sec, grouped('By size of the reference list', 'Entries grouped by how many papers OMIM cites for them.' + small, c.by_reference_count));
      add(sec, grouped('By when the OMIM entry was created', 'OMIM numbers were assigned in ranges over time, so the number range stands for the era in which the entry was written.' + small, c.by_stratum));
      if (!lk.length && !Object.keys(c.by_access || {}).length) sec.append(h('div', { class: 'empty' }, 'No breakdowns were computed for this comparison.'));
    }

    if (active === 'totals') {
      const pooled = c.pooled || {};
      const line = (label, path, kind, sub) => h('tr', null, h('th', { scope: 'row', class: sub ? 'sub' : null }, label),
        names.map((s) => { const v = get(pooled[s], path); return h('td', { class: ctl(s, 'n') }, kind === 'pct' ? fmtCmp(v, 'pct') : count(v)); }));
      sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'Pooled counts'),
        h('p', { class: 'small muted' }, 'Totals over the ' + n + ' entries, so entries with many claims or facts weigh more here than in the averages.'),
        h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' }, h('caption', { class: 'visually-hidden' }, 'Pooled claim and fact counts'), head(''),
          h('tbody', null,
            line('Claims audited', 'claims.n'), line('supported', 'claims.supported', null, true), line('partly supported', 'claims.partially_supported', null, true),
            line('not supported', 'claims.unsupported', null, true), line('contradicted', 'claims.contradicted', null, true),
            line('Share supported', 'claims.supported_rate', 'pct'), line('Share not supported or contradicted', 'claims.error_rate', 'pct'),
            line('OMIM facts judged', 'gold_facts.n_facts'), line('present', 'gold_facts.present', null, true), line('partial', 'gold_facts.partial', null, true),
            line('absent', 'gold_facts.absent', null, true), line('contradicted', 'gold_facts.contradicted', null, true),
            line('Share conveyed (partial counts ½)', 'gold_facts.coverage', 'pct'), line('Share contradicted', 'gold_facts.contradiction_rate', 'pct'))))));
      const edges = c.knowledge_graph_edges || {};
      const en = names.filter((s) => edges[s]);
      if (en.length) {
        const rel = [['caused_by', 'Disease → causal gene'], ['inheritance', 'Disease → mode of inheritance'], ['has_phenotype', 'Disease → phenotype (exact HPO term)'], ['has_variant', 'Disease → allelic variant']];
        const body = h('tbody');
        for (const [key, label] of rel) {
          if (!en.some((s) => edges[s][key])) continue;
          body.append(h('tr', { class: 'group' }, h('th', { scope: 'rowgroup', colspan: String(en.length + 1) }, label)));
          const row = (text, pick, sub) => body.append(h('tr', null, h('th', { scope: 'row', class: sub ? 'sub' : null }, text), en.map((s) => h('td', { class: ctl(s, 'n') }, pick(edges[s][key] || {})))));
          row('Precision', (e) => fmtCmp(e.precision, 'pct'));
          row('Recall', (e) => fmtCmp(e.recall, 'pct'));
          row('F1', (e) => fmtCmp(e.f1, 'pct'));
          row('in both / generated / in OMIM', (e) => count(e.in_both) + ' / ' + count(e.generated) + ' / ' + count(e.omim), true);
        }
        sec.append(h('div', { class: 'cmp-block' }, h('h3', null, 'Links to genes, inheritance, phenotypes and variants, against OMIM'),
          h('p', { class: 'small muted' }, 'Every entry a strategy drafted in this run is reduced to its links and pooled (so these columns may rest on more entries than the tables above). Precision is the share of generated links OMIM also has; recall is the share of OMIM’s links that were generated. A generated link absent from OMIM is not necessarily wrong: it is one OMIM does not record.'),
          h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' }, h('caption', { class: 'visually-hidden' }, 'Knowledge links against OMIM'), head('', en), body))));
      }
    }

    if (active === 'cost') {
      const cost = c.cost || {};
      const cn = names.filter((s) => cost[s]);
      const block = h('div', { class: 'cmp-block' }, h('h3', null, 'What each strategy costs to run, per entry'));
      if (!cn.length) block.append(h('div', { class: 'empty' }, 'No usage was recorded for this comparison.'));
      else {
        const pe = (s, phase, key) => get(cost[s], phase + '.per_entry.' + key);
        const row = (label, pick, sub) => h('tr', null, h('th', { scope: 'row', class: sub ? 'sub' : null }, label), cn.map((s) => h('td', { class: ctl(s, 'n') }, pick(s))));
        block.append(h('p', { class: 'small muted' }, 'Mean per entry when run from scratch. List price is the API price of the tokens used: a measure of consumption, not necessarily what the run was billed. ' +
          'Writing is the strategy itself. The audit and the scoring are the same procedure for every strategy and cost more or less with the amount of text produced.'));
        block.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' }, h('caption', { class: 'visually-hidden' }, 'Cost per entry by phase'), head('Per entry', cn),
          h('tbody', null,
            h('tr', { class: 'group' }, h('th', { scope: 'rowgroup', colspan: String(cn.length + 1) }, 'Writing the draft')),
            row('List price', (s) => usd(pe(s, 'generate', 'list_price_usd'))),
            row('Model calls', (s) => (isNum(pe(s, 'generate', 'calls')) ? pe(s, 'generate', 'calls').toFixed(1) : '–'), true),
            row('Tokens in / out', (s) => count(pe(s, 'generate', 'input_tokens')) + ' / ' + count(pe(s, 'generate', 'output_tokens')), true),
            row('Model time', (s) => (isNum(pe(s, 'generate', 'seconds')) ? Math.round(pe(s, 'generate', 'seconds')) + ' s' : '–'), true),
            h('tr', { class: 'group' }, h('th', { scope: 'rowgroup', colspan: String(cn.length + 1) }, 'Checking it')),
            row('Audit and repair: list price', (s) => usd(pe(s, 'audit', 'list_price_usd'))),
            row('Scoring against OMIM: list price', (s) => usd(pe(s, 'score', 'list_price_usd'))),
            h('tr', { class: 'group' }, h('th', { scope: 'rowgroup', colspan: String(cn.length + 1) }, 'Everything')),
            row('List price', (s) => h('strong', null, usd(pe(s, 'total', 'list_price_usd')))),
            row('Model time', (s) => (isNum(pe(s, 'total', 'seconds')) ? Math.round(pe(s, 'total', 'seconds')) + ' s' : '–'), true),
            row('Entries with usage recorded', (s) => count(cost[s].entries), true)))));
      }
      sec.append(block);
    }
    return sec;
  }

  // ------------------------------------------------------------------ comparison.json (older file: evidence graph against direct reading only)
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
            h('th', { class: 'n', scope: 'col' }, 'Conveyed: ' + stratName('kg')), h('th', { class: 'n', scope: 'col' }, 'Conveyed: ' + stratName('direct')),
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
        DATA.split ? h('p', { style: 'margin-top:8px' }, 'The page keeps each entry in a separate file in the “' + DATA_DIR + '” folder. Keep that folder next to this page (copy or move them together), then try again.') : null,
        h('div', { class: 'btn-row', style: 'margin-top:10px' },
          h('button', { type: 'button', class: 'btn primary', 'data-fid': 'retry', onclick: () => { item.loadError = null; render({ keepScroll: true }); } }, 'Try again'),
          h('a', { class: 'btn', href: '#overview' }, 'Back to the overview'))));
      return wrap;
    }
    wrap.append(h('div', { class: 'loading', role: 'status', 'aria-live': 'polite' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the entry…'));
    loadEntry(item);
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

    if (s && isControl(s)) {
      wrap.append(h('div', { class: 'notice control', role: 'note', style: 'margin-top:8px' }, h('span', { class: 'notice-icon', 'aria-hidden': 'true' }, '◇'),
        h('div', null, h('strong', null, 'This draft is a control, not a candidate entry. '), stratAbout(s) || 'It is here to compare the other drafts against.',
          ' Use it to see what the other drafts add; do not accept text from it.')));
    }
    const controls = h('div', { class: 'entry-controls' });
    if (item.strategies.length > 1) {
      controls.append(strategySwitch(item.strategies, s, (x) => { state.selected = null; location.hash = entryHash(item, route.tab === 'updates' ? 'review' : route.tab, x); }, 'strat-'));
    } else if (s) controls.append(h('span', { class: 'small muted' }, stratTitle(s)));
    if (s && (item.pids[s] || []).length) controls.append(progressEl(item, s));
    wrap.append(controls);
    if (s && stratAbout(s) && item.strategies.length > 1 && !isControl(s)) wrap.append(h('p', { class: 'small muted strat-about' }, h('strong', null, stratName(s) + ': '), stratAbout(s)));
    const missing = STRATS.filter((x) => item.strategies.indexOf(x) < 0);
    if (item.strategies.length > 1 && route.tab !== 'gold') {
      wrap.append(h('details', { class: 'legend entry-scores', open: state.open.has('entry-scores') || null,
        ontoggle: (e) => { if (e.target.open) state.open.add('entry-scores'); else state.open.delete('entry-scores'); } },
      h('summary', { 'data-fid': 'entry-scores' }, 'Scores of this entry’s ' + item.strategies.length + ' drafts, side by side'),
      h('div', { class: 'cmp-details-body' }, entryScores(item, s, route.tab))));
    } else if (missing.length && STRATS.length > 1 && item.strategies.length === 1) {
      wrap.append(h('p', { class: 'small muted' }, 'This entry has one draft. Not drafted for it: ' + listWords(missing.map(stratName)) + '.'));
    }

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
    else if (tab === 'evidence') wrap.append(evidenceTab(item, s, entry));
    else if (tab === 'updates') wrap.append(h('div', { class: 'section' }, updatesBlock(item)));
    return wrap;
  }
  // One row per draft of this entry, so the strategies can be read against each other.
  function entryScores(item, current, tab) {
    const list = item.strategies;
    const missing = STRATS.filter((x) => list.indexOf(x) < 0);
    const tbody = h('tbody', null, list.map((x) => {
      const row = rowFor(item, x);
      return h('tr', { class: (x === current ? 'current' : '') + (isControl(x) ? ' ctl-row' : '') },
        h('th', { scope: 'row' }, x === current ? h('span', { class: 'strat-current' }, stratTitle(x, true)) : h('a', { href: entryHash(item, tab === 'updates' ? 'review' : tab, x), title: 'Show this draft' }, stratTitle(x, true)),
          x === current ? h('div', { class: 'cmp-n' }, 'shown now') : null),
        h('td', null, (item.pids[x] || []).length ? progressEl(item, x) : '–'),
        h('td', { class: 'n' }, fmt(row.claims, 'int')),
        METRICS.map((m) => h('td', { class: 'n' }, fmt(row[m.key], m.fmt))));
    }));
    return [h('div', { class: 'table-scroll' }, h('table', { class: 'data cmp' },
      h('caption', { class: 'visually-hidden' }, 'Scores of each draft of this entry'),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Draft'), h('th', { scope: 'col' }, 'Your review'),
        h('th', { class: 'n', scope: 'col' }, h('abbr', { title: 'Number of individual claims the audit checked in this draft' }, 'Claims')), METRICS.map(headerCell))),
      tbody)),
    missing.length ? h('p', { class: 'small muted', style: 'margin-top:8px' }, 'Not drafted for this entry: ' + listWords(missing.map(stratName)) + '.') : null];
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
          isNum(it.n_present) && isNum(it.n_assessed) ? h('span', { class: 'muted', title: 'Patients reported with the feature, out of those in whom the papers say it was assessed (pooled from the case table)' }, it.n_present + ' of ' + it.n_assessed + ' patients') : null,
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

    // findings (evidence-graph drafts) or case records and notes (case-table drafts)
    const fids = p.finding_ids || [];
    const isCase = fids.some((f) => /^[RN]:/.test(f));
    if (fids.length) {
      body.append(h('div', null, h('h4', null, (isCase ? 'Case records and notes it was written from' : 'Extracted facts it was written from') + ' (' + fids.length + ')'),
        h('ul', { class: 'findings' }, fids.map((fid) => {
          const f = item.findingBy.get(fid);
          if (f) return findingItem(item, f);
          const r = item.recordBy.get(fid);
          if (r) return recordItem(item, r);
          return h('li', { class: 'muted' }, (isCase ? 'Record ' + fid + ' is not included in this page (the case table was shortened to fit).' : 'Fact ' + fid + ' is not in this run’s extraction file.'));
        }))));
    } else {
      const linked = paragraphsOf(item.entries[s]).some((y) => (y.p.finding_ids || []).length);
      body.append(h('div', null, h('h4', null, 'Extracted facts'), h('p', { class: 'muted' }, linked
        ? 'This paragraph is not linked to extracted facts.'
        : 'Drafts written this way do not record which extracted facts a paragraph rests on. Rely on the audit and the cited papers.')));
    }

    // papers
    const pmids = p.pmids || [];
    body.append(h('div', null, h('h4', null, 'Cited papers'),
      pmids.length ? h('ul', { class: 'papers-list' }, pmids.map((pmid) => {
        const pp = item.paperBy.get(String(pmid)) || {};
        return h('li', null, h('div', null, ext(pubmedUrl(pmid), paperLabel(item, pmid)), ' ', levelChip(paperLevel(item, pmid))),
          pp.title ? h('div', { class: 'small muted' }, pp.title) : null);
      })) : h('p', { class: 'muted' }, 'This paragraph cites no paper.')));
    const extra = (p.audit_pmids || []).filter((x) => pmids.indexOf(x) < 0);
    if (extra.length) {
      body.append(h('div', null, h('h4', null, 'Also checked against'),
        h('p', { class: 'small muted' }, 'The paragraph does not cite these papers. The audit checked it against them because it was written without a usable citation.'),
        h('p', { class: 'small' }, citeLinks(item, extra))));
    }
    panel.append(body);
    return panel;
  }
  function quoteRows(quotes, grounding) {
    return (quotes || []).map((q, qi) => {
      const g = (grounding || [])[qi];
      const found = isNum(g) && g >= 0.85;
      return h('div', { class: 'quote-row' }, h('blockquote', { class: 'quote' }, q),
        h('span', { class: 'small ' + (found ? '' : 'muted') }, isNum(g) ? (found ? '✓ Found in the paper' : '✗ Not found word for word in the paper') + ' (match ' + g.toFixed(2) + ')' : 'Not checked against the paper'));
    });
  }
  function findingItem(item, f) {
    return h('li', null,
      h('div', { class: 'chips' }, plainChip(SECTION_HEADINGS[f.section] || humanize(f.section)), h('span', { class: 'small' }, ext(pubmedUrl(f.pmid), paperLabel(item, f.pmid))), h('span', { class: 'para-id' }, f.id)),
      h('div', null, f.statement || ''),
      quoteRows(f.quotes, f.quote_grounding));
  }
  const RECORD_KIND = { individual: 'One patient', family: 'Family', group: 'Patient group' };
  function recordSummary(r) {
    const bits = [];
    if (r.kind !== 'individual' && isNum(r.n_affected)) bits.push(plural(r.n_affected, 'affected person', 'affected people') + (isNum(r.n_families) && r.n_families ? ' in ' + plural(r.n_families, 'family', 'families') : ''));
    if (r.sex) bits.push(r.sex);
    if (r.ancestry) bits.push(r.ancestry);
    if (r.onset) bits.push('onset ' + r.onset);
    if (r.consanguinity && r.consanguinity !== 'not_stated') bits.push('consanguinity: ' + humanize(r.consanguinity).toLowerCase());
    return bits.join(' · ');
  }
  // A case-table record (one patient, family or group) or note, as evidence for a paragraph.
  function recordItem(item, r) {
    if (r.statement !== undefined) {
      return h('li', null,
        h('div', { class: 'chips' }, plainChip('Note'), r.section ? plainChip(SECTION_HEADINGS[r.section] || humanize(r.section)) : null, h('span', { class: 'small' }, ext(pubmedUrl(r.pmid), paperLabel(item, r.pmid))), h('span', { class: 'para-id' }, r.id)),
        h('div', null, r.statement || ''), quoteRows(r.quotes, r.quote_grounding));
    }
    const vars = (r.variants || []).map((v) => (v.gene ? v.gene + ' ' : '') + (v.as_reported || v.key || '') + (v.zygosity && v.zygosity !== 'unknown' ? ' (' + humanize(v.zygosity).toLowerCase() + ')' : ''));
    return h('li', null,
      h('div', { class: 'chips' }, plainChip(RECORD_KIND[r.kind] || humanize(r.kind || 'record')), r.followup_of ? plainChip('Follow-up of an earlier report') : null,
        h('span', { class: 'small' }, ext(pubmedUrl(r.pmid), paperLabel(item, r.pmid))), h('span', { class: 'para-id' }, r.id)),
      h('div', null, h('strong', null, r.label || 'Unnamed record'), recordSummary(r) ? h('span', { class: 'muted' }, ' · ' + recordSummary(r)) : null),
      vars.length ? h('div', { class: 'small mono' }, vars.join('; ')) : null,
      quoteRows(r.quotes, r.quote_grounding),
      isNum(r.n_quotes) && r.n_quotes > (r.quotes || []).length ? h('div', { class: 'small muted' }, (r.n_quotes - r.quotes.length) + ' more quote(s) not included in this page.') : null);
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
    out.push('---\n*Machine-drafted from the cited literature (strategy: ' + stratLabel(s) + '), run “' + RUN + '”. Curator review: ' +
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
      if (item.strategies.length > 1) box.append(h('section', { class: 'section', style: 'margin-top:0' }, h('h2', null, 'This entry’s drafts, side by side'), entryScores(item, s, 'gold')));
      box.append(h('div', { class: 'empty' }, h('strong', null, 'No comparison with OMIM for this draft. '),
        item.gold ? 'The OMIM gold standard was collected, but this draft was not scored against it.' : 'This is a new entry with no OMIM entry to compare against, or scoring was skipped for this run. The audit of each paragraph against its cited paper is still available under Review draft.'));
      return box;
    }
    const row = rowFor(item, s);
    if (item.strategies.length > 1) {
      box.append(h('section', { class: 'section', style: 'margin-top:0' }, h('h2', null, 'This entry’s drafts, side by side'), entryScores(item, s, 'gold')));
    }
    box.append(h('h2', { style: 'margin-top:8px' }, stratTitle(s), ' against OMIM'));
    box.append(h('p', { class: 'source-note' }, 'This view compares ' + draftName(s) + ' with the real OMIM entry' + (item.mim ? ' ' + item.mim : '') +
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
  // What the selected draft rests on. The papers are common to every strategy; how they were
  // used differs, so each strategy's own working record is shown only when its files have it.
  const VERDICT_KEYS = ['supported', 'partially_supported', 'contradicted', 'unsupported', 'not_checkable'];
  function kvList() {
    const dl = h('dl', { class: 'kv' });
    dl.row = (k, v) => { if (v !== null && v !== undefined && v !== '') dl.append(h('dt', null, k), h('dd', null, v)); return dl; };
    return dl;
  }
  const yesNo = (v) => (v ? h('span', { class: 'yes' }, '✓ Yes') : h('span', { class: 'muted' }, 'No'));
  const countMap = (m, label) => Object.keys(m || {}).filter((k) => m[k]).map((k) => (label ? label(k) : humanize(k)) + ': ' + m[k]).join(', ');
  const share = (a, b) => (isNum(a) && isNum(b) && b ? a + ' of ' + b + ' (' + fmt(a / b, 'pct') + ')' : isNum(a) ? String(a) : '–');

  function evidenceTab(item, s, entry) {
    const box = h('div', { class: 'section' });
    const meta = (entry && entry.meta) || {};
    const r = item.retrieval;

    // 1. how this draft was made
    const how = h('section', { class: 'section', style: 'margin-top:0', 'aria-labelledby': 'how-h' },
      h('h2', { id: 'how-h' }, s ? ['How ', draftName(s), ' was made'] : 'Evidence'));
    if (s && stratAbout(s)) how.append(h('p', { class: 'lede small' }, stratAbout(s)));
    if (s && !entry) how.append(h('div', { class: 'empty' }, 'No draft was written this way for this entry.'));
    const used = get(item, 'usage.by_strategy.' + s);
    if (meta.agent || meta.quote_check) add(how, agentBlock(item, meta, used));
    if (meta.cohort || (s === 'cohort' && item.cohort)) add(how, cohortBlock(item, meta.cohort || {}));
    if (meta.recall) add(how, recallBlock(item, meta.recall));
    if (meta.closedbook) add(how, memoryBlock(item, meta.closedbook, 'What the model recalled without the papers'));
    const x = meta.extraction;
    const kg = item.kg;
    const st = (s === 'kg' && kg && kg.stats) || meta.kg || null;
    if (x || st) {
      const kv = kvList();
      if (x) {
        kv.row('Facts kept', fmt(x.findings_kept, 'int'));
        kv.row('Facts dropped (quote not found in paper)', fmt(x.findings_dropped_ungrounded, 'int'));
        kv.row('Quote grounding rate', fmt(x.quote_grounding_rate, 'pct'));
        if (x.papers_by_relevance) kv.row('Papers by relevance', countMap(x.papers_by_relevance, (k) => RELEVANCE[k] || k));
        if ((x.papers_failed || []).length) kv.row('Papers that failed extraction', x.papers_failed.join(', '));
        if (x.hpo_resolution && typeof x.hpo_resolution === 'object') kv.row('HPO term resolution', countMap(x.hpo_resolution));
      }
      if (st && st.nodes) kv.row('Graph nodes', Object.keys(st.nodes).map((k) => k + ' ' + st.nodes[k]).join(', '));
      if (st && st.edges) kv.row('Graph links', Object.keys(st.edges).map((k) => humanize(k).toLowerCase() + ' ' + st.edges[k]).join(', '));
      how.append(h('div', { class: 'cmp-block' }, h('h3', null, 'Fact extraction'), kv));
    }
    add(how, auditBlock(meta, used, item));
    box.append(how);

    // 2. papers
    if (r) {
      box.append(h('p', { class: 'source-note' }, r.mode === 'oracle' ? 'Papers: the references the OMIM entry already cites.' : r.mode === 'open' ? 'Papers: chosen by a literature search' + ((r.queries || []).length ? ' (' + plural(r.queries.length, 'query', 'queries') + ')' : '') + '.' : '',
        (r.missing || []).length ? ' ' + plural(r.missing.length, 'paper') + ' could not be retrieved: ' + r.missing.join(', ') + '.' : ''));
    }
    const papers = item.papers || [];
    const sec = h('section', { class: 'section', 'aria-labelledby': 'pp-h' }, h('h2', { id: 'pp-h' }, 'Papers supplied (' + papers.length + ')'));
    if (!papers.length) sec.append(h('div', { class: 'empty' }, 'No paper list was saved for this entry.'));
    else {
      // strategy-specific columns: [header cell, cell for a paper]
      const cols = [];
      const abbr = (text, title) => h('abbr', { title: title }, text);
      if (s === 'kg' && item.extractionBy.size) {
        cols.push([abbr('Relevance', 'How central the paper is to this entry, as judged when its facts were extracted'), (p, ex) => h('td', { title: ex && ex.relevance_reason ? ex.relevance_reason : null }, ex ? RELEVANCE[ex.relevance] || humanize(ex.relevance) : '–')]);
        cols.push([abbr('Facts kept', 'Facts extracted with a supporting quote that was found in the paper'), (p, ex) => h('td', { class: 'n' }, ex ? String((ex.findings || []).length) : '–'), 'n']);
        cols.push([abbr('Dropped', 'Facts discarded because their supporting quote could not be found in the paper'), (p, ex) => h('td', { class: 'n' }, ex ? String(ex.n_dropped || 0) : '–'), 'n']);
      }
      if (meta.agent) {
        const read = new Set((meta.agent.papers_read || []).map(String));
        cols.push([abbr('Opened by the agent', 'Whether the agent says it opened this paper while working'), (p) => h('td', null, yesNo(read.has(String(p.pmid))))]);
      }
      const cp = new Map((get(item, 'cohort.papers') || []).map((p) => [String(p.pmid), p]));
      if (meta.cohort && cp.size) {
        cols.push([abbr('Relevance', 'Only records from primary and supporting papers are pooled into the case table'), (p) => { const c = cp.get(String(p.pmid)); return h('td', null, c ? RELEVANCE[c.relevance] || humanize(c.relevance || '') || '–' : '–'); }]);
        cols.push([abbr('Records', 'Patient, family or group records extracted from the paper'), (p) => { const c = cp.get(String(p.pmid)); return h('td', { class: 'n' }, c ? String(c.records || 0) + (c.dropped_records ? ' (+' + c.dropped_records + ' dropped)' : '') : '–'); }, 'n']);
        cols.push([abbr('Notes', 'Citable results that are not about particular patients'), (p) => { const c = cp.get(String(p.pmid)); return h('td', { class: 'n' }, c ? String(c.notes || 0) + (c.dropped_notes ? ' (+' + c.dropped_notes + ' dropped)' : '') : '–'); }, 'n']);
      }
      const mem = meta.closedbook || (meta.recall && meta.recall.memory);
      if (mem && Array.isArray(mem.supplied_papers_cited_pmids)) {
        const cited = new Set(mem.supplied_papers_cited_pmids.map(String));
        cols.push([abbr('Cited from memory', 'Whether the from-memory draft cited this paper before any paper was shown to the model'), (p) => h('td', null, yesNo(cited.has(String(p.pmid))))]);
      }
      const inDraft = new Set(entry ? citedByEntry(entry) : []);
      sec.append(h('div', { class: 'table-scroll' }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Paper'), h('th', { class: 'n', scope: 'col' }, 'Year'), h('th', { scope: 'col' }, 'Journal'),
          h('th', { scope: 'col' }, 'Readable'), entry ? h('th', { scope: 'col' }, abbr('Cited in this draft', 'Whether a paragraph of the draft shown now cites the paper')) : null,
          cols.map((c) => h('th', { scope: 'col', class: c[2] || null }, c[0])), h('th', { scope: 'col' }, 'PubMed'))),
        h('tbody', null, papers.map((p) => {
          const ex = item.extractionBy.get(String(p.pmid));
          return h('tr', null,
            h('td', { style: 'min-width:260px' }, h('strong', null, p.label || ('PMID ' + p.pmid)), p.title ? h('div', { class: 'small muted' }, p.title) : null, s === 'kg' && ex && ex.error ? h('div', { class: 'small', style: 'color:var(--bad)' }, 'Extraction failed: ' + ex.error) : null),
            h('td', { class: 'n' }, p.year || '–'), h('td', null, p.journal || '–'),
            h('td', null, levelChip(p.content_level)), entry ? h('td', null, yesNo(inDraft.has(String(p.pmid)))) : null,
            cols.map((c) => c[1](p, ex)),
            h('td', null, ext(pubmedUrl(p.pmid), p.pmid)));
        })))));
    }
    box.append(sec);

    // 3. the evidence graph belongs to the evidence-graph draft
    if (kg && (kg.entities || []).length) {
      if (s === 'kg' || item.strategies.indexOf('kg') < 0) box.append(graphSection(item));
      else box.append(h('p', { class: 'source-note' }, 'The evidence graph of this entry belongs to the “' + stratName('kg') + '” draft. ', h('a', { href: entryHash(item, 'evidence', 'kg') }, 'Show that draft’s evidence.')));
    } else if (s === 'kg') {
      box.append(h('section', { class: 'section' }, h('h2', null, 'What the evidence graph established'), h('div', { class: 'empty' }, 'No evidence graph was saved for this entry.')));
    }
    return box;
  }

  function graphSection(item) {
    const kg = item.kg;
    const ksec = h('section', { class: 'section', 'aria-labelledby': 'kg-h' }, h('h2', { id: 'kg-h' }, 'What the evidence graph established'),
      h('p', { class: 'small muted' }, 'Built from the extracted facts before the evidence-graph draft was written. Each row lists the papers that support linking it to this entry.'));
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
      ksec.append(h('div', { class: 'table-scroll' + (rows.length > 14 ? ' tall' : '') }, h('table', { class: 'data' },
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, g.rel === 'has_phenotype' ? 'Feature' : 'Name'), g.rel === 'has_phenotype' ? h('th', { scope: 'col' }, 'HPO') : null,
          h('th', { class: 'n', scope: 'col' }, 'Papers'), h('th', { scope: 'col' }, 'Supported by'), g.rel === 'has_phenotype' ? h('th', { scope: 'col' }, 'Reported absent in') : null)),
        h('tbody', null, rows.map((e) => h('tr', null,
          h('td', null, g.rel === 'inheritance' ? (e.label || e.id) : g.rel === 'has_variant' ? h('span', { class: 'mono' }, e.omim_name ? e.omim_name + ' · ' : '', e.label) : e.label || e.id),
          g.rel === 'has_phenotype' ? h('td', null, hpoLink(e.hpo_id) || '–') : null,
          h('td', { class: 'n' }, String((e.pmids || []).length)),
          h('td', { class: 'small' }, (e.pmids || []).length ? citeLinks(item, e.pmids) : '–'),
          g.rel === 'has_phenotype' ? h('td', { class: 'small' }, (e.absent_in || []).length ? citeLinks(item, e.absent_in) : '–') : null))))));
    }
    return ksec;
  }

  // Audit, repair and model use: the same procedure for every strategy.
  function auditBlock(meta, used, item) {
    const kv = kvList();
    const before = meta.audit_before_repair;
    if (before && isNum(before.n_claims)) kv.row('Claims audited before repair', before.n_claims + ' (' + fmt(before.supported_rate, 'pct') + ' supported, ' + fmt(before.error_rate, 'pct') + ' not supported or contradicted)');
    const rep = meta.repair;
    if (rep) kv.row('Repair round', (rep.flagged || 0) + ' paragraph(s) flagged, ' + (rep.revised || 0) + ' revised, ' + (rep.deleted || 0) + ' deleted');
    if (isNum(meta.dropped_ungrounded_count) && meta.dropped_ungrounded_count) kv.row('Paragraphs dropped before the audit (no usable source)', String(meta.dropped_ungrounded_count));
    if ((meta.unknown_citations || []).length) kv.row('Citations that match no supplied paper', meta.unknown_citations.join('; '));
    if (isNum(meta.truncated_papers_count) && meta.truncated_papers_count) kv.row('Papers cut short to fit the prompt', String(meta.truncated_papers_count));
    if (meta.hpo_resolution && typeof meta.hpo_resolution === 'object') kv.row('HPO term resolution', countMap(meta.hpo_resolution));
    const plc = meta.papers_by_content_level;
    if (plc) kv.row('Papers by readable level', countMap(plc, (k) => (LEVEL[k] ? LEVEL[k].label : k)));
    if (meta.model) kv.row('Model', meta.model);
    if (used) {
      const part = (label, b) => (b && (b.calls || b.usd) ? label + ' ' + plural(b.calls || 0, 'call') + (b.turns && b.turns !== b.calls ? ' (' + b.turns + ' turns)' : '') + ', ' + usd(b.usd) : null);
      const bits = [part('writing', used.generate), part('audit and repair', used.audit), part('scoring against OMIM', used.score)].filter(Boolean);
      if (bits.length) kv.row('Model use for this draft', bits.join('; ') + ' (list price)');
    } else {
      const u = item.usage && item.usage.total;
      if (u && (u.calls || u.list_price_usd)) kv.row('Model use for this entry (all drafts, last pass)', plural(u.calls || 0, 'call') + ', ' + ((u.input_tokens || 0) + (u.output_tokens || 0)).toLocaleString('en-US') + ' tokens' + (isNum(u.list_price_usd) ? ', about ' + usd(u.list_price_usd) : ''));
    }
    if (!kv.children.length) return null;
    return h('div', { class: 'cmp-block' }, h('h3', null, 'Audit, repair and model use'), kv);
  }

  function agentBlock(item, meta, used) {
    const a = meta.agent || {};
    const q = meta.quote_check || {};
    const kv = kvList();
    const read = a.papers_read || [];
    if (isNum(a.papers_supplied)) kv.row('Papers opened by the agent', share(read.length, a.papers_supplied));
    if ((a.papers_not_read || []).length) kv.row('Supplied but not opened', citeLinks(item, a.papers_not_read));
    if ((a.papers_read_unknown || []).length) kv.row('Named as read but not among the supplied papers', a.papers_read_unknown.join(', '));
    const turns = isNum(a.turns) ? a.turns : get(used, 'generate.turns');
    if (isNum(turns) && turns) kv.row('Agent turns while writing', String(turns));
    if (isNum(q.paragraphs_with_quotes)) kv.row('Paragraphs backed by quotes', String(q.paragraphs_with_quotes));
    if (isNum(q.quotes)) kv.row('Quotes found word for word in the papers', share(q.quotes_found, q.quotes));
    if (isNum(a.paragraphs_without_quotes)) kv.row('Paragraphs the agent gave no quote for', String(a.paragraphs_without_quotes));
    if (isNum(q.paragraphs_dropped)) kv.row('Paragraphs dropped by the quote check', String(q.paragraphs_dropped));
    return h('div', { class: 'cmp-block' }, h('h3', null, 'What the agent did'), kv,
      a.process_note ? h('div', { class: 'process-note' }, h('div', { class: 'side-label' }, 'The agent’s own note on how it worked (its account, not checked)'), h('p', null, a.process_note)) : null);
  }

  // Shared by the memory-only control and by recall-then-verify (whose first step is the same memory draft).
  function memoryBlock(item, m, title) {
    const kv = kvList();
    if (isNum(m.paragraphs)) kv.row('Paragraphs written from memory', String(m.paragraphs));
    if (isNum(m.paragraphs_citing_supplied_papers)) kv.row('… citing a paper that was among those supplied', String(m.paragraphs_citing_supplied_papers));
    if (isNum(m.paragraphs_checked_against_all_papers)) kv.row('… with no usable citation (audited against every paper)', String(m.paragraphs_checked_against_all_papers));
    if (isNum(m.supplied_papers)) kv.row('Supplied papers the model cited from memory', share(m.supplied_papers_cited, m.supplied_papers));
    if ((m.citations_matched || []).length) kv.row('Citations matched to supplied papers', m.citations_matched.join('; '));
    if ((m.citations_unmatched || []).length) kv.row('Citations that match no supplied paper', m.citations_unmatched.join('; '));
    if (isNum(m.pmids_offered) && m.pmids_offered) kv.row('PubMed IDs the model offered', m.pmids_offered + ' (' + (m.pmids_offered_matching_supplied || 0) + ' matching a supplied paper)');
    if (!kv.children.length) return null;
    return h('div', { class: 'cmp-block' }, h('h3', null, title), kv);
  }

  function recallBlock(item, rc) {
    const mem = item.recall_memory || null;
    const by = rc.memory_claims_by_verdict || (mem && mem.by_verdict) || {};
    const omitted = rc.claims_omitted_by_verdict || {};
    const total = isNum(rc.memory_claims) ? rc.memory_claims : (mem ? mem.claims : null);
    const action = { supported: 'Kept, attributed to the paper that supports it', partially_supported: 'Restated to say what the quoted evidence says',
      contradicted: 'Corrected to what the paper says', unsupported: 'Deleted', not_checkable: 'Deleted' };
    const kv = kvList();
    if (isNum(total)) kv.row('Claims in the from-memory draft', String(total));
    if (isNum(total) && isNum(by.supported)) kv.row('Supported by the papers as written', share(by.supported, total));
    if (isNum(rc.claims_survived_share)) kv.row('Claims carried into this draft (kept, restated or corrected)', fmt(rc.claims_survived_share, 'pct'));
    if (isNum(rc.paragraphs_before)) kv.row('Paragraphs', rc.paragraphs_before + ' from memory → ' + (isNum(rc.paragraphs_after) ? rc.paragraphs_after : '–') + ' after the check');
    if (isNum(rc.paragraphs_dropped_uncited) && rc.paragraphs_dropped_uncited) kv.row('Paragraphs dropped for having no supporting paper', String(rc.paragraphs_dropped_uncited));
    const block = h('div', { class: 'cmp-block' }, h('h3', null, 'How much of the memory draft survived the check'), kv,
      h('div', { class: 'table-scroll compare' }, h('table', { class: 'data' },
        h('caption', { class: 'visually-hidden' }, 'Memory claims by audit verdict'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'What the audit found'), h('th', { class: 'n', scope: 'col' }, 'Memory claims'), h('th', { scope: 'col' }, 'What the rewrite does with them'), h('th', { class: 'n', scope: 'col' }, 'Left out of this draft'))),
        h('tbody', null, VERDICT_KEYS.filter((k) => by[k] || omitted[k]).map((k) => h('tr', null, h('td', null, chip(VERDICT[k])), h('td', { class: 'n' }, String(by[k] || 0)), h('td', null, action[k]), h('td', { class: 'n' }, String(omitted[k] || 0))))))));
    if (mem && (mem.not_standing || []).length) {
      const more = (mem.n_not_standing || 0) - mem.not_standing.length;
      block.append(h('details', { class: 'more', open: state.open.has('memory-claims') || null, ontoggle: (e) => { if (e.target.open) state.open.add('memory-claims'); else state.open.delete('memory-claims'); } },
        h('summary', { 'data-fid': 'memory-claims' }, 'Memory claims the papers did not fully support (' + (mem.n_not_standing || mem.not_standing.length) + ')'),
        h('ul', { class: 'claims' }, mem.not_standing.map((c) => { const li = claimItem(item, c); if (c.where) li.prepend(h('div', { class: 'small muted' }, c.where)); return li; })),
        more > 0 ? h('p', { class: 'small muted' }, more + ' more are not listed here; the run folder’s recall.memory_audit.json has them all.') : null));
    }
    const out = [block];
    if (rc.memory) out.push(memoryBlock(item, rc.memory, 'What the model recalled before seeing the papers'));
    return out;
  }

  function cohortBlock(item, mc) {
    const c = item.cohort || {};
    const t = c.totals || {};
    const out = [];
    const kv = kvList();
    const ind = isNum(mc.individuals_pooled) ? mc.individuals_pooled : t.individuals;
    const fam = isNum(mc.families_pooled) ? mc.families_pooled : t.families;
    const rec = isNum(mc.records_pooled) ? mc.records_pooled : t.records;
    if (isNum(ind)) kv.row('Patients pooled', ind + (isNum(fam) ? ' in ' + plural(fam, 'family', 'families') : ''));
    if (isNum(rec)) kv.row('Case records pooled', String(rec));
    const fu = isNum(mc.follow_up_records) ? mc.follow_up_records : t.follow_up_records;
    const bg = isNum(mc.background_records) ? mc.background_records : t.background_records;
    if (fu) kv.row('Follow-up records (same patients reported again; not counted twice)', String(fu));
    if (bg) kv.row('Records from background papers (shown to the writer, never counted)', String(bg));
    if (isNum(mc.records_kept)) kv.row('Records kept / dropped (quote not found in the paper)', mc.records_kept + ' / ' + (mc.records_dropped_ungrounded || 0));
    if (isNum(mc.notes_kept)) kv.row('Notes kept / dropped', mc.notes_kept + ' / ' + (mc.notes_dropped_ungrounded || 0));
    if (isNum(mc.quote_grounding_rate)) kv.row('Quote grounding rate', fmt(mc.quote_grounding_rate, 'pct'));
    if (mc.papers_by_relevance) kv.row('Papers by relevance', countMap(mc.papers_by_relevance, (k) => RELEVANCE[k] || k));
    if ((mc.papers_failed || []).length) kv.row('Papers that failed extraction', mc.papers_failed.join(', '));
    if (mc.hpo_resolution && typeof mc.hpo_resolution === 'object') kv.row('HPO term resolution', countMap(mc.hpo_resolution));
    out.push(h('div', { class: 'cmp-block' }, h('h3', null, 'The case table behind this draft'),
      h('p', { class: 'small muted' }, 'Each paper was read once for the patients it reports: one record per patient, family or group, plus notes for results that are not about particular patients. The records were pooled into a table, and the synopsis, causal genes and inheritance were computed from it.'), kv));

    // genes and inheritance decisions
    const g = mc.genes || c.gene_decisions || {};
    const inh = mc.inheritance || c.inheritance || {};
    const kv2 = kvList();
    if ((g.candidates || []).length) kv2.row('Candidate genes (patient variants in the records)', g.candidates.join(', '));
    if ((g.confirmed || []).length) kv2.row('Confirmed as causing this disorder', g.confirmed.join(', '));
    if ((g.not_confirmed || []).length) kv2.row('Not confirmed (left out of the entry)', g.not_confirmed.join(', '));
    if ((g.dropped || []).length) kv2.row('Named by the writer but not a candidate (dropped)', g.dropped.join(', '));
    if ((inh.chosen || []).length) kv2.row('Mode of inheritance called', inh.chosen.map((x) => INHERITANCE[x] || x).join(', '));
    const sup = inh.support || {};
    const supKeys = Object.keys(sup);
    const dups = mc.possible_duplicates || c.possible_duplicates || [];
    const recLabel = (id) => { const r = item.recordBy.get(id); return r ? (r.label || id) + ' (' + paperLabel(item, r.pmid) + ')' : id; };
    kv2.row('Possible duplicate patients across papers', dups.length ? h('ul', { class: 'plain-list' }, dups.map((grp) => h('li', null, (Array.isArray(grp) ? grp : [grp]).map(recLabel).join(' and ')))) : 'None flagged');
    out.push(h('div', { class: 'cmp-block' }, h('h3', null, 'Genes and inheritance worked out from the records'), kv2,
      supKeys.length ? h('div', { class: 'table-scroll compare' }, h('table', { class: 'data' },
        h('caption', { class: 'visually-hidden' }, 'Evidence for each mode of inheritance'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Mode'), h('th', { class: 'n', scope: 'col' }, 'Patients'), h('th', { class: 'n', scope: 'col' }, 'Records'), h('th', { scope: 'col' }, 'Why (records)'), h('th', { scope: 'col' }, 'Papers'))),
        h('tbody', null, supKeys.map((k) => h('tr', null, h('td', null, INHERITANCE[k] || k), h('td', { class: 'n' }, count(sup[k].individuals)),
          h('td', { class: 'n' }, count(isNum(sup[k].n_records) ? sup[k].n_records : (sup[k].records || []).length)),
          h('td', null, countMap(sup[k].reasons) || '–'), h('td', { class: 'small' }, (sup[k].pmids || []).length ? citeLinks(item, sup[k].pmids) : '–')))))) : null));

    if (!item.cohort) {
      out.push(h('p', { class: 'small muted' }, 'The case table itself (cohort.json) was not saved with this entry, so only the summary above is available.'));
      return out;
    }
    const tr = c.trimmed || {};
    const ph = c.phenotypes || [];
    if (ph.length) {
      out.push(h('div', { class: 'cmp-block' }, h('h3', null, 'Feature frequencies (' + (tr.phenotypes ? tr.phenotypes.shown + ' of ' + tr.phenotypes.of : ph.length) + ')'),
        h('p', { class: 'small muted' }, 'Patients with the feature out of those in whom the papers say it was assessed. “At least” marks a lower bound: a paper said only that some patients had it.'),
        h('div', { class: 'table-scroll' + (ph.length > 14 ? ' tall' : '') }, h('table', { class: 'data' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Feature'), h('th', { scope: 'col' }, 'HPO'), h('th', { class: 'n', scope: 'col' }, 'Present / assessed'), h('th', { class: 'n', scope: 'col' }, 'Reported absent'), h('th', { class: 'n', scope: 'col' }, 'Records'), h('th', { scope: 'col' }, 'Papers'))),
          h('tbody', null, ph.map((p) => h('tr', null, h('td', null, p.label || p.hpo_id, p.from_follow_up ? h('span', { class: 'muted small' }, ' (from a follow-up report)') : null),
            h('td', null, hpoLink(p.hpo_id) || '–'),
            h('td', { class: 'n' }, (p.lower_bound ? 'at least ' : '') + count(p.present) + ' / ' + count(p.assessed)),
            h('td', { class: 'n' }, count(p.absent || 0)), h('td', { class: 'n' }, count(p.n_records)),
            h('td', { class: 'small' }, (p.pmids || []).length ? citeLinks(item, p.pmids) : '–'))))))));
    }
    const vs = c.variants || [];
    if (vs.length) {
      out.push(h('div', { class: 'cmp-block' }, h('h3', null, 'Variants in the case table (' + vs.length + ')'),
        h('div', { class: 'table-scroll' + (vs.length > 14 ? ' tall' : '') }, h('table', { class: 'data' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variant'), h('th', { scope: 'col' }, 'Gene'), h('th', { class: 'n', scope: 'col' }, 'Carriers'), h('th', { scope: 'col' }, 'Zygosity'), h('th', { scope: 'col' }, 'Origin'), h('th', { scope: 'col' }, 'Consequence'), h('th', { scope: 'col' }, 'Authors’ view'), h('th', { scope: 'col' }, 'Papers'))),
          h('tbody', null, vs.map((v) => h('tr', null, h('td', { class: 'mono' }, v.omim_name || (v.keys || []).join(' / ') || v.id, v.omim_name && (v.keys || []).length ? h('div', { class: 'small muted' }, v.keys.join(' / ')) : null),
            h('td', null, v.gene || '–'), h('td', { class: 'n' }, count(v.individuals)),
            h('td', null, countMap(v.zygosity) || '–'), h('td', null, countMap(v.origin) || '–'), h('td', null, v.consequence ? humanize(v.consequence) : '–'), h('td', null, countMap(v.authors) || '–'),
            h('td', { class: 'small' }, (v.pmids || []).length ? citeLinks(item, v.pmids) : '–'))))))));
    }
    const recs = c.records || [];
    if (recs.length) {
      out.push(h('div', { class: 'cmp-block' }, h('h3', null, 'Case records (' + (tr.records ? tr.records.shown + ' of ' + tr.records.of : recs.length) + ')'),
        h('div', { class: 'table-scroll' + (recs.length > 10 ? ' tall' : '') }, h('table', { class: 'data records' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Record'), h('th', { scope: 'col' }, 'Paper'), h('th', { scope: 'col' }, 'Variants'), h('th', { scope: 'col' }, h('abbr', { title: 'The mode of inheritance this record’s genotype implies, with the rule that gave it' }, 'Mode from genotype')), h('th', { scope: 'col' }, 'Features recorded'))),
          h('tbody', null, recs.map((r) => {
            const feats = r.phenotypes || [];
            const present = feats.filter((p) => p.present !== false);
            const vars = (r.variants || []).map((v) => (v.gene ? v.gene + ' ' : '') + (v.as_reported || v.key || '') + (v.zygosity && v.zygosity !== 'unknown' ? ' (' + humanize(v.zygosity).toLowerCase() + ')' : ''));
            return h('tr', null,
              h('td', { style: 'min-width:220px' }, h('strong', null, r.label || 'Unnamed record'), ' ', plainChip(RECORD_KIND[r.kind] || humanize(r.kind || '')), r.followup_of ? [' ', plainChip('Follow-up')] : null,
                recordSummary(r) ? h('div', { class: 'small muted' }, recordSummary(r)) : null,
                (r.quotes || []).length ? h('details', { class: 'more' }, h('summary', null, plural(isNum(r.n_quotes) ? r.n_quotes : r.quotes.length, 'quote')), quoteRows(r.quotes, r.quote_grounding)) : null),
              h('td', { class: 'small' }, ext(pubmedUrl(r.pmid), paperLabel(item, r.pmid))),
              h('td', { class: 'small mono' }, vars.length ? vars.map((v) => h('div', null, v)) : '–'),
              h('td', { class: 'small' }, r.genotype_mode ? [h('strong', null, INHERITANCE[r.genotype_mode] || r.genotype_mode), r.genotype_reason ? h('div', { class: 'muted' }, r.genotype_reason) : null] : (r.genotype_reason || '–')),
              h('td', { class: 'small' }, feats.length ? [present.slice(0, 6).map((p) => p.hpo_label || p.text).join('; '), feats.length > 6 ? h('span', { class: 'muted' }, ' … ' + feats.length + ' in all') : null]
                : isNum(r.n_phenotypes) ? plural(r.n_phenotypes, 'feature') : '–'));
          }))))));
    }
    const notes = c.notes || [];
    if (notes.length) {
      out.push(h('details', { class: 'more', open: state.open.has('cohort-notes') || null, ontoggle: (e) => { if (e.target.open) state.open.add('cohort-notes'); else state.open.delete('cohort-notes'); } },
        h('summary', { 'data-fid': 'cohort-notes' }, 'Notes: results not about particular patients (' + (tr.notes ? tr.notes.shown + ' of ' + tr.notes.of : notes.length) + ')'),
        h('ul', { class: 'findings' }, notes.map((n) => recordItem(item, n)))));
    }
    if (Object.keys(tr).length) {
      const bits = [];
      if (tr.records) bits.push(tr.records.shown + ' of ' + tr.records.of + ' records');
      if (tr.notes) bits.push(tr.notes.shown + ' of ' + tr.notes.of + ' notes');
      if (tr.phenotypes) bits.push(tr.phenotypes.shown + ' of ' + tr.phenotypes.of + ' features (the most frequent)');
      if (tr.record_features) bits.push('feature lists per record as counts only');
      if (tr.quotes) bits.push('one quote per record and note');
      out.push(h('p', { class: 'small muted' }, 'This case table was shortened to fit the page: ' + bits.join('; ') + '. The frequencies above were computed from the whole table; the run folder’s cohort.json has everything.'));
    }
    return out;
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
        loadEntry(it);
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
