"""Pure helpers of the A1 large-entry tier (selection rule and analysis)."""

from aiomim import largetier as lt


def test_mims_in_skips_header_comments_and_duplicates():
    lines = ["# comment 123", "mim\tn_refs", "600116\t39", "128100\t60", "600116\t39", ""]
    assert lt.mims_in(lines) == ["600116", "128100"]


def test_seeded_order_is_reproducible_and_input_order_free():
    a = lt.seeded_order(["3", "1", "2", "10"], 5)
    b = lt.seeded_order(["10", "2", "1", "3", "3"], 5)
    assert a == b and sorted(a, key=int) == ["1", "2", "3", "10"]
    assert lt.seeded_order(["1", "2", "3", "10"], 6) != a or len(a) < 3


def test_rank_key_orders_by_count_then_entry_number():
    rows = {"600002": 7, "600001": 7, "100000": 9, "100001": 2}
    assert sorted(rows, key=lambda m: lt.rank_key(m, rows[m])) == ["100000", "600001", "600002", "100001"]


def test_exact_top_k_matches_full_resolution_and_stops_early():
    true = {"1": 5, "2": 9, "3": 0, "4": 7, "5": 7, "6": 1, "7": 3}
    bounds = {"1": 6, "2": 12, "3": 1, "4": 7, "5": 9, "6": 30, "7": 4}
    calls = []

    def resolve(m):
        calls.append(m)
        return true[m]

    top, resolved = lt.exact_top_k(bounds, resolve, 3)
    full = sorted(true, key=lambda m: lt.rank_key(m, true[m]))[:3]
    assert top == full == ["2", "4", "5"]
    # "1" (bound 6) cannot beat the third place (7), nor can anything after it.
    assert set(calls) == {"6", "2", "5", "4"}
    assert all(resolved[m] == true[m] for m in resolved)


def test_exact_top_k_tie_on_bound_goes_to_lower_number():
    true = {"10": 3, "20": 3, "5": 3}
    bounds = {"10": 3, "20": 3, "5": 3}
    top, resolved = lt.exact_top_k(bounds, lambda m: true[m], 2)
    assert top == ["5", "10"] and "20" not in resolved


def test_threshold_lowered_only_when_needed():
    assert lt.threshold_used([9, 8, 5]) == 5
    assert lt.threshold_used([9, 8, 3]) == 3
    assert lt.threshold_used([]) == 5


def test_sign_test_exact_values():
    assert lt.sign_test(0, 0) is None
    assert lt.sign_test(5, 0) == 2 / 32
    assert abs(lt.sign_test(3, 3) - 1.0) < 1e-12
    assert abs(lt.sign_test(1, 7) - 2 * 9 / 256) < 1e-12


def test_bootstrap_ci_brackets_the_mean_and_needs_three_values():
    assert lt.bootstrap_ci([0.1, 0.2]) is None
    lo, hi = lt.bootstrap_ci([0.1, 0.2, 0.3, 0.0, -0.1, 0.25])
    assert lo <= sum([0.1, 0.2, 0.3, 0.0, -0.1, 0.25]) / 6 <= hi
    lo, hi = lt.bootstrap_ci([0.05] * 6)
    assert abs(lo - 0.05) < 1e-12 and abs(hi - 0.05) < 1e-12


def test_paired_counts_and_means():
    res = lt.paired({"a": (0.5, 0.4), "b": (0.3, 0.3), "c": (0.2, 0.6)})
    assert (res["better"], res["worse"], res["tied"], res["n"]) == (1, 1, 1, 3)
    assert abs(res["mean_diff"] - (0.1 + 0 - 0.4) / 3) < 1e-4
    assert res["sign_p"] == 1.0


def test_median_split_puts_median_in_lower_half():
    med, lower, upper = lt.median_split({"1": 10, "2": 20, "3": 30, "4": 40})
    assert med == 25 and lower == ["1", "2"] and upper == ["3", "4"]
    med, lower, upper = lt.median_split({"1": 10, "2": 20, "3": 30})
    assert med == 20 and lower == ["1", "2"] and upper == ["3"]
    assert lt.median_split({}) == (None, [], [])


def test_direct_prompts_from_meta():
    assert lt.direct_prompts({"direct_batching": {"used": False}}) == 1
    assert lt.direct_prompts({"direct_batching": {"used": True, "batches": [{}, {}, {}]}}) == 4
    assert lt.direct_prompts({"direct_batching": {"used": True, "batches": [{}]}}) == 1
    assert lt.direct_prompts({}) is None


def test_direct_cut_single_prompt_and_batched():
    # 40 papers: the single-prompt share is max(20,000, 15,000) = 20,000 per paper.
    sizes = [1_000] * 38 + [25_000, 100_000]
    assert lt.direct_cut(sizes, batched=False) == (2, 5_000 + 80_000)
    assert lt.direct_cut(sizes, batched=True) == (0, 0)
    assert lt.direct_cut([700_000, 10], batched=True) == (1, 100_000)
    # 10 papers: share 60,000.
    assert lt.direct_cut([59_000] * 9 + [61_000], batched=False) == (1, 1_000)


def test_reference_share():
    n, share = lt.reference_share([["1", "2"], ["2", "9"]], ["1", "2", "3", "4"])
    assert (n, share) == (2, 0.5)
    assert lt.reference_share([], []) == (0, None)


def test_marking_calls_skips_paragraphs_without_draft_text():
    frozen = {"paragraphs": [
        {"facts": [{"id": "a", "status": "present", "note": "x"}]},
        {"facts": [{"id": "b", "status": "absent", "note": lt.NO_DRAFT_NOTE}]},
        {"facts": []},
        {"facts": [{"id": "c", "status": "absent", "note": ""}], "mark_attempts": 2},
    ]}
    assert lt.marking_calls(frozen) == 3


def test_read_timing_sums_resumed_passes(tmp_path):
    p = tmp_path / "timing.tsv"
    p.write_text("600116\tdirect\t0\t100\t100\t0\t0\t5\t1\t0.5\n"
                 "600116\tdirect\t200\t260\t60\t0\t1\t7\t5\t0.2\n"
                 "600116\tkg\t0\t10\t10\t1\t0\tNA\tNA\tNA\n")
    t = lt.read_timing(p)
    assert t[("600116", "direct")] == {"wall_seconds": 160, "passes": 2, "new_calls": 6, "usd_now": 0.7, "ok": True}
    assert t[("600116", "kg")]["new_calls"] == 0 and not t[("600116", "kg")]["ok"]


def test_exact_top_k_batched_gives_the_same_top():
    true = {str(i): (i * 7) % 11 for i in range(1, 30)}
    bounds = {m: v + (int(m) % 3) for m, v in true.items()}
    full = sorted(true, key=lambda m: lt.rank_key(m, true[m]))[:5]
    for batch in (1, 2, 4, 7):
        top, resolved = lt.exact_top_k(bounds, lambda m: true[m], 5, batch=batch)
        assert top == full


def test_counts_from_log_reads_resolved_lines_last_wins():
    lines = ["03:26:51 INFO    resolved 222100: 9 of 142 readable in full (bound 50)",
             "03:25:36 INFO    sample: 25 eligible after 394 candidates walked",
             "03:53:27 INFO    resolved 222100: 9 of 142 readable in full (bound 50)",
             "04:00:00 INFO    resolved 155600: 33 of 119 readable in full (bound 54)"]
    assert lt.counts_from_log(lines) == {"222100": 9, "155600": 33}


def test_resolution_events_in_log_order():
    lines = ["03:26:51 INFO    resolved 222100: 9 of 142 readable in full (bound 50)",
             "=== restart ===",
             "03:30:17 INFO    resolved 155600: 33 of 119 readable in full (bound 54)"]
    assert lt.resolution_events(lines) == [("03:26:51", "222100", 9), ("03:30:17", "155600", 33)]


def test_first_certain_waits_until_fewer_than_k_could_rank_above():
    bounds = {"1": 10, "2": 9, "3": 8, "4": 3}
    events = [("t1", "3", 6), ("t2", "1", 2), ("t3", "2", 7)]
    # k = 1: "3" (6) is certain only once both "1" and "2" are resolved below or above it.
    assert lt.first_certain(events, bounds, "3", 1) is None          # "2" (7) ranks above it
    assert lt.first_certain(events, bounds, "2", 1) == (2, "t3")
    # k = 2: after "1" resolves to 2, only "2" (bound 9) could be above "3".
    assert lt.first_certain(events, bounds, "3", 2) == (1, "t2")


def test_selection_state_finished_and_threats():
    bounds = {"1": 10, "2": 9, "3": 8, "4": 5, "5": 7}
    st = lt.selection_state(bounds, {"1": 9, "2": 7, "3": 6}, 2)
    assert st["top"] == ["1", "2"] and st["finished"] and st["could_displace"] == []
    assert st["max_unresolved_bound"] == 7 and st["unresolved"] == ["4", "5"]
    st = lt.selection_state(bounds, {"1": 9, "2": 6, "3": 6}, 2)
    assert st["could_displace"] == ["5"] and not st["finished"]      # bound 7 > 6
    st = lt.selection_state({"1": 4, "7": 6}, {"1": 4}, 2)
    assert st["could_displace"] == ["7"]                             # fewer than k resolved


def test_text_windows_and_leaked():
    assert lt.text_windows("a  b", 60) == ["a b"]
    w = lt.text_windows("x" * 100, 60, 30)
    assert len(w) == 2 and all(len(s) == 60 for s in w)
    gold = ["Davies et al. (2002) identified a transversion in exon 15 of the gene that leads to a substitution.",
            "short fact"]
    hay = "prefix Davies et al. (2002) identified a transversion in exon 15 of the gene that leads to a substitution. end"
    assert lt.leaked(gold, hay) and not lt.leaked(gold, "unrelated text " * 20)
    assert lt.leaked(["short fact"], "short fact") == []               # below the length floor


def _rec(mim, **cov):
    st = {}
    for s in lt.STRATEGIES:
        v = cov.get(s)
        if v is None:
            st[s] = {"status": "no_draft"}
        elif isinstance(v, tuple):
            st[s] = {"status": "incomplete", "coverage": v[0]}
        else:
            st[s] = {"status": "complete", "coverage": v}
    return {"mim": mim, "strategies": st}


def test_compare_block_and_pairwise_views():
    recs = [_rec("1", direct=0.5, agent=0.4, kg=0.6, cohort=0.5),
            _rec("2", direct=0.3, agent=0.3, kg=(0.2,), cohort=0.4),
            _rec("3", agent=0.7, kg=0.6, cohort=0.6)]
    assert lt.compare_block(recs)["entries"] == ["1"]
    assert lt.compare_block(recs, allow_incomplete=True)["entries"] == ["1", "2"]
    pw = lt.pairwise_with_direct(recs)
    assert pw["agent"]["entries"] == ["1", "2"] and pw["kg"]["entries"] == ["1", "2"]
    assert pw["agent"]["worse"] == 1 and pw["agent"]["tied"] == 1


def test_run_entries_needs_every_strategy(tmp_path):
    p = tmp_path / "timing.tsv"
    rows = [f"1\t{s}\t0\t1\t1\t0\t1\t1\t0\t0" for s in lt.STRATEGIES]
    rows += [f"2\t{s}\t0\t1\t1\t0\t1\t1\t0\t0" for s in lt.STRATEGIES[:3]]
    p.write_text("\n".join(rows) + "\n")
    assert lt.run_entries(p) == ["1"]
