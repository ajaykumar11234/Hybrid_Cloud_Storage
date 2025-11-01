import openai
from config import Config
import json
from datetime import datetime

class OpenAIService:
    """OpenAI service for file analysis"""
    
    def __init__(self):
        if Config.OPENAI_API_KEY:
            try:
                openai.api_key = Config.OPENAI_API_KEY
                # Test the connection
                test_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say 'Hello'"}],
                    max_tokens=5
                )
                print("✅ OpenAI API service initialized and working!")
            except Exception as e:
                print(f"❌ OpenAI API initialization failed: {e}")
                self.client = None
        else:
            print("⚠️ OPENAI_API_KEY not found, AI features disabled")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return openai.api_key is not None
    
    def analyze_text(self, text: str, filename: str, model: str = "gpt-3.5-turbo") -> dict:
        """Analyze text using OpenAI"""
        if not self.is_available() or not text:
            return None
        
        try:
            # Prepare the content for analysis
            content_preview = text[:3000]
            
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
            
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that analyzes document content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            print(f"🤖 OpenAI Response ({model}): {result_text[:200]}...")
            
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
            print(f"❌ Error in OpenAI analysis: {e}")
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
                keywords = [k.strip().strip('"[]') for k in keyword_line.split(',')][:10]
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