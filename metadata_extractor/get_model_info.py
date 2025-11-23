import os
from dotenv import load_dotenv
from openai import OpenAI
import json
from pathlib import Path

load_dotenv()

metadata_extractor_root = Path("metadata_extractor")

METADATA_EXTRACTOR_ASKER_PROMPT_PATH = metadata_extractor_root / "metadata_extractor_asker.txt"
METADATA_EXTRACTOR_UPDATER_PROMPT_PATH = metadata_extractor_root / "metadata_extractor_updater.txt"
MODEL_FIELDS_PATH = metadata_extractor_root / "model_fields.json"
LAYER_TYPES_PATH = metadata_extractor_root / "layer_types.json"

OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPEN_AI_API_KEY is None:
    OPEN_AI_API_KEY = input("Enter your openai API key: ")

with open(METADATA_EXTRACTOR_ASKER_PROMPT_PATH) as f:
    asker_prompt = f.read()
with open(METADATA_EXTRACTOR_UPDATER_PROMPT_PATH) as f:
    updater_prompt = f.read()

with open(MODEL_FIELDS_PATH) as f:
    model_fields = json.loads(f.read())

layer_types = {}
with open(LAYER_TYPES_PATH) as f:
    layer_types["cnn"] = json.loads(f.read())

model_types = list(model_fields.keys())

# Choose model type
model_type = "cnn"

allowed_layers = layer_types[model_type]

model_fields = model_fields[model_type]
filled = False
follow_up_question = "some example question?"
model_fields["filled"] = filled
model_fields["follow_up_question"] = follow_up_question
last_msg = "null"
last_question = "null"
cur_state = None

client = OpenAI(api_key=OPEN_AI_API_KEY)
while not filled:
    formatted_prompt = asker_prompt.format(json.dumps(model_fields, indent=2),
                                     json.dumps(cur_state, indent=2))

    response = client.responses.create(
        model="o3-mini",
        input=formatted_prompt
    )

    cur_state = json.loads(response.output_text)
    follow_up_question = cur_state["follow_up_question"]
    filled = cur_state["filled"]
    del cur_state["filled"]
    del cur_state["follow_up_question"]

    if filled:
        break


    print(follow_up_question)
    lines = []
    while ((x := input()) != '-1'):
        lines.append(x)
    last_msg = '\n'.join(lines)


    formatted_prompt = updater_prompt.format(allowed_layers,
                                     json.dumps(model_fields, indent=2),
                                     json.dumps(cur_state, indent=2), last_question, last_msg)
    response = client.responses.create(
        model="o3-mini",
        input=formatted_prompt
    )
    cur_state = json.loads(response.output_text)
    del cur_state["filled"]
    del cur_state["follow_up_question"]

print(json.dumps(cur_state, indent=2))