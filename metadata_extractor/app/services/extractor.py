import json
from openai import OpenAI

from metadata_extractor.app.schemas import ExtractionRequest
from metadata_extractor.app.config import (
    OPENAI_API_KEY,
    ASKER_PROMPT,
    UPDATER_PROMPT,
    MODEL_FIELDS,
    LAYER_TYPES,
    OPENAI_LLM_MODEL,
)

client = OpenAI(api_key=OPENAI_API_KEY)

async def run_metadata_extractor(extraction_request: ExtractionRequest):
    model_fields = MODEL_FIELDS[extraction_request.model_type]
    model_fields['filled'] = False
    model_fields['follow_up_question'] = "null"

    allowed_layers = LAYER_TYPES[extraction_request.model_type]

    # filled = False
    last_msg = extraction_request.user_input or "null"
    cur_state = extraction_request.cur_state or "null"
    last_question = "null" if cur_state == "null" else cur_state.get("last_question", "null")

    # update step
    formatted_prompt = UPDATER_PROMPT.format(
        allowed_layers,
        json.dumps(model_fields, indent=2),
        json.dumps(cur_state, indent=2),
        last_question,
        last_msg
    )

    update_response = client.responses.create(
        model=OPENAI_LLM_MODEL,
        input=formatted_prompt
    )
    cur_state = json.loads(update_response.output_text)

    formatted_prompt = ASKER_PROMPT.format(
        json.dumps(model_fields, indent=2),
        json.dumps(cur_state, indent=2)
    )

    response = client.responses.create(
        model=OPENAI_LLM_MODEL,
        input=formatted_prompt
    )
    cur_state = json.loads(response.output_text)

    return {
        "metadata": cur_state
    }
