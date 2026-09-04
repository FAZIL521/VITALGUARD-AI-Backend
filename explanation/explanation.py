def human_explanation(result):
    reasons = result.get("reasons", [])
    if not reasons:
        return "No strong deviation or worsening trend was detected."
    names = {
        "hr_deviation": "heart rate is away from your personal baseline",
        "spo2_deviation": "SpO₂ is below your personal baseline",
        "temperature_deviation": "body temperature is above your personal baseline",
        "heat_humidity": "ambient heat/humidity is elevated",
        "worsening_trend": "recent measurements show a worsening trend",
    }
    phrases = [names.get(x["factor"], x["factor"]) for x in reasons[:3]]
    return "Risk increased because " + ", ".join(phrases) + "."
