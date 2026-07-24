import os
import matplotlib
matplotlib.use("Agg")  # بدون پنجره گرافیکی (فقط ذخیره فایل)
import matplotlib.pyplot as plt
import networkx as nx

import config
from graph_loader import load_graph
from modularity import calculate_modularity
from gbsa import GbSA


def main():
    # بارگذاری گراف
    path = config.dataset_path
    if os.path.exists(path):
        graph = load_graph(path)
        print(f"Graph loaded from: {path}")
    else:
        # اگر فایل نبود، از گراف معروف Zachary's Karate Club استفاده کن
        graph = nx.karate_club_graph()
        print("Dataset file not found. Using Karate Club Graph.")

    print(f"Nodes: {graph.number_of_nodes()}")
    print(f"Edges: {graph.number_of_edges()}")

    # اجرای GbSA
    algorithm = GbSA(
        graph=graph,
        population_size=config.population_size,
        iterations=config.iterations,
    )
    best_partition, history = algorithm.run()

    # محاسبه و پرینت نتیجه
    best_q = calculate_modularity(graph, best_partition)
    nodes = list(graph.nodes())

    print("\n========== Result ==========")
    print(f"Best Modularity (Q): {best_q:.4f}")
    print("Partition (node -> community):")
    for i, node in enumerate(nodes):
        print(f"  Node {node}: Community {best_partition[i]}")

    # رسم نمودار همگرایی Q
    plt.figure(figsize=(8, 5))
    plt.plot(history, marker="o", markersize=3)
    plt.xlabel("Iteration")
    plt.ylabel("Best Modularity (Q)")
    plt.title("GbSA Convergence - Community Detection")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("convergence.png")
    print("\nConvergence plot saved to convergence.png")
    plt.close()


if __name__ == "__main__":
    main()
