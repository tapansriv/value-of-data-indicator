def compute_delta(t_opt, t_real):
    return (t_real - t_opt) / t_opt

"""Profile utility functions"""
def batch_utility(t_opt: float, t_real: float) -> float: 
    delta = compute_delta(t_opt, t_real)
    delta_free = 2.0
    delta_max = 10.0
    if delta <= delta_free:
        return 1.0
    if delta >= delta_max:
        return 0.0
    return 1.0 - (delta - delta_free) / (delta_max - delta_free)

def sla_utiliy(t_opt: float, t_real: float) -> float:
    delta = compute_delta(t_opt, t_real)
    delta_good = 0.25
    delta_bad = 1.0
    if delta <= delta_good:
        return 1.0
    if delta >= delta_bad:
        return 0.0
    return 1.0 - (delta - delta_good) / (delta_bad - delta_good)

def interactive_utility(t_opt: float, t_real: float) -> float:
    delta = compute_delta(t_opt, t_real)
    alpha = -1.5
    x = alpha * max(delta, 0.0)
    if x < -60:
        return 0.0
    return math.exp(x)

def real_time_utility(t_opt: float, t_real: float) -> float:
    delta = compute_delta(t_opt, t_real)
    delta_mid=0.15
    k=20.0
    max_exp = 60.0
    x = k * (delta - delta_mid)

    # Clamp exponent to avoid overflow
    if x > max_exp:
        return 0.0
    if x < -max_exp:
        return 1.0

    return 1.0 / (1.0 + math.exp(x))

def compute_utility(profile: str, t_opt: float, t_real: float) -> float:
    if profile == "batch":
        return batch_utility(t_opt, t_real)
    elif profile == "sla":
        return sla_utiliy(t_opt, t_real)
    elif profile == "interactive":
        return interactive_utility(t_opt, t_real)
    elif profile == "real_time":
        return real_time_utility(t_opt, t_real)
    else:
        raise ValueError(f"Unknown profile: {profile}")


""" Assign profiles to queries uniformally at random """
rng = np.random.default_rng(42)
profiles = ["batch", "sla", "interactive", "real_time"]
probs = [0.35, 0.25, 0.25, 0.15]
profile_assignment = rng.choice(profiles, size=len(query_keys),
                                replace=True, p=probs)


