import json
import re
from time import sleep

import requests

from cloudbot import hook

LANG_MODEL_MAP = {
    "en": "vennify/t5-base-grammar-correction",
    "de": "MRNH/mbart-german-grammar-corrector",
}
API_URL = "https://api-inference.huggingface.co/models/{model}"


class HuggingFaceClient:
    def __init__(self, api_tokens: "list[str]"):
        self.api_tokens = iter(api_tokens)
        self.session = requests.Session()
        self.refresh_headers()

    def refresh_headers(self) -> None:
        self.session.headers.update(
            {"Authorization": f"Bearer {self.next_token()}"}
        )

    def next_token(self) -> str:
        return next(self.api_tokens)

    def _send(self, payload: dict, model: str) -> dict:
        data = json.dumps(payload)
        response = self.session.request(
            "POST", API_URL.format(model=model), data=data
        )
        obj = json.loads(response.content.decode("utf-8"))
        return obj

    def send(self, text: str, model: str) -> dict:
        inputs = {"inputs": text}
        return self._send(inputs, model)


def grammar(text, bot, reply, lang="en", retry=True):
    api_key = bot.config.get_api_key("huggingface")
    if not api_key:
        return "error: missing api key for huggingface"

    if lang not in LANG_MODEL_MAP:
        return f"error: language '{lang}' not supported"

    model = LANG_MODEL_MAP[lang]

    text = text.strip()

    client = HuggingFaceClient([api_key])
    response = client.send(text, model)
    if (
        "estimated_time" in response
        and "error" in response
        and "currently loading" in response["error"]
        and retry
    ):
        estimated_time = int(response["estimated_time"])
        if estimated_time < 120 and estimated_time > 0:
            reply(
                f"⏳ Model is currently loading. I will retry in a few minutes and give your response. Please don't spam. Estimated time: {estimated_time} seconds."
            )
            sleep(estimated_time)
            return grammar(text, bot, reply, lang, retry=False)
        else:
            reply(
                f"⏳ Model is currently loading and will take some minutes. Try again later. Estimated time: {estimated_time} seconds."
            )
            return

    if "error" in response:
        return response["error"]

    def proccess_response(resp: str) -> str:
        resp = resp.strip()
        # Replace " ." in endings with "."
        resp = re.sub(r"\s+\.$", ".", resp)
        return resp

    generated_text = {proccess_response(r["generated_text"]) for r in response}
    if text.strip() in generated_text:
        return "✅ Perfect grammar! No changes needed."

    return " - ".join(generated_text)


@hook.command("grammar", "grammaren")
def grammar_command(text, message, bot, reply):
    return grammar(text, bot, reply, lang="en")


@hook.command("grammarde", "grammatik")
def grammar_command2(text, message, bot, reply):
    return grammar(text, bot, reply, lang="de")
