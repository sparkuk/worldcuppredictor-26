def calculate_points(predicted_home: int, predicted_away: int, actual_home: int, actual_away: int) -> int:
    """
    Calculate points based on:
    - 1 point for correctly predicting the winner/draw (outcome)
    - 1 point for getting exactly one team's score correct
    - 3 points (1 + 2 bonus) for getting both teams' scores correct.
    """
    points = 0
    
    # 1. Correct outcome
    actual_diff = actual_home - actual_away
    pred_diff = predicted_home - predicted_away
    
    correct_outcome = False
    if actual_diff > 0 and pred_diff > 0:
        correct_outcome = True
    elif actual_diff < 0 and pred_diff < 0:
        correct_outcome = True
    elif actual_diff == 0 and pred_diff == 0:
        correct_outcome = True
        
    if correct_outcome:
        points += 1
        
    # 2. Score accuracy
    home_correct = (predicted_home == actual_home)
    away_correct = (predicted_away == actual_away)
    
    if home_correct or away_correct:
        points += 1
        
    if home_correct and away_correct:
        points += 2
        
    return points
