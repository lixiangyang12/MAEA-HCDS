"""分析81组敏感性结果，找出失败组合的参数模式"""
import json

with open(r'c:\个人资料\申博材料\企业运营与科研管理数据库\p0_results\参数敏感性分析.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data['results']

print("=" * 80)
print("81组敏感性分析结果统计")
print("=" * 80)

n_cost_down = sum(1 for r in results if r['cost_reduction_pct'] > 0)
n_sl_up = sum(1 for r in results if r['sl_improvement_pp'] > 0)
n_both = sum(1 for r in results if r['cost_reduction_pct'] > 0 and r['sl_improvement_pp'] > 0)

print(f"总组合数: {len(results)}")
print(f"成本降低: {n_cost_down}/81 ({n_cost_down/81*100:.1f}%)")
print(f"SL提升:   {n_sl_up}/81 ({n_sl_up/81*100:.1f}%)")
print(f"双目标:   {n_both}/81 ({n_both/81*100:.1f}%)")

# 按参数分组统计
print("\n" + "=" * 80)
print("按 w_s 分组")
print("=" * 80)
for ws in [1.0, 2.0, 4.0]:
    grp = [r for r in results if r['params']['w_s'] == ws]
    n_c = sum(1 for r in grp if r['cost_reduction_pct'] > 0)
    n_s = sum(1 for r in grp if r['sl_improvement_pp'] > 0)
    n_b = sum(1 for r in grp if r['cost_reduction_pct'] > 0 and r['sl_improvement_pp'] > 0)
    avg_cr = sum(r['cost_reduction_pct'] for r in grp) / len(grp)
    avg_sl = sum(r['sl_improvement_pp'] for r in grp) / len(grp)
    print(f"  w_s={ws}: 成本↓{n_c}/27, SL↑{n_s}/27, 双目标{n_b}/27 | 均Δ成本={avg_cr:+.3f}%, 均ΔSL={avg_sl:+.4f}pp")

print("\n" + "=" * 80)
print("按 sigma_noise 分组")
print("=" * 80)
for sn in [0.0, 0.15, 0.30]:
    grp = [r for r in results if r['params']['sigma_noise'] == sn]
    n_c = sum(1 for r in grp if r['cost_reduction_pct'] > 0)
    n_s = sum(1 for r in grp if r['sl_improvement_pp'] > 0)
    n_b = sum(1 for r in grp if r['cost_reduction_pct'] > 0 and r['sl_improvement_pp'] > 0)
    avg_cr = sum(r['cost_reduction_pct'] for r in grp) / len(grp)
    avg_sl = sum(r['sl_improvement_pp'] for r in grp) / len(grp)
    print(f"  σ_noise={sn}: 成本↓{n_c}/27, SL↑{n_s}/27, 双目标{n_b}/27 | 均Δ成本={avg_cr:+.3f}%, 均ΔSL={avg_sl:+.4f}pp")

print("\n" + "=" * 80)
print("按 sigma_eps 分组")
print("=" * 80)
for se in [5, 7, 10]:
    grp = [r for r in results if r['params']['sigma_eps'] == se]
    n_c = sum(1 for r in grp if r['cost_reduction_pct'] > 0)
    n_s = sum(1 for r in grp if r['sl_improvement_pp'] > 0)
    n_b = sum(1 for r in grp if r['cost_reduction_pct'] > 0 and r['sl_improvement_pp'] > 0)
    avg_cr = sum(r['cost_reduction_pct'] for r in grp) / len(grp)
    avg_sl = sum(r['sl_improvement_pp'] for r in grp) / len(grp)
    print(f"  σ_ε={se}: 成本↓{n_c}/27, SL↑{n_s}/27, 双目标{n_b}/27 | 均Δ成本={avg_cr:+.3f}%, 均ΔSL={avg_sl:+.4f}pp")

print("\n" + "=" * 80)
print("按 L 分组")
print("=" * 80)
for L in [1, 2, 3]:
    grp = [r for r in results if r['params']['L'] == L]
    n_c = sum(1 for r in grp if r['cost_reduction_pct'] > 0)
    n_s = sum(1 for r in grp if r['sl_improvement_pp'] > 0)
    n_b = sum(1 for r in grp if r['cost_reduction_pct'] > 0 and r['sl_improvement_pp'] > 0)
    avg_cr = sum(r['cost_reduction_pct'] for r in grp) / len(grp)
    avg_sl = sum(r['sl_improvement_pp'] for r in grp) / len(grp)
    print(f"  L={L}: 成本↓{n_c}/27, SL↑{n_s}/27, 双目标{n_b}/27 | 均Δ成本={avg_cr:+.3f}%, 均ΔSL={avg_sl:+.4f}pp")

# 成本升高组合
print("\n" + "=" * 80)
print("成本升高的组合 (Δ成本<0)")
print("=" * 80)
cost_up = [r for r in results if r['cost_reduction_pct'] <= 0]
cost_up.sort(key=lambda x: x['cost_reduction_pct'])
for r in cost_up:
    p = r['params']
    print(f"  w_s={p['w_s']}, σ={p['sigma_noise']}, σ_ε={p['sigma_eps']}, L={p['L']} | "
          f"Δ成本={r['cost_reduction_pct']:+.3f}% | ΔSL={r['sl_improvement_pp']:+.4f}pp")

# SL降低组合
print("\n" + "=" * 80)
print("SL降低最多的组合 (top 10)")
print("=" * 80)
sl_down = sorted(results, key=lambda x: x['sl_improvement_pp'])[:10]
for r in sl_down:
    p = r['params']
    print(f"  w_s={p['w_s']}, σ={p['sigma_noise']}, σ_ε={p['sigma_eps']}, L={p['L']} | "
          f"Δ成本={r['cost_reduction_pct']:+.3f}% | ΔSL={r['sl_improvement_pp']:+.4f}pp")
