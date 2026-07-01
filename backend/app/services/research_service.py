import urllib.parse
from app.services.playwright_client import playwright_browser
from app.core.config import settings
import google.generativeai as genai
from typing import List, Dict


class ResearchService:
    def __init__(self):
        # Configure Gemini model if key is present
        self.gemini_configured = False
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_configured = True

    async def search_duckduckgo(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        """Perform search on DuckDuckGo and return top result links."""
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        browser = await playwright_browser.get_browser()
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        results = []
        try:
            await page.goto(search_url, wait_until="domcontentloaded")
            # Wait for results container
            await page.wait_for_selector(".links_main", timeout=8000)
            
            # Extract links and titles
            links_elements = await page.query_selector_all(".result__a")
            for elem in links_elements[:limit]:
                title = await elem.inner_text()
                url = await elem.get_attribute("href")
                if url and title:
                    # Clean duckduckgo redirection URLs if needed
                    # e.g., //duckduckgo.com/l/?uddg=https%3A%2F%2F...
                    if "uddg=" in url:
                        actual_url = url.split("uddg=")[1].split("&")[0]
                        url = urllib.parse.unquote(actual_url)
                    results.append({"title": title, "url": url})
        except Exception as e:
            print(f"Error during search scraping: {str(e)}")
            # Return simple fallback link
            results = [
                {"title": f"Google Search for {query}", "url": f"https://www.google.com/search?q={encoded_query}"}
            ]
        finally:
            await page.close()
        return results

    async def summarize_text(self, text: str, query: str) -> str:
        """Summarize text using Gemini LLM if configured, otherwise fall back to NLP summary."""
        cleaned_text = text[:15000]  # Limit context length for prompt efficiency
        
        if self.gemini_configured:
            try:
                # Use Gemini 1.5 Flash or Pro
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = (
                    f"You are Prime, an advanced AI research assistant. Review the following web content "
                    f"and write a concise summary addressing the query: '{query}'. Provide key findings "
                    f"in markdown bullet points and explain core concepts.\n\nContent:\n{cleaned_text}"
                )
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Gemini error during summarisation: {str(e)}\n\n(Fallback summary: Scraped {len(text)} characters of text)."
        else:
            # Fallback heuristic summarizer
            paragraphs = [p.strip() for p in cleaned_text.split('\n') if len(p.strip()) > 100]
            summary_sentences = paragraphs[:4]
            summary = "\n\n".join(summary_sentences)
            return (
                f"### Heuristic Web Extract for: {query}\n"
                f"*Note: Gemini API key not detected. Showing parsed page text extraction.*\n\n"
                f"{summary}\n\n"
                f"... (extracted {len(cleaned_text)} characters total)."
            )

    async def compile_research_report(self, query: str) -> Dict:
        """Execute full research pipeline: search, scrape top link, and summarize."""
        search_results = await self.search_duckduckgo(query, limit=3)
        
        if not search_results or search_results[0]["title"].startswith("Google Search"):
            # Fallback when search scraping fails or returns nothing
            return {
                "title": f"Research Report: {query}",
                "summary": f"Could not scrape real-time search engine results directly. Showing search queries.",
                "content": f"Please verify internet connection or check your Playwright chromium installation.\nSearch query was: '{query}'",
                "sources": search_results
            }

        # Fetch content of the top result
        top_result = search_results[0]
        page_data = await playwright_browser.fetch_page_content(top_result["url"])
        
        summary = await self.summarize_text(page_data["content"], query)
        
        return {
            "title": f"Research: {query.title()}",
            "summary": f"Consolidated summary from the top source: {top_result['title']}.",
            "content": summary,
            "sources": search_results
        }


research_service = ResearchService()
