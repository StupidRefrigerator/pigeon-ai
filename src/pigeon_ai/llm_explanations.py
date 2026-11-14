
import os
import json
import asyncio

from pydantic import BaseModel, Field

from agents import (
    Agent,
    Runner,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "model"
    / "candidate_evidence.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "model"
    / "llm_explanations.json"
)

# --------------------------------------------------
# 1. Structured output
# --------------------------------------------------

class HexExplanation(BaseModel):
    hex_id: str
    rank: int

    prediction_explanation: str = Field(
        description="Explain the main factors driving the model prediction."
    )

    recommendation_explanation: str = Field(
        description="Explain why the algorithm prioritised this location."
    )

    key_drivers: list[str]
    caveats: list[str]


class ExplanationBatch(BaseModel):
    explanations: list[HexExplanation]


# --------------------------------------------------
# 2. Configure model
# --------------------------------------------------

client = AsyncOpenAI(
    api_key=os.environ["COMP3110_API_KEY"],
    base_url=os.environ["COMP3110_MODEL_BASE_URL"],
)

model = OpenAIChatCompletionsModel(
    model=os.environ["COMP3110_MODEL"],
    openai_client=client,
)

# SCX is a third-party endpoint, so disable OpenAI tracing
# unless you have explicitly configured a suitable trace provider.
set_tracing_disabled(True)


# --------------------------------------------------
# 3. Define agent
# --------------------------------------------------

explanation_agent = Agent(
    name="Infrastructure Recommendation Explainer",

    model=model,

    instructions="""
    You are an infrastructure planning analyst.

    Your task is to explain existing public toilet
    infrastructure recommendations from a machine learning model.

    You receive structured data containing:
    - Recommendation rankings and priority scores
    - Predicted toilet demand
    - Existing toilet provision
    - Population and demographic context
    - SHAP feature contributions

    Rules:

    1. Never change rankings or recommendation scores.
    2. Explain predictions using the supplied SHAP drivers.
    3. Explain recommendation priority using the
       recommendation and contextual data.
    4. Never claim that a feature causes demand.
    5. SHAP contributions indicate model behaviour,
       not real-world causation.
    6. Do not invent missing information.
    7. Flag inconsistencies and potentially misleading
       information in the caveats.
    8. Treat SEIFA as socioeconomic context, not a
       direct measure of infrastructure demand.
    9. Distinguish predicted demand from actual demand.
    10. Write clear explanations understandable to
        a local council planner.

    Keep each explanation concise and evidence-based.
    """,

    output_type=ExplanationBatch,
)


# --------------------------------------------------
# 4. Run explanation
# --------------------------------------------------

async def explain_recommendations(recommendations):

    prompt = f"""
    Explain the following infrastructure recommendations.

    Return one explanation for every supplied hexagon.

    DATA:
    {json.dumps(recommendations, indent=2)}
    """

    result = await Runner.run(
        explanation_agent,
        prompt,
    )

    return result.final_output


# --------------------------------------------------
# 5. Save results
# --------------------------------------------------

async def main():

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        recommendations = json.load(f)

    # Support a single recommendation object as well
    # as a list of recommendation objects.
    if isinstance(recommendations, dict):
        recommendations = [recommendations]

    explanations = await explain_recommendations(
        recommendations
    )

    output = [
        explanation.model_dump()
        for explanation in explanations.explanations
    ]

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Generated {len(output)} explanations.")


if __name__ == "__main__":
    asyncio.run(main())
