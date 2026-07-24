import networkx as nx


def load_graph(path):
    """خواندن گراف از فایل edge list با networkx"""
    graph = nx.read_edgelist(path, nodetype=int)
    # اگر گراف خالی بود یا فایل نبود، گراف karate را بساز
    if graph.number_of_nodes() == 0:
        graph = nx.karate_club_graph()
    return graph
