import groq
from config import Config
import json
from datetime import datetime

class GroqService:
    """Groq AI service for file analysis"""
    
    def __init__(self):
        if Config.GROQ_API_KEY:
            try:
                self.client = groq.Groq(api_key=Config.GROQ_API_KEY)
                # Test the connection with a current model
                test_response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": "Say 'Hello'"}],
                    model="llama-3.1-8b-instant",  # Updated to current model
                    max_tokens=5
                )
                print("✅ Groq API service initialized and working!")
                print(f"✅ Using model: {test_response.model}")
            except Exception as e:
                print(f"❌ Groq API initialization failed: {e}")
                self.client = None
        else:
            print("⚠️ GROQ_API_KEY not found, AI features disabled")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Groq service is available"""
        return self.client is not None
    
    def analyze_text(self, text: str, filename: str, model: str = "llama-3.1-8b-instant") -> dict:
        """Analyze text using Groq AI"""
        if not self.is_available() or not text:
            return None
        
        try:
            # Prepare the content for analysis
            content_preview = text[:4000]
            
            # Available Groq models (updated list):
            # - "llama-3.1-8b-instant" (fast, good for most tasks)
            # - "llama-3.1-70b-versatile" (more powerful)
            # - "mixtral-8x7b-32768" (excellent for complex tasks)
            # - "gemma2-9b-it" (good alternative)
            
            prompt = f"""Analyze the following content from the file "{filename}" and provide:

1. A concise 2-3 sentence summary
2. 5-10 relevant keywords or key phrases as a JSON array
3. A brief one-sentence caption

Return your response as a JSON object with the following structure:
{{
  "summary": "your summary here",
  "keywords": ["keyword1", "keyword2", ...],
  "caption": "your caption here"
}}

Content to analyze:
{content_preview}

JSON Response:"""
            
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=0.1,
                max_tokens=1024,
                top_p=0.9,
                stream=False
            )
            
            result_text = response.choices[0].message.content.strip()
            print(f"🤖 Groq Response ({model}): {result_text[:200]}...")
            
            # Parse JSON response
            try:
                analysis_result = json.loads(result_text)
            except json.JSONDecodeError:
                analysis_result = self._parse_fallback_response(result_text, filename)
            
            # Ensure required fields
            analysis_result = self._ensure_analysis_fields(analysis_result, filename)
            analysis_result["analysis_date"] = datetime.utcnow().isoformat()
            analysis_result["model_used"] = model
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error in Groq analysis: {e}")
            return None
    
    def _parse_fallback_response(self, result_text: str, filename: str) -> dict:
        """Fallback parsing for non-JSON responses"""
        lines = result_text.split('\n')
        summary = ""
        keywords = []
        caption = ""
        
        for line in lines:
            line_lower = line.lower()
            if 'summary' in line_lower and not summary:
                summary = line.split(':')[-1].strip() if ':' in line else line
            elif 'keyword' in line_lower and not keywords:
                keyword_line = line.split(':')[-1].strip()
                if '[' in keyword_line and ']' in keyword_line:
                    try:
                        keywords = json.loads(keyword_line)
                    except:
                        keywords = [k.strip().strip('"[]') for k in keyword_line.strip('[]').split(',')]
                else:
                    keywords = [k.strip().strip('"') for k in keyword_line.split(',')]
                keywords = keywords[:10]
            elif 'caption' in line_lower and not caption:
                caption = line.split(':')[-1].strip() if ':' in line else line
        
        return {
            "summary": summary,
            "keywords": keywords,
            "caption": caption
        }
    
    def _ensure_analysis_fields(self, analysis_result: dict, filename: str) -> dict:
        """Ensure all required fields are present in analysis result"""
        file_extension = filename.split('.')[-1].upper()
        
        if not analysis_result.get('summary'):
            analysis_result['summary'] = f"This appears to be a {file_extension} file containing relevant content."
        
        if not analysis_result.get('keywords'):
            base_name = filename.split('.')[0]
            analysis_result['keywords'] = [base_name, 'document', 'file']
        
        if not analysis_result.get('caption'):
            analysis_result['caption'] = f"Document: {filename}"
        
        return analysis_result