from typing import List, Union, Dict, Any

def compute_overall_score(pipeline_risks: Union[List[float], Dict[str, float], Any]) -> float:
    if isinstance(pipeline_risks, dict):
        pipeline_risks = list(pipeline_risks.values())
    if not pipeline_risks:
        return 0.0
    if len(pipeline_risks) == 1:
        return float(pipeline_risks[0])
    return 0.7 * max(pipeline_risks) + 0.3 * (sum(pipeline_risks) / len(pipeline_risks))
