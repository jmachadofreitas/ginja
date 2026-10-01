"""Report helpers: a presentation filter and a small data-preparation step."""


def percent(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f} %"


def setup(env):
    env.filters["percent"] = percent


def transform_data(context):
    metrics = context["data"]["metrics"]
    for service in metrics["services"]:
        service["meets_target"] = service["availability"] >= metrics["target"]
    metrics["missed"] = [service for service in metrics["services"] if not service["meets_target"]]
    return context
