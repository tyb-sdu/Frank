"""Knowledge base — Aitomia-inspired RAG-lite for computational chemistry Q&A."""

import re
from dataclasses import dataclass
from typing import Optional

from ..methods.dft import list_dft_functionals
from ..methods.post_hf import list_post_hf_methods
from ..methods.solvation import list_solvation_models
from ..basis import list_basis_sets
from ..config import get_api_key


@dataclass
class KnowledgeChunk:
    topic: str
    title: str
    content: str
    keywords: list[str]
    category: str  # method | basis | workflow | concept | frank


def _build_knowledge_base() -> list[KnowledgeChunk]:
    """Build knowledge chunks from Frank's built-in databases."""
    chunks = []

    # Frank overview
    chunks.append(KnowledgeChunk(
        topic="frank_overview",
        title="Frank 智能体概述",
        content=(
            "Frank 是一个计算化学终端智能体，灵感来自 Aitomia 多智能体架构。"
            "核心能力：自然语言意图解析 → PySCF 代码生成（模板驱动，非 LLM 生成代码）→ "
            "自动执行 → 错误诊断与自校正 → 结果解读。"
            "支持单步计算（能量、优化、频率、TDDFT、CASSCF）和多步工作流"
            "（反应热力学、互变异构比较、方法对比、基组收敛、势能面扫描、溶剂化）。"
            "使用 'plan <query>' 让智能体自动规划复杂工作流，'explain <question>' 查询方法知识。"
        ),
        keywords=["frank", "aitomia", "智能体", "overview", "概述", "what is frank"],
        category="frank",
    ))

    # Aitomia architecture concept
    chunks.append(KnowledgeChunk(
        topic="aitomia_architecture",
        title="Aitomia 多智能体架构",
        content=(
            "Aitomia 采用 LangGraph 多智能体架构：编排智能体（Orchestrator）分析用户意图，"
            "设计工作流并调度单任务智能体（结构检索、几何优化、频率、光谱等）。"
            "Frank 借鉴此设计：WorkflowPlanner 规划工作流，OrchestratorEngine 执行，"
            "SelfCorrectionEngine 在检测到虚频时自动重新优化。"
            "关键原则：代码由预定义模板生成（非 LLM 直接写代码），确保计算稳定性。"
        ),
        keywords=["aitomia", "multi-agent", "多智能体", "langgraph", "orchestrator", "架构"],
        category="concept",
    ))

    # Deterministic stoichiometry (Aitomia)
    chunks.append(KnowledgeChunk(
        topic="deterministic_stoichiometry",
        title="确定性化学计量与单位换算",
        content=(
            "借鉴 Aitomia：反应化学计量系数不由 LLM 推断，而是从各物种的原子组成"
            "构建原子守恒矩阵，用 scipy.linalg.null_space 数学求解。"
            "相对能量（ΔE、ΔH、ΔG）由计算引擎预先换算为 Hartree 和 kcal/mol 双单位输出，"
            "避免 LLM 做单位算术。绝对单点能仅报告 Hartree。"
        ),
        keywords=["stoichiometry", "化学计量", "null space", "原子守恒", "单位换算", "kcal"],
        category="concept",
    ))

    # Structure validation
    chunks.append(KnowledgeChunk(
        topic="structure_validation",
        title="分子结构验证与检索",
        content=(
            "结构检索流程（Aitomia 风格）：PubChem 3D 构象 → NIH Cactus SMILES 解析 → "
            "RDKit ETKDG 嵌入 + MMFF94 优化。检索后验证原子数与分子式是否一致，"
            "若有 SMILES 则进行 RDKit 分子图一致性检查。"
        ),
        keywords=["pubchem", "cactus", "结构验证", "structure validation", "rdkit", "检索"],
        category="concept",
    ))

    # Error diagnosis
    chunks.append(KnowledgeChunk(
        topic="error_diagnosis",
        title="错误诊断模块",
        content=(
            "计算失败时，Frank 聚合 stderr/stdout 及工作目录中的 .log/.err/.out 文件，"
            "结合规则分类与 LLM 分析（Aitomia error analysis），给出可能原因和修正建议。"
        ),
        keywords=["error diagnosis", "错误诊断", "traceback", "失败分析"],
        category="concept",
    ))

    # Self-correction
    chunks.append(KnowledgeChunk(
        topic="self_correction",
        title="自校正机制",
        content=(
            "Aitomia 和 Frank 均实现了自校正：频率计算检测到虚频时，"
            "自动触发重新几何优化（收紧收敛标准），最多重试 2 次。"
            "小虚频（< 50 cm⁻¹）视为数值噪声可忽略。"
            "1 个大虚频可能表示过渡态；多个虚频表示结构不是极小值点。"
        ),
        keywords=["self-correction", "自校正", "虚频", "imaginary frequency", "re-optimize"],
        category="concept",
    ))

    # DFT functionals
    for func in list_dft_functionals():
        chunks.append(KnowledgeChunk(
            topic=f"dft_{func.name.lower()}",
            title=f"DFT 泛函: {func.name} ({func.name_cn})",
            content=(
                f"{func.description}。"
                f"类别: {func.category}。精度: {func.accuracy}。"
                f"适用场景: {func.when_to_use}。"
                + (f" 备注: {func.notes}" if func.notes else "")
            ),
            keywords=[func.name.lower()] + func.aliases + [func.name_cn, "dft", "泛函", "functional"],
            category="method",
        ))

    # Post-HF methods
    for method in list_post_hf_methods():
        chunks.append(KnowledgeChunk(
            topic=f"posthf_{method.name.lower()}",
            title=f"后 HF 方法: {method.name}",
            content=(
                f"{method.description}。"
                f"精度: {method.accuracy}。适用: {method.when_to_use}。"
                f"计算成本: {method.cost_scaling}。"
            ),
            keywords=[method.name.lower(), method.name_cn, "post-hf", "后hf", "mp2", "ccsd"],
            category="method",
        ))

    # Basis sets
    for bs in list_basis_sets():
        chunks.append(KnowledgeChunk(
            topic=f"basis_{bs.name}",
            title=f"基组: {bs.name}",
            content=(
                f"{bs.description}。"
                f"级别: {bs.level}。类别: {bs.category}。"
                + (f" 备注: {bs.notes}" if bs.notes else "")
            ),
            keywords=[bs.name, bs.category, "基组", "basis"],
            category="basis",
        ))

    # Method selection guide
    chunks.append(KnowledgeChunk(
        topic="method_selection",
        title="计算方法选择指南",
        content=(
            "快速筛选/大体系: HF/STO-3G 或 GFN-xTB（Frank 暂不支持 xTB）。"
            "有机分子常规计算: B3LYP/6-31G* 或 B3LYP/def2-SVP。"
            "高精度能量: CCSD(T)/cc-pVTZ 或 MP2/cc-pVDZ。"
            "激发态/光谱: TDDFT/CAM-B3LYP 或 wB97X-D/aug-cc-pVDZ（需弥散函数）。"
            "非共价相互作用: wB97X-D 或 M06-2X + 弥散基组。"
            "多参考体系（键断裂）: CASSCF/cc-pVDZ。"
            "溶剂效应: SMD 或 PCM 隐式溶剂模型。"
        ),
        keywords=["方法选择", "method selection", "推荐", "recommend", "哪个方法", "用什么方法"],
        category="concept",
    ))

    # Workflows
    workflow_docs = [
        ("opt_freq", "几何优化+频率", "优化结构后计算振动频率，验证是否为极小值点，可选高精度单点能。"),
        ("reaction_thermo", "反应热力学", "对各反应物和产物分别 opt→freq，计算 ΔE、ΔH、ΔG。"),
        ("tautomer", "互变异构比较", "对各互变异构体 opt→freq，比较相对自由能。"),
        ("method_comparison", "方法对比", "同一分子用多种方法（HF/B3LYP/MP2）计算单点能并比较。"),
        ("basis_convergence", "基组收敛", "逐步增大基组，检验能量收敛性。"),
        ("pes_scan", "势能面扫描", "沿键长/键角/二面角扫描势能面。"),
        ("solvation", "溶剂化自由能", "气相优化+频率 → 液相单点，估算 ΔG_solv。"),
        ("conformer", "构象搜索", "RDKit ETKDG 枚举构象 → MMFF 排序 → 对最低几个构象 opt→freq。"),
    ]
    for wf_id, title, desc in workflow_docs:
        chunks.append(KnowledgeChunk(
            topic=f"workflow_{wf_id}",
            title=f"工作流: {title}",
            content=desc,
            keywords=[wf_id, title, "工作流", "workflow"],
            category="workflow",
        ))

    # Solvation
    for model in list_solvation_models():
        chunks.append(KnowledgeChunk(
            topic=f"solvation_{model.name.lower()}",
            title=f"溶剂化模型: {model.name}",
            content=f"{model.description}。适用: {model.when_to_use}。",
            keywords=[model.name.lower(), "溶剂化", "solvation", "pcm", "smd"],
            category="method",
        ))

    return chunks


_KNOWLEDGE_BASE: list[KnowledgeChunk] = []


def get_knowledge_base() -> list[KnowledgeChunk]:
    global _KNOWLEDGE_BASE
    if not _KNOWLEDGE_BASE:
        _KNOWLEDGE_BASE = _build_knowledge_base()
    return _KNOWLEDGE_BASE


class KnowledgeRetriever:
    """Adaptive-RAG-lite: keyword scoring with optional LLM synthesis."""

    DIRECT_ANSWER_THRESHOLD = 3.0  # high score → direct answer without LLM
    COMPLEX_QUERY_THRESHOLD = 1.5  # below → try multi-step retrieval

    def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        query_lower = query.lower()
        query_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", query_lower))

        scored = []
        for chunk in get_knowledge_base():
            score = 0.0
            for kw in chunk.keywords:
                if kw.lower() in query_lower:
                    score += 2.0
            for token in query_tokens:
                if token in chunk.content.lower():
                    score += 0.5
                if token in chunk.title.lower():
                    score += 1.0
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:top_k]]

    def explain(self, question: str) -> str:
        """Answer a computational chemistry question using knowledge base + optional LLM."""
        chunks = self.retrieve(question, top_k=5)

        if not chunks:
            return (
                "未找到相关知识。请尝试更具体的问题，例如：\n"
                "  - B3LYP 和 MP2 有什么区别？\n"
                "  - 什么时候需要 aug-cc-pVDZ？\n"
                "  - Frank 支持哪些工作流？"
            )

        top_score = self._score_chunk(question, chunks[0])

        # Adaptive-RAG: multi-step retrieval for complex queries
        if top_score < self.COMPLEX_QUERY_THRESHOLD and len(chunks) < 3:
            refined = self._refine_query(question)
            if refined != question:
                extra = self.retrieve(refined, top_k=3)
                seen = {c.topic for c in chunks}
                for c in extra:
                    if c.topic not in seen:
                        chunks.append(c)
                        seen.add(c.topic)

        top_score = self._score_chunk(question, chunks[0]) if chunks else 0

        # Adaptive: direct answer for simple queries
        if top_score >= self.DIRECT_ANSWER_THRESHOLD or len(chunks) == 1:
            return self._format_direct_answer(question, chunks)

        # Complex query: try LLM synthesis
        llm_answer = self._synthesize_with_llm(question, chunks)
        if llm_answer:
            return llm_answer

        return self._format_direct_answer(question, chunks)

    def _score_chunk(self, query: str, chunk: KnowledgeChunk) -> float:
        query_lower = query.lower()
        score = 0.0
        for kw in chunk.keywords:
            if kw.lower() in query_lower:
                score += 2.0
        return score

    def _refine_query(self, question: str) -> str:
        """Generate a refined query for multi-step Adaptive-RAG retrieval."""
        if not get_api_key():
            return question
        try:
            from openai import OpenAI
            from ..llm import get_base_url, get_model_name

            client = OpenAI(api_key=get_api_key(), base_url=get_base_url())
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Rewrite the user's computational chemistry question into a "
                            "more specific search query (one sentence). Output only the query."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.2,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip() or question
        except Exception:
            return question

    def _format_direct_answer(self, question: str, chunks: list[KnowledgeChunk]) -> str:
        lines = [f"问题: {question}\n"]
        for chunk in chunks[:3]:
            lines.append(f"## {chunk.title}")
            lines.append(chunk.content)
            lines.append("")
        if len(chunks) > 3:
            lines.append(f"（另有 {len(chunks)-3} 条相关知识未显示）")
        return "\n".join(lines)

    def _synthesize_with_llm(self, question: str, chunks: list[KnowledgeChunk]) -> Optional[str]:
        if not get_api_key():
            return None
        try:
            from openai import OpenAI
            from ..llm import get_base_url, get_model_name

            context = "\n\n".join(
                f"[{c.title}]\n{c.content}" for c in chunks
            )
            client = OpenAI(api_key=get_api_key(), base_url=get_base_url())
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Frank, a computational chemistry expert assistant. "
                            "Answer the user's question based ONLY on the provided knowledge. "
                            "If the knowledge is insufficient, say so. "
                            "Use the same language as the user. Be concise (3-8 sentences). "
                            "Do not use emoji."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Knowledge:\n{context}\n\nQuestion: {question}",
                    },
                ],
                temperature=0.3,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return None
