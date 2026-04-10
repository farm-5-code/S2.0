def calculate_confidence(probabilities, data_quality):
    ordered = sorted(probabilities.values(), reverse=True)
    spread = ordered[0] - ordered[1]
    confidence = (spread * 0.7 + data_quality * 0.3) * 100
    return round(max(30.0, min(95.0, confidence)), 2)
