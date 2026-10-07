"""HIVEMIND Media Outlets, Editorial Credibility & News Broadcasts Module."""

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class NewsArticle:
    """A published newspaper article or municipal news broadcast."""

    article_id: str
    headline: str
    topic: str
    summary: str
    sentiment: float  # [-1.0 (Alarming / Crisis) to +1.0 (Celebratory / Thriving)]
    credibility: float  # [0.0, 1.0]
    publisher: str
    tick: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "topic": self.topic,
            "summary": self.summary,
            "sentiment": round(self.sentiment, 2),
            "credibility": round(self.credibility, 4),
            "publisher": self.publisher,
            "tick": self.tick,
        }


@dataclass
class MediaOutlet:
    """A city newspaper or broadcasting agency with distinct editorial bias and reliability."""

    outlet_id: str
    name: str
    bias_factor: float  # [-1.0 (Opposition / Sensationalist) to +1.0 (State Gazette / Civic Official)]
    credibility: float  # Baseline journalistic integrity [0.0, 1.0]
    sensationalism: float  # Tendency to exaggerate crises [0.0, 1.0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outlet_id": self.outlet_id,
            "name": self.name,
            "bias_factor": round(self.bias_factor, 2),
            "credibility": round(self.credibility, 4),
            "sensationalism": round(self.sensationalism, 2),
        }


class MediaEngine:
    """Authoritative city press and media publisher."""

    def __init__(self) -> None:
        self.outlets: dict[str, MediaOutlet] = {
            "press_civic": MediaOutlet(
                outlet_id="press_civic",
                name="Metropolitan Civic Chronicle",
                bias_factor=0.30,
                credibility=0.85,
                sensationalism=0.15,
            ),
            "press_tabloid": MediaOutlet(
                outlet_id="press_tabloid",
                name="The Metro Whisper & Voice",
                bias_factor=-0.40,
                credibility=0.55,
                sensationalism=0.85,
            ),
        }
        self.articles_archive: list[NewsArticle] = []
        self.daily_articles: list[NewsArticle] = []

    def generate_daily_news(
        self,
        world_state: Any,
        rng: random.Random,
    ) -> list[NewsArticle]:
        """
        Synthesize current economic, political, and social conditions into daily published articles.
        """
        current_tick = world_state.clock.current_tick
        new_articles: list[NewsArticle] = []
        metrics = world_state.metrics

        civic_press = self.outlets["press_civic"]
        tabloid = self.outlets["press_tabloid"]

        # 1. Riots or Civil Unrest News
        rioting_count = metrics.rioting_districts_count
        if rioting_count > 0:
            headline = f"BREAKING: Civil Disturbance Erupts in {rioting_count} City District(s)!"
            summary = (
                "Emergency security protocols deployed. Property damage and commercial "
                "disruptions reported as citizen unrest reaches critical levels."
            )
            art = NewsArticle(
                article_id=f"art_{current_tick:04d}_riot",
                headline=headline,
                topic="RIOT_ALERT",
                summary=summary,
                sentiment=-0.80,
                credibility=tabloid.credibility,
                publisher=tabloid.name,
                tick=current_tick,
            )
            new_articles.append(art)

        # 2. Food Prices / Inflation News
        elif metrics.inflation_rate > 5.0 or metrics.cpi > 115.0:
            headline = (
                f"Cost of Living Alert: Commodity Index Rises to {metrics.cpi:.1f} C"
            )
            summary = (
                f"Households face increasing grocery and rent expenses. "
                f"Rolling inflation stands at {metrics.inflation_rate:.1f}%."
            )
            art = NewsArticle(
                article_id=f"art_{current_tick:04d}_cpi",
                headline=headline,
                topic="INFLATION_SURGE",
                summary=summary,
                sentiment=-0.50,
                credibility=civic_press.credibility,
                publisher=civic_press.name,
                tick=current_tick,
            )
            new_articles.append(art)

        # 3. Democratic Politics & Elections News
        if current_tick == getattr(world_state, "last_election_tick", -1):
            winner_id = metrics.current_mayor_id
            headline = f"ELECTION VERDICT: Mayor ({winner_id}) Holds City Hall Mandate"
            summary = (
                f"Electoral commission ratifies municipal vote tallies. Citizen approval "
                f"stands at {metrics.approval_rating:.1f}% as administration pledges civic order."
            )
            art = NewsArticle(
                article_id=f"art_{current_tick:04d}_elec",
                headline=headline,
                topic="ELECTION_UPDATE",
                summary=summary,
                sentiment=0.30,
                credibility=civic_press.credibility,
                publisher=civic_press.name,
                tick=current_tick,
            )
            new_articles.append(art)

        # 4. Standard Economic & Civic Prosperity News
        if not new_articles and (current_tick % 10 == 0 or current_tick == 1):
            if metrics.city_favorability >= 0.50:
                headline = f"Civic Progress Report: Municipal Market Cap Sustains {metrics.stock_market_cap:,.0f} C"
                summary = (
                    "City treasury reports stable liquidity. Employment and production "
                    "continue across central industrial and agricultural facilities."
                )
                sentiment = 0.40
            else:
                headline = f"Public Skepticism Rises as Citizen Approval Slips to {metrics.approval_rating:.1f}%"
                summary = (
                    "Opposition commentators raise questions regarding public expenditures "
                    "and municipal living conditions."
                )
                sentiment = -0.35

            art = NewsArticle(
                article_id=f"art_{current_tick:04d}_general",
                headline=headline,
                topic="CIVIC_REPORT",
                summary=summary,
                sentiment=sentiment,
                credibility=civic_press.credibility,
                publisher=civic_press.name,
                tick=current_tick,
            )
            new_articles.append(art)

        self.daily_articles = new_articles
        self.articles_archive.extend(new_articles)
        # Keep rolling last 60 articles
        if len(self.articles_archive) > 60:
            self.articles_archive = self.articles_archive[-60:]

        return new_articles

    def to_dict(self) -> dict[str, Any]:
        return {
            "outlets": {k: v.to_dict() for k, v in self.outlets.items()},
            "daily_articles_count": len(self.daily_articles),
            "archive_count": len(self.articles_archive),
        }
