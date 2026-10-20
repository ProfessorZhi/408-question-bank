#!/usr/bin/env python3
"""Separate-algorithm author cross-check for Set 01 OS Q46 and CN Q47.

This uses exhaustive SIMPLE PATH enumeration rather than the main verifier's
shortest-path relaxation; its COW simulator uses ownership-indexed PTEs and
two counterfactual memory policies. It remains AUTHOR-WRITTEN testing, not
independent expert review or exam difficulty measurement.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations, permutations
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "specs" / "exam.json").read_text(encoding="utf-8"))


def route_oracle():
    p = SPEC["q47"]
    nodes = p["nodes"]
    destination = p["destination"]
    actors = [r for r in nodes if r != destination]
    old_next, new_next = {}, {}
    for epoch in ("old", "new"):
        neighbors = defaultdict(list)
        for e in p["edges"]:
            u, v, cost = e["u"], e["v"], e[epoch + "_cost"]
            neighbors[u].append((v, cost))
            neighbors[v].append((u, cost))
        table = {}
        for source in actors:
            candidates = []

            def visit(node, path, cost):
                if node == destination:
                    candidates.append((cost, tuple(path)))
                    return
                for nxt, weight in neighbors[node]:
                    if nxt not in path:
                        visit(nxt, path + [nxt], cost + weight)
            visit(source, [source], 0)
            shortest_cost = min(x[0] for x in candidates)
            optimal = [x for x in candidates if x[0] == shortest_cost]
            assert len(optimal) == 1, (epoch, source, optimal)
            table[source] = optimal[0][1][1]
        assert table == p["expected_" + epoch + "_next"], (epoch, table)
        if epoch == "old":
            old_next = table
        else:
            new_next = table

    def has_cycle(table):
        for origin in actors:
            visited = set()
            current = origin
            while current != destination:
                if current in visited:
                    return True
                visited.add(current)
                current = table[current]
        return False

    safe_subsets = []
    for mask in range(1 << len(actors)):
        changed = {router for i, router in enumerate(actors) if mask & (1 << i)}
        table = {r: new_next[r] if r in changed else old_next[r] for r in actors}
        if not has_cycle(table):
            safe_subsets.append(tuple(r for r in actors if r in changed))
    assert safe_subsets == [(), ("R1",), ("R1", "R2"), ("R1", "R2", "R3")], safe_subsets

    safe_orders = []
    for order in permutations(actors):
        changed = set()
        if all(
            not has_cycle({r: new_next[r] if r in changed else old_next[r] for r in actors})
            for _ in [0]
        ):
            ok = True
            for r in order:
                changed.add(r)
                mixed = {u: new_next[u] if u in changed else old_next[u] for u in actors}
                if has_cycle(mixed):
                    ok = False
                    break
            if ok:
                safe_orders.append(order)
    assert safe_orders == [tuple(p["expected_safe_update_order"])]

    current = p["source_router"]
    mixed = dict(old_next)
    mixed[p["first_updated"]] = new_next[p["first_updated"]]
    ttl = p["initial_ttl"]
    visits = []
    while True:
        visits.append(current)
        ttl -= 1
        if ttl == 0:
            dropped_at = current
            break
        current = mixed[current]
        assert len(visits) < 10
    assert visits == ["R1", "R2", "R1", "R2"] and dropped_at == "R2"
    return {"simple_path_oracle": True, "mixed_tables_exhausted": 8,
            "safe_subsets": safe_subsets, "update_orders_exhausted": 6,
            "safe_order": safe_orders[0], "ttl_visits": visits}


def cow_oracle(eager_clear_on_exit=False, clone_even_if_solo=False):
    p = SPEC["q46"]
    owners = {x["initial_frame"]: set(p["processes"]) for x in p["pages"]}
    values = {x["initial_frame"]: x["initial_value"] for x in p["pages"]}
    pt = {who: {x["vpn"]: [x["initial_frame"], False] for x in p["pages"]}
          for who in p["processes"]}
    fresh = p["next_fresh_frame"]
    faults, copies, snapshots = [], [], {}
    for step, event in enumerate(p["operations"], 1):
        who = event["process"]
        if event["type"] == "exit":
            for frame, writable in pt.pop(who).values():
                owners[frame].remove(who)
            if eager_clear_on_exit:
                for proc, table in pt.items():
                    for vpn, mapping in table.items():
                        frame, writable = mapping
                        if len(owners[frame]) == 1:
                            mapping[1] = True
            continue
        vpn = event["vpn"]
        frame, writable = pt[who][vpn]
        if not writable:
            faults.append(step)
            if len(owners[frame]) > 1 or clone_even_if_solo:
                values[fresh] = values[frame]
                owners[fresh] = {who}
                owners[frame].remove(who)
                pt[who][vpn] = [fresh, True]
                copies.append((step, fresh))
                frame = fresh
                fresh += 1
            else:
                pt[who][vpn][1] = True
        values[frame] = event["value"]
        if step == 3:
            snapshots = {
                proc: tuple(values[pt[proc][x["vpn"]][0]] for x in p["pages"])
                for proc in p["processes"]
            }
    final = tuple(values[pt["P"][x["vpn"]][0]] for x in p["pages"])
    return {"faults": faults, "copies": copies, "after_step3": snapshots, "final_parent": final}


def main():
    routing = route_oracle()
    normal = cow_oracle()
    eager = cow_oracle(eager_clear_on_exit=True)
    clone = cow_oracle(clone_even_if_solo=True)
    assert normal["faults"] == [1, 2, 3, 5]
    assert normal["copies"] == [(1, 9), (3, 10)]
    assert normal["after_step3"] == {"P": (12, 21, 30), "C": (11, 20, 30)}
    assert normal["final_parent"] == (12, 21, 31)
    assert eager["faults"] == [1, 2, 3], "eager permission restoration should remove the last fault"
    assert clone["faults"] == [1, 2, 3, 5]
    assert len(clone["copies"]) == 4, "always-clone counterfactual must differ in actual page allocations"
    print("[audit-v3] Q46: independent page-ownership simulator PASS; counterfactual PTE and cloning policies alter result")
    print("[audit-v3] Q47: enumerated simple paths, 8 mixed tables, 6 update orders and TTL=4 trace PASS")
    print("[audit-v3] WARNING: separate algorithms by the same author; no independent expert or timed pilot")


if __name__ == "__main__":
    main()
