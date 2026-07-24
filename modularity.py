import networkx as nx
from networkx.algorithms.community.quality import modularity


def calculate_modularity(graph, partition):
    """
    محاسبه Modularity (Q) برای یک partition.
    partition: لیستی به طول تعداد نودها؛ هر خانه = شماره community آن نود
    """
    # ساخت دیکشنری: community_id -> لیست نودها
    communities = {}
    nodes = list(graph.nodes())

    for i, node in enumerate(nodes):
        comm_id = partition[i]
        if comm_id not in communities:
            communities[comm_id] = []
        communities[comm_id].append(node)

    # لیست مجموعه‌های community برای تابع modularity
    community_sets = [set(members) for members in communities.values()]

    if len(community_sets) == 0:
        return 0.0

    q = modularity(graph, community_sets)
    return q
