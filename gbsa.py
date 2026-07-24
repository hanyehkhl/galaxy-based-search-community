import random
import copy
from modularity import calculate_modularity


class GbSA:
    """Galaxy-based Search Algorithm برای Community Detection"""

    def __init__(self, graph, population_size, iterations):
        self.graph = graph
        self.population_size = population_size
        self.iterations = iterations
        self.nodes = list(graph.nodes())
        self.n = len(self.nodes)
        # جمعیت اولیه: هر star یک partition تصادفی است
        self.population = [self._random_partition() for _ in range(population_size)]

    def _random_partition(self):
        """ساخت یک partition تصادفی با تعداد کم community"""
        num_communities = random.randint(2, min(6, self.n))
        return [random.randint(0, num_communities - 1) for _ in range(self.n)]

    def _normalize(self, star):
        """شماره‌گذاری مجدد communityها از 0 تا k-1"""
        mapping = {}
        next_id = 0
        new_star = []
        for c in star:
            if c not in mapping:
                mapping[c] = next_id
                next_id += 1
            new_star.append(mapping[c])
        return new_star

    def spiral_chaotic_move(self, star):
        """
        اکتشاف: ساخت partition جدید با تغییرات تصادفی (حرکت مارپیچی/آشوبناک).
        چند نود را به community تصادفی دیگر منتقل می‌کند.
        """
        new_star = copy.deepcopy(star)
        num_changes = random.randint(1, max(1, self.n // 5))
        current_comms = list(set(new_star))

        for _ in range(num_changes):
            idx = random.randint(0, self.n - 1)
            if random.random() < 0.7 and len(current_comms) > 0:
                # جابه‌جایی به یک community موجود
                new_star[idx] = random.choice(current_comms)
            else:
                # ایجاد community جدید (با احتمال کم)
                new_star[idx] = max(current_comms) + 1 if current_comms else 0
                current_comms = list(set(new_star))

        return self._normalize(new_star)

    def local_search(self, star):
        """
        جستجوی محلی: جابه‌جایی یک نود بین دو community برای بهبود Q.
        برای چند نود تصادفی، همه communityهای موجود را امتحان می‌کند.
        """
        best = self._normalize(copy.deepcopy(star))
        best_q = calculate_modularity(self.graph, best)

        # چند نود تصادفی را بهبود بده
        indices = list(range(self.n))
        random.shuffle(indices)
        indices = indices[: max(5, self.n // 3)]

        for idx in indices:
            current_comms = list(set(best))
            improved = False

            for comm in current_comms:
                if comm == best[idx]:
                    continue
                candidate = copy.deepcopy(best)
                candidate[idx] = comm
                candidate = self._normalize(candidate)
                q = calculate_modularity(self.graph, candidate)
                if q > best_q:
                    best = candidate
                    best_q = q
                    improved = True

            # گاهی امتحان community کاملاً جدید
            if not improved and random.random() < 0.2:
                candidate = copy.deepcopy(best)
                candidate[idx] = max(best) + 1
                candidate = self._normalize(candidate)
                q = calculate_modularity(self.graph, candidate)
                if q > best_q:
                    best = candidate
                    best_q = q

        return best

    def run(self):
        """اجرای کامل الگوریتم GbSA"""
        history = []  # تاریخچه بهترین Q در هر iteration

        # ارزیابی جمعیت اولیه
        best_partition = None
        best_q = -1.0
        fitness = []

        for star in self.population:
            star = self._normalize(star)
            q = calculate_modularity(self.graph, star)
            fitness.append(q)
            if q > best_q:
                best_q = q
                best_partition = copy.deepcopy(star)

        history.append(best_q)

        for it in range(self.iterations):
            new_population = []
            new_fitness = []

            for i, star in enumerate(self.population):
                # 1. حرکت مارپیچی/آشوبناک (اکتشاف)
                moved = self.spiral_chaotic_move(star)
                # 2. جستجوی محلی (بهره‌برداری)
                improved = self.local_search(moved)
                q = calculate_modularity(self.graph, improved)

                # اگر بهتر از star قبلی بود، جایگزین کن؛ وگرنه star قبلی بماند
                if q >= fitness[i]:
                    new_population.append(improved)
                    new_fitness.append(q)
                else:
                    new_population.append(star)
                    new_fitness.append(fitness[i])

                if q > best_q:
                    best_q = q
                    best_partition = copy.deepcopy(improved)

            # نگه داشتن بهترین star در جمعیت (elitism)
            worst_idx = new_fitness.index(min(new_fitness))
            new_population[worst_idx] = copy.deepcopy(best_partition)
            new_fitness[worst_idx] = best_q

            self.population = new_population
            fitness = new_fitness
            history.append(best_q)
            print(f"Iteration {it + 1}/{self.iterations} | Best Q = {best_q:.4f}")

        return best_partition, history
