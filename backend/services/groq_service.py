import json
import re
from datetime import datetime
from collections import Counter
import logging
from groq import Groq  # ✅ Correct import for the current SDK
from config import Config

logger = logging.getLogger(__name__)

class GroqService:
    """Robust Groq AI service for text and document analysis"""

    def __init__(self):
        self.available_models = [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        self.default_model = "llama-3.1-8b-instant"
        self.client = None

        # Initialize Groq client safely
        if getattr(Config, "GROQ_API_KEY", None):
            try:
                # ✅ Correct client initialization
                self.client = Groq(api_key=Config.GROQ_API_KEY)

                # Optional connectivity test
                response = self.client.chat.completions.create(
                    model=self.default_model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=3
                )

                logger.info(f"✅ [Groq] Connected successfully. Model: {response.model}")
                print("✅ [Groq] API service initialized successfully")

            except Exception as e:
                logger.error(f"❌ [Groq] Initialization failed: {e}", exc_info=True)
                print(f"❌ [Groq] Initialization failed: {e}")
                self.client = None
        else:
            logger.warning("⚠️ GROQ_API_KEY not found — AI features disabled")
            self.client = None

    # ------------------------------------------------------------
    def is_available(self) -> bool:
        """Check if Groq service is ready"""
        return self.client is not None

    # ------------------------------------------------------------
    def analyze_text(self, text: str, filename: str, model: str = None) -> dict:
        """Analyze text using Groq AI with fallback logic"""
        if not self.is_available() or not text:
            logger.warning("⚠️ [Groq] Service unavailable or text empty.")
            return None

        model = model or self.default_model
        result = self._analyze_with_model(text, filename, model)

        # Try fallback models if weak output
        if not result or not result.get("keywords") or len(result["keywords"]) < 3:
            logger.warning(f"⚠️ [Groq] Primary model {model} produced weak output — trying fallbacks")
            for fallback in self.available_models:
                if fallback != model:
                    fallback_result = self._analyze_with_model(text, filename, fallback)
                    if fallback_result and len(fallback_result.get("keywords", [])) >= 3:
                        result = fallback_result
                        logger.info(f"✅ [Groq] Using fallback model: {fallback}")
                        break

        # Generate keywords manually if still weak
        if not result or len(result.get("keywords", [])) < 3:
            logger.info("⚙️ [Groq] Auto-generating keywords from raw text")
            generated = self._generate_keywords_from_text(text, filename)
            result = result or {}
            result["keywords"] = generated
            result["keywords_source"] = "generated"

        return result

    # ------------------------------------------------------------
    def _analyze_with_model(self, text: str, filename: str, model: str) -> dict:
        """Run a single Groq model analysis safely"""
        try:
            prompt = self._build_analysis_prompt(text[:4000], filename)
            logger.info(f"🧠 [Groq] Sending request to model: {model}")

            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
                top_p=0.9,
                stream=False
            )

            # ✅ Robust extraction: handle dict-like or object-like structures
            message = None
            if hasattr(response, "choices") and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    message = choice.message.content
                elif isinstance(choice, dict) and "message" in choice:
                    message = choice["message"].get("content")

            if not message:
                logger.warning(f"⚠️ [Groq] Empty response for {filename}")
                return None

            result_text = message.strip()
            parsed = self._parse_response(result_text, filename)
            parsed = self._ensure_analysis_fields(parsed, text, filename)
            parsed["analysis_date"] = datetime.utcnow().isoformat()
            parsed["model_used"] = model
            return parsed

        except Exception as e:
            logger.error(f"❌ [Groq] Error analyzing {filename} with {model}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------
    def _build_analysis_prompt(self, text: str, filename: str) -> str:
        """Prepare Groq input prompt"""
        ext = filename.split('.')[-1].upper() if '.' in filename else 'FILE'
        return f"""
Analyze the following file: {filename} (type: {ext})

Return a VALID JSON with:
- "summary": 2–3 sentence summary
- "keywords": list of 5–10 keywords
- "caption": one short caption

Content:
{text[:3500]}

JSON ONLY:
""".strip()

    # ------------------------------------------------------------
    def _parse_response(self, result_text: str, filename: str) -> dict:
        """Parse Groq output safely into JSON"""
        try:
            clean = result_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        logger.warning(f"⚠️ [Groq] Failed to parse JSON for {filename}")
        return {"summary": "", "keywords": [], "caption": ""}

    # ------------------------------------------------------------
    def _generate_keywords_from_text(self, text: str, filename: str, max_keywords: int = 8) -> list:
        """Basic keyword generator fallback"""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        stop_words = {
            "the","and","for","with","that","this","have","from","they","what",
            "when","where","which","were","their","there","been","because","into",
            "your","more","will","about","after","also","than","then","some","such",
            "only","other","these","them","would","could","should","much","very",
            "upon","each","both","while","like","said"
        }
        filtered = [w for w in words if w not in stop_words]
        counts = Counter(filtered)
        keywords = [w.title() for w, _ in counts.most_common(max_keywords)]
        if len(keywords) < 3:
            keywords.append(filename.split('.')[0])
        return keywords[:max_keywords]

    # ------------------------------------------------------------
    def _ensure_analysis_fields(self, result: dict, text: str, filename: str) -> dict:
        """Ensure result fields always exist"""
        result = result or {}
        ext = filename.split('.')[-1].upper() if '.' in filename else 'FILE'

        if not result.get("summary"):
            preview = text[:200].replace("\n", " ")
            result["summary"] = f"This {ext.lower()} file contains: {preview}..."
        if not result.get("keywords") or len(result["keywords"]) < 3:
            result["keywords"] = self._generate_keywords_from_text(text, filename)
        if not result.get("caption"):
            kw = ", ".join(result["keywords"][:3])
            result["caption"] = f"{ext} file: {kw}"

        result["keywords"] = list(dict.fromkeys(result["keywords"]))[:10]
        return result

    # ------------------------------------------------------------
    def get_available_models(self):
        """Return supported Groq models"""
        return self.available_models.copy()


# ------------------------------------------------------------
# Global instance
# ------------------------------------------------------------
try:
    groq_service = GroqService()
    if groq_service and groq_service.client:
        logger.info("✅ [Groq] Global instance ready.")
    else:
        logger.warning("⚠️ [Groq] Service not available.")
except Exception as e:
    logger.error(f"❌ [Groq] Failed to initialize global instance: {e}", exc_info=True)
    groq_service = None
