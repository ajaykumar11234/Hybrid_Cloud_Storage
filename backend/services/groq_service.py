import groq
import json
import re
from datetime import datetime
from collections import Counter
import logging
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

        if Config.GROQ_API_KEY:
            try:
                self.client = groq.Groq(api_key=Config.GROQ_API_KEY)
                test = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": "Hello"}],
                    model=self.default_model,
                    max_tokens=3
                )
                logger.info(f"✅ Groq initialized using model: {test.model}")
                print("✅ Groq API service initialized successfully")
            except Exception as e:
                logger.error(f"❌ Groq initialization failed: {e}")
                print(f"❌ Groq initialization failed: {e}")
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
            return None

        model = model or self.default_model
        result = self._analyze_with_model(text, filename, model)

        # Try fallback models if few keywords
        if not result or not result.get("keywords") or len(result["keywords"]) < 3:
            logger.warning(f"Primary model {model} produced weak output — trying fallbacks")
            for fallback in self.available_models:
                if fallback != model:
                    logger.info(f"🔁 Trying fallback model: {fallback}")
                    fallback_result = self._analyze_with_model(text, filename, fallback)
                    if fallback_result and len(fallback_result.get("keywords", [])) >= 3:
                        logger.info(f"✅ Using fallback model: {fallback}")
                        result = fallback_result
                        break

        # Generate keywords manually if still weak
        if not result or len(result.get("keywords", [])) < 3:
            logger.info("⚙️ Auto-generating keywords from raw text")
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
            logger.info(f"🧠 Sending request to Groq model: {model}")

            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=0.3,
                max_tokens=1024,
                top_p=0.9,
                stream=False
            )

            # Handle unexpected structure
            message = getattr(response.choices[0].message, "content", None)
            if not message:
                logger.warning(f"⚠️ No content in Groq response for {filename}")
                return None

            result_text = message.strip()
            parsed = self._parse_response(result_text, filename)
            parsed = self._ensure_analysis_fields(parsed, text, filename)
            parsed["analysis_date"] = datetime.utcnow().isoformat()
            parsed["model_used"] = model
            return parsed

        except Exception as e:
            logger.error(f"❌ Error analyzing {filename} with {model}: {e}")
            return None

    # ------------------------------------------------------------
    def _build_analysis_prompt(self, text: str, filename: str) -> str:
        """Prepare the Groq input prompt"""
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
        """Parse Groq output to JSON"""
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
        """Ensure summary, keywords, caption exist"""
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
