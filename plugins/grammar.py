import json

import requests
from cloudbot import hook

MODEL = "vennify/t5-base-grammar-correction"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"


class HuggingFaceClient:
    def __init__(self, api_tokens: "list[str]"):
        self.api_tokens = iter(api_tokens)
        self.session = requests.Session()
        self.refresh_headers()

    def refresh_headers(self) -> None:
        self.session.headers.update({"Authorization": f"Bearer {self.next_token()}"})

    def next_token(self) -> str:
        return next(self.api_tokens)

    def _send(self, payload: dict) -> dict:
        data = json.dumps(payload)
        response = self.session.request("POST", API_URL, data=data)
        obj = json.loads(response.content.decode("utf-8"))
        return obj

    def send(self, text: str) -> dict:
        inputs = {"inputs": text}
        return self._send(inputs)


@hook.command("grammar")
def grammar(text, bot, reply):
    api_key = bot.config.get_api_key("huggingface")
    if not api_key:
        return "error: missing api key for huggingface"

    client = HuggingFaceClient([api_key])
    response = client.send(text)
    if "error" in response:
        return response["error"] + ". Maybe try again later?"

    generated_text = [r["generated_text"].strip() for r in response]
    if text.strip() in generated_text:
        return "✅ Perfect grammar! No changes needed."

    return ". ".join(generated_text)
