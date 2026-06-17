from dataclasses import dataclass


@dataclass
class PostHFMethod:
    name: str
    name_cn: str
    pyscf_class: str
    description: str
    when_to_use: str
    cost_scaling: str
    accuracy: str
    notes: str = ""


POST_HF_METHODS: dict[str, PostHFMethod] = {}


def _add(m: PostHFMethod):
    POST_HF_METHODS[m.name] = m
    POST_HF_METHODS[m.name.lower()] = m


_add(PostHFMethod(
    name="MP2",
    name_cn="二阶 Moller-Plesset 微扰理论",
    pyscf_class="mp.MP2",
    description="最简单的后 HF 方法，包含二阶微扰相关能",
    when_to_use="中等精度相关计算、基准方法",
    cost_scaling="O(N^5)",
    accuracy="medium",
    notes="闭壳层 RMP2，开壳层 UMP2",
))

_add(PostHFMethod(
    name="SCS-MP2",
    name_cn="自旋分量标度 MP2",
    pyscf_class="mp.MP2",
    description="对 αα 和 ββ 相关分别标度的 MP2",
    when_to_use="比 MP2 更准确的相关计算",
    cost_scaling="O(N^5)",
    accuracy="medium",
    notes="需要手动设置标度系数",
))

_add(PostHFMethod(
    name="DF-MP2",
    name_cn="密度拟合 MP2",
    pyscf_class="df.mp.MP2",
    description="使用密度拟合加速的 MP2",
    when_to_use="大体系 MP2 计算",
    cost_scaling="O(N^4 ~ N^5)",
    accuracy="medium",
    notes="显著加速，适合大体系",
))

_add(PostHFMethod(
    name="CCSD",
    name_cn="耦合簇单双激发",
    pyscf_class="cc.CCSD",
    description="包含单激发和双激发的耦合簇方法",
    when_to_use="高精度能量计算",
    cost_scaling="O(N^6)",
    accuracy="high",
    notes="需要良好的 HF 参考波函数",
))

_add(PostHFMethod(
    name="CCSD(T)",
    name_cn="CCSD + 微扰三激发",
    pyscf_class="cc.CCSD",
    description="CCSD 加微扰三激发，'金标准'方法",
    when_to_use="最高精度单参考态方法",
    cost_scaling="O(N^7)",
    accuracy="very-high",
    notes="量子化学金标准，计算成本很高",
))

_add(PostHFMethod(
    name="DF-CCSD",
    name_cn="密度拟合 CCSD",
    pyscf_class="df.cc.CCSD",
    description="使用密度拟合加速的 CCSD",
    when_to_use="大体系 CCSD 计算",
    cost_scaling="O(N^5 ~ N^6)",
    accuracy="high",
    notes="显著加速",
))

_add(PostHFMethod(
    name="DF-CCSD(T)",
    name_cn="密度拟合 CCSD(T)",
    pyscf_class="df.cc.CCSD",
    description="使用密度拟合加速的 CCSD(T)",
    when_to_use="大体系 CCSD(T) 计算",
    cost_scaling="O(N^6 ~ N^7)",
    accuracy="very-high",
    notes="显著加速",
))

_add(PostHFMethod(
    name="UCCSD",
    name_cn="非限制性 CCSD",
    pyscf_class="cc.UCCSD",
    description="非限制性 CCSD，适用于开壳层体系",
    when_to_use="开壳层分子的高精度计算",
    cost_scaling="O(N^6)",
    accuracy="high",
))

_add(PostHFMethod(
    name="UCCSD(T)",
    name_cn="非限制性 CCSD(T)",
    pyscf_class="cc.UCCSD",
    description="非限制性 CCSD(T)",
    when_to_use="开壳层分子的最高精度计算",
    cost_scaling="O(N^7)",
    accuracy="very-high",
))

_add(PostHFMethod(
    name="ROHF-CCSD",
    name_cn="限制性开壳层 CCSD",
    pyscf_class="cc.CCSD",
    description="基于 ROHF 参考的 CCSD",
    when_to_use="避免自旋污染的开壳层 CCSD",
    cost_scaling="O(N^6)",
    accuracy="high",
))

_add(PostHFMethod(
    name="EOM-CCSD",
    name_cn="运动方程 CCSD",
    pyscf_class="cc.EOMCCSD",
    description="使用 EOM-CCSD 计算激发态",
    when_to_use="激发态能量、电离能、电子亲和能",
    cost_scaling="O(N^6)",
    accuracy="high",
    notes="可计算 IP/EA/EE",
))

_add(PostHFMethod(
    name="CISD",
    name_cn="组态相互作用单双激发",
    pyscf_class="ci.CISD",
    description="包含单双激发的 CI 方法",
    when_to_use="CI 基准计算",
    cost_scaling="O(N^6)",
    accuracy="medium",
    notes="不满足大小一致性",
))

_add(PostHFMethod(
    name="FCI",
    name_cn="全组态相互作用",
    pyscf_class="fci.FCI",
    description="精确解（在给定基组下）",
    when_to_use="小分子的精确基准计算",
    cost_scaling="指数增长",
    accuracy="exact",
    notes="仅适用于非常小的体系",
))


def get_post_hf_method(name: str) -> PostHFMethod:
    name_upper = name.upper()
    name_lower = name.lower()
    if name_upper in POST_HF_METHODS:
        return POST_HF_METHODS[name_upper]
    if name_lower in POST_HF_METHODS:
        return POST_HF_METHODS[name_lower]
    if "ccsd(t)" in name_lower or "ccsd-t" in name_lower:
        return POST_HF_METHODS["CCSD(T)"]
    raise KeyError(f"未找到后 HF 方法: {name}")


def list_post_hf_methods() -> list[PostHFMethod]:
    seen = set()
    result = []
    for m in POST_HF_METHODS.values():
        if m.name not in seen:
            seen.add(m.name)
            result.append(m)
    return sorted(result, key=lambda x: x.name)


def recommend_post_hf_method(accuracy: str = "medium", spin: int = 0) -> str:
    if accuracy == "very-high":
        return "CCSD(T)" if spin == 0 else "UCCSD(T)"
    elif accuracy == "high":
        return "CCSD" if spin == 0 else "UCCSD"
    else:
        return "MP2"
