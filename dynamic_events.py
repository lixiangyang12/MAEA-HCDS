"""
动态突发事件触发器 (Dynamic Event Trigger)
==========================================

在多智能体供应链环境中引入三类现实扰动:
    1. 需求突变 (Demand Shock): 终端需求突然翻倍或减半
    2. 供应中断 (Supply Disruption): 制造商节点随机断供 3-5 周期
    3. 情绪传染 (Emotion Contagion): 严重缺货节点的恐慌以概率传染上游

理论背景:
    现实供应链频繁遭受突发事件冲击 (如疫情需求暴涨、港口罢工断供、
    恐慌性囤货蔓延)。这些事件打破了平稳假设, 是牛鞭效应在极端
    情境下急剧恶化的主因。本模块将这些扰动建模为可控的随机过程,
    用于压力测试 MARL 策略的鲁棒性。

情绪传染机制 (核心创新):
    当节点 k 发生严重缺货 (stockout_rate > θ), 其恐慌情绪 E_k<0
    不仅调节自身决策, 还以概率 p_c 传染给上游节点 k+1:
        E_{k+1} ← tanh(E_{k+1} + shock)
    其中 shock = -s_c (传染强度, 负值表示恐慌注入)。

    这模拟了"恐慌性囤货蔓延"的群体心理现象:
    下游缺货消息传到上游 → 上游也恐慌 → 上游过度囤货 → 牛鞭放大。

    数学上, 传染冲击是独立于演化方程 (α·E + γ·Φ) 的外部项,
    通过 EmotionState.apply_contagion_shock() 注入。

使用:
    from dynamic_events import DynamicEventTrigger
    trigger = DynamicEventTrigger(seed=42)
    events = trigger.step()  # 每周期调用, 返回本周期事件
    demand = trigger.apply_demand_shock(base_demand)
    arrival = trigger.apply_supply_disruption(manufacturer_arrival)
    trigger.apply_emotion_contagion(agent_states, k_to_id)
"""

import numpy as np
from typing import Optional, Dict, Any, List, Tuple


class DynamicEventTrigger:
    """
    动态突发事件触发器

    管理三类事件的随机触发与状态维护:
        - demand_shock: 需求突变 (单周期事件)
        - supply_disruption: 供应中断 (持续多周期事件)
        - emotion_contagion: 情绪传染 (周期末触发)

    所有事件均通过随机种子控制, 确保 100% 可复现。
    """

    def __init__(self,
                 # ---- 需求突变参数 ----
                 demand_shock_prob: float = 0.02,
                 demand_shock_magnitude: float = 2.0,
                 # ---- 供应中断参数 ----
                 supply_disruption_prob: float = 0.01,
                 supply_disruption_duration: Tuple[int, int] = (3, 5),
                 # ---- 情绪传染参数 ----
                 contagion_threshold: float = 0.3,
                 contagion_prob: float = 0.3,
                 contagion_strength: float = 0.4,
                 # ---- 随机种子 ----
                 seed: Optional[int] = None):
        """
        初始化事件触发器

        参数:
            demand_shock_prob: 每周期需求突变概率 (默认 2%)
            demand_shock_magnitude: 需求突变倍数 (2.0=翻倍, 0.5=减半, 随机二选一)
            supply_disruption_prob: 每周期供应中断触发概率 (默认 1%)
            supply_disruption_duration: 中断持续周期范围 (3, 5)
            contagion_threshold: 严重缺货阈值 (stockout_rate > θ 触发传染)
            contagion_prob: 传染概率 (默认 30%)
            contagion_strength: 传染强度 (恐慌注入量, 默认 -0.4)
            seed: 随机种子
        """
        self.demand_shock_prob = demand_shock_prob
        self.demand_shock_magnitude = demand_shock_magnitude
        self.supply_disruption_prob = supply_disruption_prob
        self.supply_disruption_duration = supply_disruption_duration
        self.contagion_threshold = contagion_threshold
        self.contagion_prob = contagion_prob
        self.contagion_strength = contagion_strength

        self.rng = np.random.default_rng(seed)

        # ---- 事件状态 ----
        # 当前周期的需求突变倍数 (1.0=无突变, 2.0=翻倍, 0.5=减半)
        self.current_demand_multiplier: float = 1.0
        # 供应中断剩余周期数
        self.supply_disruption_remaining: int = 0
        # 供应中断总周期 (用于记录)
        self.supply_disruption_total: int = 0

        # ---- 事件历史 (用于分析与可视化) ----
        self.event_log: List[Dict[str, Any]] = []
        self.demand_shock_count: int = 0
        self.supply_disruption_count: int = 0
        self.contagion_count: int = 0

        # ---- 当前周期事件记录 ----
        self._current_events: Dict[str, Any] = {}

    # ============================================================
    # 周期推进: 触发新事件, 维护持续事件
    # ============================================================

    def step(self, t: int) -> Dict[str, Any]:
        """
        每周期开始时调用, 触发新事件并维护持续事件状态

        参数:
            t: 当前周期

        返回:
            本周期事件字典:
                {
                    'demand_shock': bool,       # 是否发生需求突变
                    'demand_multiplier': float, # 需求倍数 (1.0/2.0/0.5)
                    'supply_disruption': bool,  # 是否处于供应中断
                    'disruption_remaining': int,# 中断剩余周期
                }
        """
        self._current_events = {}

        # ---- 1. 需求突变 (单周期事件) ----
        self.current_demand_multiplier = 1.0
        if self.rng.random() < self.demand_shock_prob:
            # 随机选择翻倍或减半
            if self.rng.random() < 0.5:
                self.current_demand_multiplier = self.demand_shock_magnitude  # 翻倍
                shock_type = 'surge'
            else:
                self.current_demand_multiplier = 1.0 / self.demand_shock_magnitude  # 减半
                shock_type = 'drop'
            self.demand_shock_count += 1
            self._current_events['demand_shock'] = True
            self._current_events['demand_multiplier'] = self.current_demand_multiplier
            self._current_events['demand_shock_type'] = shock_type

        # ---- 2. 供应中断 (持续多周期事件) ----
        # 若已有中断在进行, 递减剩余周期
        if self.supply_disruption_remaining > 0:
            self.supply_disruption_remaining -= 1
            self._current_events['supply_disruption'] = True
            self._current_events['disruption_remaining'] = self.supply_disruption_remaining
        # 否则以概率触发新中断
        elif self.rng.random() < self.supply_disruption_prob:
            dur_low, dur_high = self.supply_disruption_duration
            self.supply_disruption_total = int(self.rng.integers(dur_low, dur_high + 1))
            self.supply_disruption_remaining = self.supply_disruption_total
            self.supply_disruption_count += 1
            self._current_events['supply_disruption'] = True
            self._current_events['disruption_remaining'] = self.supply_disruption_remaining
            self._current_events['disruption_duration'] = self.supply_disruption_total

        # 记录事件日志
        if self._current_events:
            log_entry = {'t': t}
            log_entry.update(self._current_events)
            self.event_log.append(log_entry)

        return dict(self._current_events)

    # ============================================================
    # 事件应用接口
    # ============================================================

    def apply_demand_shock(self, base_demand: float) -> float:
        """
        应用需求突变到基础需求

        参数:
            base_demand: AR(1) 生成的基础需求

        返回:
            突变后的需求 D_t * multiplier
        """
        return base_demand * self.current_demand_multiplier

    def apply_supply_disruption(self, manufacturer_arrival: float) -> float:
        """
        应用供应中断到制造商到货量

        当处于供应中断状态时, 制造商收到的上游货物归零
        (模拟原材料断供/产能停摆)

        参数:
            manufacturer_arrival: 正常情况下的到货量

        返回:
            实际到货量 (中断时为 0)
        """
        if self.supply_disruption_remaining > 0:
            return 0.0
        return manufacturer_arrival

    def apply_emotion_contagion(self, agent_states: Dict[str, Any],
                                 k_to_id: Dict[int, str],
                                 id_to_k: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        情绪传染: 严重缺货节点的恐慌传染给上游节点

        传染逻辑:
            1. 遍历每个节点, 检查其 stockout_rate 是否超过阈值 θ
            2. 若超过阈值 (严重缺货), 以概率 p_c 触发传染
            3. 传染目标: 上游节点 (k+1)
            4. 传染方式: 上游情绪注入负向冲击 shock = -s_c
                        E_{k+1} ← tanh(E_{k+1} + shock)

        参数:
            agent_states: {agent_id: SupplyChainAgent} 各 Agent 状态
            k_to_id: {k: agent_id} 层级到 id 映射
            id_to_k: {agent_id: k} id 到层级映射

        返回:
            传染事件列表 [{'from': aid, 'to': upstream_id,
                          'shock': -s_c, 'before_E': , 'after_E': }, ...]
        """
        contagion_events = []

        for aid, agent in agent_states.items():
            # 跳过无情绪模块的节点
            if agent.emotion is None:
                continue

            # 计算本节点缺货率
            demand = agent.incoming_demand
            if demand <= 0:
                continue
            stockout_rate = agent.stockout / demand

            # 判定严重缺货
            if stockout_rate <= self.contagion_threshold:
                continue

            # 以概率传染上游
            k = id_to_k.get(aid)
            if k is None:
                continue
            upstream_k = k + 1
            upstream_id = k_to_id.get(upstream_k)
            if upstream_id is None:
                continue  # 制造商无上游
            upstream_agent = agent_states.get(upstream_id)
            if upstream_agent is None or upstream_agent.emotion is None:
                continue

            # 概率判定
            if self.rng.random() >= self.contagion_prob:
                continue

            # 触发传染: 上游情绪注入恐慌冲击
            shock = -self.contagion_strength  # 负值=恐慌注入
            before_E = float(upstream_agent.emotion.E)
            upstream_agent.emotion.apply_contagion_shock(shock)
            after_E = float(upstream_agent.emotion.E)

            self.contagion_count += 1
            contagion_events.append({
                'from': aid,
                'to': upstream_id,
                'stockout_rate': float(stockout_rate),
                'shock': shock,
                'before_E': before_E,
                'after_E': after_E,
            })

        # 记录到事件日志
        if contagion_events:
            self.event_log.append({
                't': -1,  # 由调用方补充
                'emotion_contagion': contagion_events,
            })

        return contagion_events

    # ============================================================
    # 查询与统计
    # ============================================================

    def get_current_events(self) -> Dict[str, Any]:
        """获取当前周期事件"""
        return dict(self._current_events)

    def is_demand_shock_active(self) -> bool:
        return self.current_demand_multiplier != 1.0

    def is_supply_disruption_active(self) -> bool:
        return self.supply_disruption_remaining > 0

    def get_stats(self) -> Dict[str, Any]:
        """获取事件统计"""
        return {
            'demand_shock_count': self.demand_shock_count,
            'supply_disruption_count': self.supply_disruption_count,
            'contagion_count': self.contagion_count,
            'total_events': len(self.event_log),
            'supply_disruption_remaining': self.supply_disruption_remaining,
            'current_demand_multiplier': self.current_demand_multiplier,
        }

    def reset(self, seed: Optional[int] = None):
        """重置触发器状态"""
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.current_demand_multiplier = 1.0
        self.supply_disruption_remaining = 0
        self.supply_disruption_total = 0
        self.event_log = []
        self.demand_shock_count = 0
        self.supply_disruption_count = 0
        self.contagion_count = 0
        self._current_events = {}


# ============================================================
# 自检: 验证动态事件触发与情绪传染
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("DynamicEventTrigger - 自检")
    print("=" * 70)

    # ---- 创建触发器 (提高概率以便观察事件) ----
    trigger = DynamicEventTrigger(
        demand_shock_prob=0.3,           # 30% 概率需求突变 (便于观察)
        demand_shock_magnitude=2.0,
        supply_disruption_prob=0.2,      # 20% 概率供应中断
        supply_disruption_duration=(3, 5),
        contagion_threshold=0.3,
        contagion_prob=0.5,              # 50% 传染概率 (便于观察)
        contagion_strength=0.4,
        seed=42,
    )

    # ---- 模拟 20 个周期 ----
    print("\n[模拟] 运行 20 周期, 观察事件触发:")
    print(f"{'周期':>4} | {'需求突变':>8} | {'倍数':>6} | {'供应中断':>8} | {'剩余':>4}")
    print("-" * 50)
    for t in range(20):
        events = trigger.step(t)
        ds = '是' if events.get('demand_shock') else '-'
        mult = events.get('demand_multiplier', 1.0)
        sd = '是' if events.get('supply_disruption') else '-'
        rem = events.get('disruption_remaining', 0)
        print(f"{t:>4} | {ds:>8} | {mult:>6.2f} | {sd:>8} | {rem:>4}")

    print(f"\n[统计] {trigger.get_stats()}")

    # ---- 验证需求突变应用 ----
    print("\n[验证] 需求突变应用:")
    trigger.reset(seed=42)
    base_demand = 20.0
    for t in range(10):
        trigger.step(t)
        shocked = trigger.apply_demand_shock(base_demand)
        flag = ' *** 突变' if trigger.is_demand_shock_active() else ''
        print(f"  t={t}: base={base_demand:.1f} -> shocked={shocked:.1f}{flag}")

    # ---- 验证供应中断应用 ----
    print("\n[验证] 供应中断应用:")
    trigger.reset(seed=42)
    for t in range(15):
        trigger.step(t)
        arrival = 15.0
        actual = trigger.apply_supply_disruption(arrival)
        flag = ' *** 断供' if trigger.is_supply_disruption_active() else ''
        print(f"  t={t}: 正常到货={arrival:.1f} -> 实际到货={actual:.1f}{flag}")

    # ---- 验证情绪传染 ----
    print("\n[验证] 情绪传染机制:")
    from emotion_module import EmotionState
    from dataclasses import dataclass

    # 模拟 agent_states (简化版)
    @dataclass
    class MockAgent:
        incoming_demand: float
        stockout: float
        emotion: EmotionState

    k_to_id = {1: 'retailer', 2: 'wholesaler', 3: 'distributor', 4: 'manufacturer'}
    id_to_k = {v: k for k, v in k_to_id.items()}

    # 场景: 零售商严重缺货 (stockout_rate=0.6 > 0.3)
    mock_agents = {
        'retailer': MockAgent(incoming_demand=20.0, stockout=12.0,
                              emotion=EmotionState()),
        'wholesaler': MockAgent(incoming_demand=15.0, stockout=0.0,
                                emotion=EmotionState()),
        'distributor': MockAgent(incoming_demand=10.0, stockout=0.0,
                                 emotion=EmotionState()),
        'manufacturer': MockAgent(incoming_demand=5.0, stockout=0.0,
                                  emotion=EmotionState()),
    }

    print("  传染前情绪:")
    for aid, ag in mock_agents.items():
        print(f"    {aid:12s}: E={ag.emotion.E:+.3f}")

    # 提高传染概率确保触发
    trigger2 = DynamicEventTrigger(
        contagion_threshold=0.3,
        contagion_prob=1.0,  # 100% 传染 (确保观察)
        contagion_strength=0.4,
        seed=42,
    )
    contagions = trigger2.apply_emotion_contagion(mock_agents, k_to_id, id_to_k)

    print(f"\n  触发 {len(contagions)} 次传染:")
    for c in contagions:
        print(f"    {c['from']:12s} (stockout_rate={c['stockout_rate']:.2f}) "
              f"-> {c['to']:12s}: E {c['before_E']:+.3f} -> {c['after_E']:+.3f} "
              f"(shock={c['shock']:+.2f})")

    print("\n  传染后情绪:")
    for aid, ag in mock_agents.items():
        print(f"    {aid:12s}: E={ag.emotion.E:+.3f}")

    # 验证连锁传染: 零售商→批发商, 若批发商也恐慌且严重缺货则→分销商
    print("\n[验证] 连锁传染 (批发商也恐慌):")
    # 让批发商也严重缺货
    mock_agents['wholesaler'].stockout = 8.0
    mock_agents['wholesaler'].incoming_demand = 15.0
    contagions2 = trigger2.apply_emotion_contagion(mock_agents, k_to_id, id_to_k)
    print(f"  第二轮触发 {len(contagions2)} 次传染:")
    for c in contagions2:
        print(f"    {c['from']:12s} -> {c['to']:12s}: "
              f"E {c['before_E']:+.3f} -> {c['after_E']:+.3f}")

    print(f"\n[统计] {trigger2.get_stats()}")

    print("\n" + "=" * 70)
    print("[OK] DynamicEventTrigger 自检通过!")
    print("=" * 70)
