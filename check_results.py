import json

d = json.load(open('p0_results/参数敏感性分析.json', 'r', encoding='utf-8'))
for r in d['results']:
    p = r['params']
    print(f"\nparams: w_s={p['w_s']}, σ_noise={p['sigma_noise']}, σ_ε={p['sigma_eps']}, L={p['L']}")
    e2 = r['exp2']
    bs = r['baseline']
    e2_sl = [f"{e2['sl'][str(k)]*100:.1f}%" for k in range(1, 5)]
    bs_sl = [f"{bs['sl'][str(k)]*100:.1f}%" for k in range(1, 5)]
    print(f"  Exp2:  cost={e2['total_cost']:.1f}  SL={e2['avg_sl']*100:.2f}%  per-node=[{', '.join(e2_sl)}]")
    print(f"  Base:  cost={bs['total_cost']:.1f}  SL={bs['avg_sl']*100:.2f}%  per-node=[{', '.join(bs_sl)}]")
    print(f"  Δcost={r['cost_reduction_pct']:.1f}%  ΔSL={r['sl_improvement_pp']:.1f}pp")
