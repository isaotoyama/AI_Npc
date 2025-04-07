import openai
import os
import re
import traceback

class LLMHandler:
    def __init__(self, enabled=True):
        self.client = None
        self.llm_enabled = False
        self.model_name = "gpt-4o"

        if not enabled: return
        api_key = os.getenv("OPENAI_API_KEY") 

        if not api_key:
            print("ERROR: OPENAI_API_KEY missing.")
            return
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.client.models.list() # Test connection
            print("OpenAI client initialized.")
            self.llm_enabled = True
        except Exception as e:
            print(f"ERROR: Failed to initialize OpenAI client: {e}")
            traceback.print_exc()

    # --- Generate Dialogue ---
    def generate_dialogue(self, history, seed_location_info):
        if not self.llm_enabled or not self.client:
            print("LLM Disabled. Using fallback.")
            return self._fallback_response()

        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": LLM_SYSTEM_PROMPT.format(SEED_LOCATION_DESCRIPTION=seed_location_info)}]
        for turn in history:
            if turn.get('player'): messages.append({"role": "user", "content": turn['player']})
            if turn.get('npc'): messages.append({"role": "assistant", "content": turn['npc']})

        print("\n--- Generating OpenAI Dialogue ---")
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7, # Controls creativity (0=deterministic, >1=wild)
                max_tokens=150 # Limit response length (and cost)
            )
            response_content = completion.choices[0].message.content
            if not response_content: return self._fallback_response()
            return self._parse_response(response_content)
        except Exception as e: # Catch various OpenAI errors
            print(f"ERROR during OpenAI call: {e}")
            traceback.print_exc()
            return self._fallback_response(error=True)

    # --- Parse Response ---
    def _parse_response(self, response_text):
        lines = response_text.strip().split('\n')
        npc_lines = []
        options = []
        options_started = False
        # Regex to find lines like "1. Option text"
        option_pattern = re.compile(r'^\s*([1-3])\.\s+(.*?)')

        for line in lines:
            line = line.strip()
            if not line: continue
            match = option_pattern.match(line)
            if match:
                options_started = True
                text = match.group(2).strip()
                # Infer state based on keywords (simple approach)
                state = 'llm_end' if text.lower() in ["bye", "goodbye", "okay, bye!", "got it!", "thanks!"] else 'llm_continue'
                if text: options.append((text, state))
            elif not options_started:
                npc_lines.append(line)

        npc_dialogue = " ".join(npc_lines).strip() or "Pip chirps thoughtfully..."
        if not options: options = self._fallback_options() # Ensure we always have options

        # Ensure exactly 3 options
        while len(options) < 3: options.append(("...", "llm_end"))
        return npc_dialogue, options[:3]

    # --- Fallbacks ---
    def _fallback_response(self, error=False):
        npc = "Chirp... chirp! (Fuzzy thoughts!)" if error else "Pip looks around curiously. Peep!"
        return npc, self._fallback_options()

    def _fallback_options(self):
        return [("Okay.", 'llm_end'), ("Maybe later.", 'llm_end'), ("Bye!", 'llm_end')]