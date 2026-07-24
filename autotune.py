"""
حلقه خودتنظیم دو عاملی (Executor + Critic) برای GbSA.

Executor: اجرای GbSA با پارامترهای فعلی
Critic: ارزیابی نتیجه و پیشنهاد پارامتر جدید (LLM + قواعد پشتیبان)
"""

import json
import copy

from gbsa import GbSA
from modularity import calculate_modularity
from llm import _chat


# محدوده‌های امن پارامتر
MIN_POP, MAX_POP = 2, 100
MIN_ITER, MAX_ITER = 5, 200


def _clamp_params(population_size: int, iterations: int) -> tuple[int, int]:
    pop = max(MIN_POP, min(MAX_POP, int(population_size)))
    it = max(MIN_ITER, min(MAX_ITER, int(iterations)))
    return pop, it


def _history_trend(history: list) -> dict:
    """خلاصه روند همگرایی Q در یک اجرا."""
    if not history:
        return {"start_q": 0.0, "end_q": 0.0, "gain": 0.0, "stagnant_tail": True}

    start_q = float(history[0])
    end_q = float(history[-1])
    gain = end_q - start_q

    # آیا در یک‌سوم پایانی بهبود محسوس نبود؟
    tail = history[max(0, len(history) * 2 // 3) :]
    stagnant_tail = True
    if len(tail) >= 2:
        stagnant_tail = (max(tail) - min(tail)) < 0.005

    return {
        "start_q": start_q,
        "end_q": end_q,
        "gain": gain,
        "stagnant_tail": stagnant_tail,
    }


def executor_agent(graph, population_size: int, iterations: int) -> dict:
    """
    عامل اجراکننده: GbSA را با پارامترهای داده‌شده اجرا می‌کند.

    Returns:
        {
          population_size, iterations,
          modularity, num_communities, partition, history, trend
        }
    """
    pop, it = _clamp_params(population_size, iterations)
    algo = GbSA(graph=graph, population_size=pop, iterations=it)
    partition, history = algo.run()
    q = calculate_modularity(graph, partition)
    num_comms = len(set(partition)) if partition else 0
    trend = _history_trend(history)

    return {
        "population_size": pop,
        "iterations": it,
        "modularity": float(q),
        "num_communities": num_comms,
        "partition": partition,
        "history": history,
        "trend": trend,
    }


def _rule_based_critic(
    attempt: dict,
    prev_attempt: dict | None,
    num_nodes: int,
    threshold: float,
) -> dict:
    """
    تصمیم‌گیری قاعده‌ای (fallback اگر LLM در دسترس نباشد).

    معیارهای «کافی بودن»:
      1. Q >= threshold
      2. Q خیلی خوب برای اندازه گراف (مثلاً > 0.5 برای گراف کوچک)
      3. دو تلاش پشت‌سرهم بدون بهبود (>= 0.005)

    پیشنهاد پارامتر:
      - اگر Q پایین و stagnant_tail → افزایش iterations
      - اگر Q متوسط و gain کم → افزایش population
      - اگر Q خوب ولی زیر threshold → هر دو کمی افزایش
      - اگر communities خیلی زیاد/کم نسبت به n → تنظیم exploration (pop)
    """
    q = attempt["modularity"]
    trend = attempt["trend"]
    pop = attempt["population_size"]
    it = attempt["iterations"]
    n_comm = attempt["num_communities"]

    # --- توقف: کافی است ---
    if q >= threshold:
        return {
            "good_enough": True,
            "reason": f"Q={q:.4f} به آستانه {threshold} رسیده یا از آن گذشته است.",
            "population_size": pop,
            "iterations": it,
        }

    # --- توقف: بدون بهبود در دو تلاش متوالی ---
    if prev_attempt is not None:
        delta = q - prev_attempt["modularity"]
        if abs(delta) < 0.005:
            return {
                "good_enough": True,
                "reason": f"در دو تلاش متوالی بهبود محسوس نبود (ΔQ={delta:.4f}).",
                "population_size": pop,
                "iterations": it,
            }

    # --- پیشنهاد پارامتر جدید ---
    new_pop, new_it = pop, it
    reasons = []

    if q < 0.2:
        # خیلی ضعیف → اکتشاف بیشتر
        new_pop = min(MAX_POP, int(pop * 1.5) + 5)
        new_it = min(MAX_ITER, int(it * 1.5) + 10)
        reasons.append("Q خیلی پایین است؛ جمعیت و تکرارها افزایش یافت.")
    elif trend["stagnant_tail"] and trend["gain"] < 0.05:
        # گیر کرده در انتها → iterations بیشتر
        new_it = min(MAX_ITER, it + max(10, it // 3))
        reasons.append("همگرایی در انتهای اجرا متوقف شده؛ iterations افزایش یافت.")
    elif trend["gain"] < 0.03:
        # بهبود کم از ابتدا → population بیشتر
        new_pop = min(MAX_POP, pop + max(5, pop // 4))
        reasons.append("بهبود کلی کم است؛ population_size افزایش یافت.")
    else:
        # پیشرفت هست ولی هنوز زیر threshold
        new_pop = min(MAX_POP, pop + 5)
        new_it = min(MAX_ITER, it + 10)
        reasons.append("نتیجه رو به بهبود است؛ هر دو پارامتر کمی افزایش یافت.")

    # تنظیم بر اساس تعداد community
    if num_nodes > 0:
        if n_comm > num_nodes // 2:
            new_pop = min(MAX_POP, new_pop + 5)
            reasons.append("تعداد community زیاد است؛ اکتشاف بیشتر.")
        elif n_comm < 2 and num_nodes > 10:
            new_it = min(MAX_ITER, new_it + 15)
            reasons.append("تعداد community کم است؛ iterations بیشتر.")

    new_pop, new_it = _clamp_params(new_pop, new_it)

    # اگر پارامترها عوض نشدند، اجباری کمی تغییر بده
    if new_pop == pop and new_it == it:
        new_it = min(MAX_ITER, it + 10)
        reasons.append("پارامترها یکسان بودند؛ iterations به‌اجبار افزایش یافت.")

    return {
        "good_enough": False,
        "reason": " ".join(reasons),
        "population_size": new_pop,
        "iterations": new_it,
    }


def critic_agent(
    attempt: dict,
    prev_attempt: dict | None,
    num_nodes: int,
    num_edges: int,
    threshold: float,
    attempt_index: int,
    max_attempts: int,
) -> dict:
    """
    عامل منتقد: تصمیم می‌گیرد نتیجه کافی است یا پارامتر جدید پیشنهاد می‌دهد.

    Returns:
        {
          good_enough: bool,
          reason: str,
          population_size: int,   # برای تلاش بعدی (یا همان فعلی اگر تمام)
          iterations: int,
        }
    """
    # اگر LLM خاموش/خطا → قاعده‌ای
    try:
        prev_q = prev_attempt["modularity"] if prev_attempt else None
        prompt = f"""You are a critic agent for GbSA community detection parameter tuning.

Graph: {num_nodes} nodes, {num_edges} edges.
Attempt {attempt_index}/{max_attempts}
Current params: population_size={attempt['population_size']}, iterations={attempt['iterations']}
Result: Q={attempt['modularity']:.4f}, communities={attempt['num_communities']}
Trend: start={attempt['trend']['start_q']:.4f}, end={attempt['trend']['end_q']:.4f}, gain={attempt['trend']['gain']:.4f}, stagnant_tail={attempt['trend']['stagnant_tail']}
Previous attempt Q: {prev_q}
Target threshold Q: {threshold}

Decide:
1. good_enough=true if Q >= threshold OR no meaningful improvement vs previous (|ΔQ|<0.005)
2. Otherwise propose NEW population_size (2-100) and iterations (5-200).
   Rules of thumb:
   - Low Q + stagnant tail → increase iterations
   - Low gain overall → increase population_size
   - Too many communities → more exploration (population)
   - Too few communities → more iterations
   - Do not decrease both params at once if Q is still low

Answer EXACTLY this JSON (no markdown):
{{"good_enough": true/false, "reason": "short English reason", "population_size": <int>, "iterations": <int>}}"""

        text = _chat(prompt)
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)

        good = bool(data.get("good_enough", False))
        # اجبار منطق محلی: threshold و plateau
        if attempt["modularity"] >= threshold:
            good = True
        if prev_attempt is not None and abs(attempt["modularity"] - prev_attempt["modularity"]) < 0.005:
            good = True

        pop, it = _clamp_params(
            data.get("population_size", attempt["population_size"]),
            data.get("iterations", attempt["iterations"]),
        )
        reason = str(data.get("reason", "critic decision"))

        return {
            "good_enough": good,
            "reason": reason,
            "population_size": pop,
            "iterations": it,
        }
    except Exception:
        return _rule_based_critic(attempt, prev_attempt, num_nodes, threshold)


def explain_final(
    attempts: list[dict],
    best: dict,
    stop_reason: str,
    num_nodes: int,
    num_edges: int,
    threshold: float,
) -> str:
    """توضیح فارسی: چرا پارامترهای نهایی انتخاب شدند."""
    summary = []
    for i, a in enumerate(attempts, 1):
        summary.append(
            f"تلاش {i}: pop={a['population_size']}, iter={a['iterations']}, "
            f"Q={a['modularity']:.4f}, comms={a['num_communities']}"
        )
    summary_text = "\n".join(summary)

    prompt = f"""You explain GbSA auto-tuning results in Persian (Farsi).

Graph: {num_nodes} nodes, {num_edges} edges. Threshold Q={threshold}.
Stop reason: {stop_reason}

Attempts:
{summary_text}

Best: pop={best['population_size']}, iter={best['iterations']}, Q={best['modularity']:.4f}, communities={best['num_communities']}

Write 3-6 sentences in Persian only:
- Why these final parameters were chosen
- How Q improved across attempts (or why it plateaued)
- Brief advice if user wants to try again
No markdown headings. Persian only."""

    try:
        return _chat(prompt)
    except Exception:
        return (
            f"حلقه خودتنظیم پس از {len(attempts)} تلاش متوقف شد ({stop_reason}). "
            f"بهترین پارامترها: population_size={best['population_size']} و "
            f"iterations={best['iterations']} با Q={best['modularity']:.4f} "
            f"و {best['num_communities']} اجتماع. "
            f"آستانه هدف Q={threshold} بود."
        )


def run_autotune(
    graph,
    population_size: int = 20,
    iterations: int = 50,
    max_attempts: int = 3,
    threshold: float = 0.4,
) -> dict:
    """
    حلقه اصلی Executor ↔ Critic.

    توقف وقتی:
      - Q >= threshold
      - تعداد تلاش‌ها به max_attempts برسد
      - دو تلاش متوالی بدون بهبود محسوس

    Returns:
        {
          best_partition, best_modularity, best_params,
          num_communities, history (best run),
          attempts: [{attempt, params, Q, num_communities, critic_reason, ...}],
          stop_reason, explanation_fa,
          num_nodes, num_edges
        }
    """
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    pop, it = _clamp_params(population_size, iterations)
    max_attempts = max(1, min(10, int(max_attempts)))
    threshold = float(threshold)

    attempts_log = []
    best = None
    prev = None
    stop_reason = "max_attempts"

    for i in range(1, max_attempts + 1):
        # --- Executor ---
        result = executor_agent(graph, pop, it)

        # --- Critic ---
        decision = critic_agent(
            attempt=result,
            prev_attempt=prev,
            num_nodes=num_nodes,
            num_edges=num_edges,
            threshold=threshold,
            attempt_index=i,
            max_attempts=max_attempts,
        )

        entry = {
            "attempt": i,
            "population_size": result["population_size"],
            "iterations": result["iterations"],
            "modularity": result["modularity"],
            "num_communities": result["num_communities"],
            "history": result["history"],
            "trend": result["trend"],
            "critic_good_enough": decision["good_enough"],
            "critic_reason": decision["reason"],
            "proposed_population_size": decision["population_size"],
            "proposed_iterations": decision["iterations"],
        }
        attempts_log.append(entry)

        # به‌روزرسانی بهترین
        if best is None or result["modularity"] > best["modularity"]:
            best = copy.deepcopy(result)

        # شرط توقف
        if result["modularity"] >= threshold:
            stop_reason = "threshold_reached"
            break

        if prev is not None and abs(result["modularity"] - prev["modularity"]) < 0.005:
            stop_reason = "no_improvement"
            break

        if decision["good_enough"]:
            stop_reason = "critic_satisfied"
            break

        if i == max_attempts:
            stop_reason = "max_attempts"
            break

        # پارامترهای تلاش بعدی
        pop = decision["population_size"]
        it = decision["iterations"]
        prev = result

    explanation = explain_final(
        attempts=attempts_log,
        best=best,
        stop_reason=stop_reason,
        num_nodes=num_nodes,
        num_edges=num_edges,
        threshold=threshold,
    )

    return {
        "best_partition": best["partition"],
        "best_modularity": best["modularity"],
        "best_params": {
            "population_size": best["population_size"],
            "iterations": best["iterations"],
        },
        "num_communities": best["num_communities"],
        "history": best["history"],
        "attempts": [
            {
                "attempt": a["attempt"],
                "population_size": a["population_size"],
                "iterations": a["iterations"],
                "modularity": a["modularity"],
                "num_communities": a["num_communities"],
                "critic_reason": a["critic_reason"],
                "critic_good_enough": a["critic_good_enough"],
                "proposed_population_size": a["proposed_population_size"],
                "proposed_iterations": a["proposed_iterations"],
            }
            for a in attempts_log
        ],
        "stop_reason": stop_reason,
        "explanation_fa": explanation,
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "threshold": threshold,
        "max_attempts": max_attempts,
    }
