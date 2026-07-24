import json

from openai import OpenAI

import config


def _get_client():
    return OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url or None,
        timeout=config.llm_timeout,
    )


def _chat(prompt: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=config.llm_model,
        temperature=0.5,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def analyze_results(data: dict) -> str:
    """
    تحلیل و تفسیر نتایج community detection با LLM.
    data: خروجی /api/run (شامل num_nodes, num_edges, num_communities,
          modularity, partition, history, communities)
    """
    max_nodes = min(data["num_nodes"], 10)
    top_nodes = data["partition"][:max_nodes]

    communities = json.dumps(
        {k: v[:15] for k, v in list(data["communities"].items())[:6]},
        ensure_ascii=False,
    )

    prompt = f"""You are a network science expert. Analyze this community detection result and write a short report in Persian (Farsi).

Graph: {data['num_nodes']} nodes, {data['num_edges']} edges.
Detected communities: {data['num_communities']}
Modularity (Q): {data['modularity']:.4f}
Sample node->community (first {max_nodes} nodes): {top_nodes}

Per-community members: {communities}

Your report (in Persian, 4-7 paragraphs):
1. Overall assessment: Is this a good clustering? (Modularity above 0.3 is good)
2. Describe each community briefly: size, approximate role
3. Identify which community seems most central/dense
4. Any interesting patterns or suggestions for improvement

Write ONLY the report in Persian. No English, no markdown headings."""
    return _chat(prompt)


def suggest_parameters(num_nodes: int, num_edges: int) -> dict:
    """
    پیشنهاد population_size و iterations بهینه با توجه به مشخصات گراف.
    """
    density = (2 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0

    prompt = f"""You are an optimization expert. Suggest optimal GbSA parameters for a graph.

Graph: {num_nodes} nodes, {num_edges} edges, density={density:.4f}

Suggest population_size (2-100) and iterations (5-200) considering:
- Larger/sparser graphs need more exploration
- High density needs fine-tuning
- Small graphs need fewer resources

Answer EXACTLY in this JSON format (numbers only, no explanation):
{{"population_size": <int>, "iterations": <int>}}"""
    try:
        text = _chat(prompt)
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        if num_nodes < 50:
            return {"population_size": 10, "iterations": 30}
        elif num_nodes < 200:
            return {"population_size": 20, "iterations": 60}
        else:
            return {"population_size": 40, "iterations": 100}


def chat_qa(context: dict, question: str) -> str:
    """
    پرسش و پاسخ هوشمند درباره نتایج اجرا.
    context: همان data از /api/run
    """
    communities = json.dumps(
        {k: v[:20] for k, v in list(context["communities"].items())[:6]},
        ensure_ascii=False,
    )
    partition_sample = context["partition"][:min(context["num_nodes"], 15)]

    prompt = f"""You are an intelligent data science assistant embedded in a community detection dashboard.

Graph context:
- {context['num_nodes']} nodes, {context['num_edges']} edges
- {context['num_communities']} communities detected
- Modularity Q = {context['modularity']:.4f}
- Sample partition (node->community): {partition_sample}
- Community members: {communities}

User question: {question}

RULES:
- Answer in Persian (Farsi), 2-5 sentences.
- If the user asks about improving results, give SPECIFIC actionable suggestions (e.g., "جمعیت را به X افزایش دهید" or "تکرارها را به Y برسانید").
- If the user asks about modularity quality, compare to what is expected for this graph size.
- Be conversational and helpful — you are an assistant that knows the data.
- Never say you don't have enough context — use the numbers provided."""
    return _chat(prompt)
