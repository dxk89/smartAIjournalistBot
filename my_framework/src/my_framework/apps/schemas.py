# File: src/my_framework/apps/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional

class ArticleMetadata(BaseModel):
    """A Pydantic model to define the structure for the AI's JSON output."""
    title: str = Field(description="A concise, compelling, SEO-friendly title for the article.")
    body: str = Field(description="The full revised article, formatted with HTML paragraph tags (`<p>`).")
    publications: Optional[List[str]] = Field(None, description="This will be populated by a separate process.")
    countries: Optional[List[str]] = Field(None, description="This will be populated by a separate process.")
    industries: Optional[List[str]] = Field(None, description="This will be populated by a separate process.")
    seo_description: str = Field(description="A concise, engaging SEO meta description (155 characters max).")
    seo_keywords: str = Field(description="A comma-separated string of relevant SEO keywords.")
    hashtags: List[str] = Field(description="An array of 3-5 relevant social media hashtags, each starting with '#'.")
    weekly_title_value: str = Field(description="A very short, punchy title for a weekly newsletter.")
    website_callout_value: str = Field(description="A brief, attention-grabbing callout for the website's front page.")
    social_media_callout_value: str = Field(description="A short, engaging phrase for social media posts (less than 250 characters).")
    abstract_value: str = Field(description="A concise summary of the article's content (150 characters max).")
    google_news_keywords_value: str = Field(description="A comma-separated string of relevant keywords for Google News.")
    daily_subject_value: str = Field(description="Choose ONE: 'Macroeconomic News', 'Banking And Finance', 'Companies and Industries', or 'Political'.")
    key_point_value: str = Field(description="Choose ONE: 'Yes' or 'No'.")
    machine_written_value: str = Field(description="Choose ONE: 'Yes' or 'No'.")
    byline_value: str = Field(description="The author's name, or 'staff writer' if not available.")
    ballot_box_value: str = Field(description="Choose ONE: 'Yes' or 'No'. If the article is about elections, this must be 'Yes'.")
    africa_daily_section_value: str = Field(description="If relevant, choose ONE from the provided list for Africa Daily Section.")
    southeast_europe_today_sections_value: str = Field(description="If relevant, choose ONE from the provided list for Southeast Europe Today Sections.")
    cee_news_watch_country_sections_value: str = Field(description="If relevant, choose ONE from the provided list for CEE News Watch Country Sections.")
    n_africa_today_section_value: str = Field(description="If relevant, choose ONE from the provided list for N.Africa Today Section.")
    middle_east_today_section_value: str = Field(description="If relevant, choose ONE from the provided list for Middle East Today Section.")
    baltic_states_today_sections_value: str = Field(description="If relevant, choose ONE from the provided list for Baltic States Today Sections.")
    asia_today_sections_value: str = Field(description="If relevant, choose ONE from the provided list for Asia Today Sections.")
    latam_today_value: str = Field(description="If relevant, choose ONE from the provided list for LatAm Today.")